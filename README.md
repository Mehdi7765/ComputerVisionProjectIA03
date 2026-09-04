# Architecture distribuée pour le traitement d'images — IA03

Détection d'objets **en temps réel** sur un flux vidéo, répartie sur plusieurs machines d'un réseau local :

- une machine **capture** la webcam et la diffuse ;
- une autre machine **analyse** chaque image avec un modèle YOLO et rediffuse le flux annoté ;
- **n'importe quel appareil** du réseau (téléphone, PC) **consulte** le résultat dans un simple navigateur, sans rien installer.

Chaque rôle est un script indépendant : **n'importe quel ordinateur peut tenir n'importe quel rôle**, il suffit de lancer le bon script.

---

## 1. Architecture

```
   PC CAPTURE                       PC ANALYSE                          CONSULTATION
 ┌──────────────────┐   HTTP MJPEG  ┌──────────────────────────┐  HTTP MJPEG + page web  ┌────────────────────┐
 │ webcam           │  port 5000    │ YOLOv4-tiny (OpenCV DNN) │  port 8000              │ navigateur         │
 │ capture.py       │ ────────────▶ │ analyse.py               │ ──────────────────────▶ │ téléphone / PC     │
 │                  │  /video_feed  │                          │  /  et  /video_feed     │ aucun logiciel     │
 └──────────────────┘               └──────────────────────────┘                         └────────────────────┘
```

| Rôle | Script | Ce qu'il fait | Port |
|---|---|---|---|
| **Capture** | `capture.py` | Lit la webcam, diffuse le flux brut en MJPEG | 5000 |
| **Analyse** | `analyse.py` | Lit le flux brut, applique YOLO, rediffuse le flux **annoté** + interface web | 8000 |
| **Consultation** | *(aucun)* | Un navigateur ouvre `http://<IP du PC analyse>:8000/` | — |

Les images circulent en **MJPEG sur HTTP** (une suite d'images JPEG), un format lu nativement par tous les navigateurs et par OpenCV. Les statistiques et les réglages passent en **JSON**.

---

## 2. Contenu du dépôt

| Fichier / dossier | Rôle |
|---|---|
| `config.py` | **Tous les paramètres** (adresses, ports, caméra, modèle, seuils) regroupés au même endroit |
| `capture.py` | Rôle capture |
| `analyse.py` | Rôle analyse + serveur web |
| `detecteur.py` | Classe `DetecteurYOLO` : chargement du modèle, détection, dessin des boîtes |
| `diffuseur.py` | Classe `DiffuseurMJPEG` : diffusion d'un flux vers plusieurs spectateurs |
| `utilitaires.py` | Adresse IP locale, compteur d'images/s, petites fonctions communes |
| `templates/index.html` | Interface web de consultation |
| `modeles/` | YOLOv4-tiny (`.cfg`, `.weights`) et la liste des 80 classes (`coco.names`) — **inclus, rien à télécharger** |
| `requirements.txt` | Dépendances Python |
| `exemples_cours/` | Scripts de départ fournis en TP (RTSP/GStreamer/ffmpeg), gardés pour référence, **non utilisés** |
| `docs/` | Grille d'évaluation |

---

## 3. Installation

Prérequis : **Python 3.8 ou plus**, `git`, et une webcam sur la machine qui fera la capture.

```bash
git clone https://github.com/Mehdi7765/ComputerVisionProjectIA03.git
cd ComputerVisionProjectIA03
```

### Windows / macOS

```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS
pip install -r requirements.txt
```

### Linux (Debian / Ubuntu)

Au choix, avec les paquets système (recommandé, OpenCV y est déjà compilé) :

```bash
sudo apt install python3-opencv python3-flask python3-numpy
```

ou dans un environnement virtuel comme ci-dessus. Si `pip` refuse avec *externally-managed-environment*, c'est qu'il faut passer par le `venv`.

### Vérifier

```bash
python -c "import cv2, flask, numpy; print('OpenCV', cv2.__version__, '- OK')"
```

> Sur Linux/macOS la commande s'appelle généralement `python3` ; sur Windows `python`. Les exemples ci-dessous utilisent `python`.

---

## 4. Configuration

Tout est dans **`config.py`**. Les valeurs à connaître :

| Paramètre | Défaut | Signification |
|---|---|---|
| `ADRESSE_PC_CAPTURE` | `172.20.10.11` | IP du PC capture sur le réseau local (**à adapter**) |
| `CAPTURE_PORT` | `5000` | Port du flux brut |
| `ANALYSE_PORT` | `8000` | Port de l'interface web et du flux annoté |
| `INDEX_CAMERA` | `0` | Webcam à utiliser (0 = la première) |
| `LARGEUR_CAPTURE` × `HAUTEUR_CAPTURE` | `640×480` | Résolution de capture |
| `QUALITE_JPEG` | `80` | Compression des images envoyées (plus bas = moins de débit) |
| `TAILLE_ENTREE` | `416` | Taille d'entrée du réseau : 320 (rapide) / 416 / 608 (précis) |
| `SEUIL_CONFIANCE` | `0.5` | Confiance minimale pour afficher une détection |

**Pas besoin d'éditer le fichier en séance** : chaque script accepte des options qui prennent le dessus, par exemple `--source`, `--port`, `--camera`, `--seuil`, `--taille`, `--qualite`. Voir `python analyse.py --help`.

### Trouver l'adresse IP d'une machine

- `capture.py` et `analyse.py` **affichent leur adresse au démarrage** : c'est la méthode la plus simple.
- Sinon : `hostname -I` (Linux), `ipconfig` (Windows), `ifconfig` (macOS).

⚠️ Sur un réseau en DHCP (box, partage de connexion), l'adresse d'une machine **peut changer** d'une connexion à l'autre. Vérifiez-la à chaque séance.

---

## 5. Démarrage — dans cet ordre

Toutes les machines doivent être **sur le même réseau Wi-Fi / Ethernet**.

### Étape 1 — PC capture (celui qui a la webcam)

```bash
python capture.py
```

Le terminal affiche :

```
  PC CAPTURE prêt
  Flux à donner au PC d'analyse :  http://192.168.1.20:5000/video_feed
  Page de contrôle :               http://192.168.1.20:5000/
```

Notez l'adresse du flux. Vérification : ouvrir `http://localhost:5000/` sur ce même PC, la webcam doit s'afficher.

Options utiles : `--camera 1` (autre webcam), `--camera video.mp4` (fichier vidéo, pour tester sans webcam), `--largeur 320 --hauteur 240` (moins de débit).

### Étape 2 — PC analyse (celui qui fait tourner YOLO, pas besoin de webcam)

```bash
python analyse.py --source http://192.168.1.20:5000/video_feed
```

*(remplacez par l'adresse affichée à l'étape 1, ou mettez-la dans `ADRESSE_PC_CAPTURE` de `config.py` et lancez simplement `python analyse.py`)*

Le terminal affiche :

```
  PC ANALYSE prêt
  Source vidéo :        http://192.168.1.20:5000/video_feed
  Interface web :       http://192.168.1.30:8000/   <- à ouvrir sur n'importe quel appareil
```

Options utiles : `--taille 320` (plus rapide), `--seuil 0.6` (moins de fausses détections).

### Étape 3 — Consultation (téléphone, PC du prof, n'importe quoi)

Se connecter au même Wi-Fi et ouvrir dans un navigateur :

```
http://192.168.1.30:8000/
```

On voit le flux annoté en direct, les images par seconde, la latence, le nombre d'objets, et on peut modifier les réglages. Plusieurs spectateurs peuvent regarder en même temps.

### Test sur une seule machine

Pour vérifier l'installation sans réseau, dans deux terminaux :

```bash
python capture.py
python analyse.py --source http://127.0.0.1:5000/video_feed
```

ou même sans `capture.py`, directement sur la webcam locale :

```bash
python analyse.py --source 0
```

---

## 6. Vérifications et dépannage

Deux commandes suffisent pour diagnostiquer, à lancer depuis la machine *cliente* vers la machine *serveur* :

```bash
ping 192.168.1.20                          # la machine est-elle joignable ?
curl -m 5 http://192.168.1.20:5000/etat    # le serveur répond-il ?
```

| Symptôme | Cause probable | Solution |
|---|---|---|
| `Connection refused` immédiat | Le script serveur n'est pas lancé, ou mauvais port | Lancer `capture.py` / `analyse.py`, vérifier le port |
| **Aucune réponse, délai qui expire** (le `ping` peut échouer aussi) | **Pare-feu du PC serveur** qui bloque les connexions entrantes. Cas le plus fréquent, surtout sous Windows | Windows : autoriser Python quand la fenêtre du pare-feu apparaît (réseaux privés), ou en PowerShell administrateur `New-NetFirewallRule -DisplayName "IA03" -Direction Inbound -LocalPort 5000,8000 -Protocol TCP -Action Allow`. Linux : `sudo ufw allow 5000,8000/tcp` |
| Le `ping` passe entre les machines et le prof mais pas entre nos PC | Isolation des clients activée sur le point d'accès (fréquent sur les partages de connexion et Wi-Fi publics) | Utiliser une box / un routeur, ou un partage de connexion sans isolation |
| Badge « source coupée, reconnexion… » sur l'interface | `capture.py` arrêté, ou l'IP du PC capture a changé | Relancer `capture.py`, relire son adresse, relancer `analyse.py --source ...`. La reconnexion est automatique une fois la source revenue |
| « impossible d'ouvrir la source 0 » | Webcam utilisée par une autre application, ou autre index | Fermer Teams/Zoom/navigateur, essayer `--camera 1` |
| Image saccadée, latence élevée | PC analyse trop lent, ou réseau chargé | `--taille 320`, `--qualite 60`, capture en `--largeur 320 --hauteur 240` |
| La page s'affiche mais pas la vidéo | Le navigateur bloque le contenu, ou flux non démarré | Recharger la page ; ouvrir `/video_feed` directement pour isoler le problème |

---

## 7. Fonctionnalités

**Chaîne de base**
- Diffusion de la webcam sur le réseau (MJPEG/HTTP).
- Détection d'objets YOLOv4-tiny, 80 classes (personnes, véhicules, animaux, objets du quotidien), boîtes et étiquettes avec le pourcentage de confiance.
- Rediffusion du flux annoté, consultable depuis n'importe quel navigateur.

**Au-delà de la demande**
- **Interface web** claire et adaptée au téléphone : flux, statistiques, réglages.
- **Réglages à chaud** sans redémarrer : seuil de confiance, taille d'entrée du réseau (vitesse ⇄ précision), **filtre des classes** à détecter.
- **Indicateurs en direct** : images/s, latence d'inférence (ms), nombre d'objets, compteur par classe ; bandeau incrusté dans la vidéo.
- **Plusieurs spectateurs simultanés** : la source n'est lue et encodée qu'une fois, chaque spectateur reçoit la dernière image (un spectateur lent ne ralentit pas les autres).
- **Reprise automatique** : si la webcam ou le flux coupe, capture et analyse se reconnectent seuls ; la page web relance la vidéo d'elle-même.
- **Maîtrise de la latence** : l'analyse ne garde que la dernière image reçue au lieu d'empiler une file d'attente ; si le modèle est plus lent que la caméra, on saute des images plutôt que d'accumuler du retard.
- **Réduction du débit** : qualité JPEG et résolution réglables.
- **Plusieurs sources** : webcam, fichier vidéo ou flux RTSP (`--camera`), et une seule machine si besoin (`--source 0`).
- **Portable** : même code sous Linux, Windows et macOS ; paramètres centralisés ; aucune adresse en dur dans le code.

---

## 8. Choix techniques (résumé)

| Décision | Retenu | Pourquoi | Écarté |
|---|---|---|---|
| Protocole de diffusion | **MJPEG sur HTTP** | Lu par tout navigateur sans plugin (critère « accessible avec un simple navigateur »), un seul port TCP donc facile à passer au pare-feu, multi-clients trivial, débogable avec `curl` | RTSP + H.264 (GStreamer/ffmpeg, cf. `exemples_cours/`) : débit plus faible, mais nécessite un lecteur (VLC), une compilation d'OpenCV avec GStreamer, et **non lisible dans un navigateur** |
| Modèle | **YOLOv4-tiny via `cv2.dnn`** | Aucune dépendance lourde (pas de PyTorch), 15–20 img/s sur un CPU portable, fichiers de 24 Mo inclus dans le dépôt : `git clone` suffit | YOLOv8 (ultralytics) : plus précis mais ~2 Go à installer et plus lent sur CPU |
| Emplacement du traitement | **Sur une machine dédiée** (PC analyse) | Le PC capture reste léger (une webcam suffit, ex. Raspberry Pi), le calcul est sur la machine qui a le CPU, les spectateurs n'ont rien à installer | Traitement sur le PC capture : concentre toute la charge sur une seule machine et empêche l'architecture distribuée |
| Format des échanges | JPEG (images) + JSON (statistiques, réglages) | Standards, lisibles, supportés partout | Flux binaire maison : rien à gagner sur un réseau local |

---

## 9. Limites connues

- Le serveur web est celui de développement de Flask : suffisant pour une démonstration, pas pour une mise en production.
- Le MJPEG consomme plus de bande passante que du H.264 (environ 1 à 2 Mbit/s par spectateur en 640×480) ; le débit croît avec le nombre de spectateurs.
- YOLOv4-tiny est moins précis qu'un modèle complet, surtout sur les petits objets.
- Latence de bout en bout typique : 200 à 500 ms sur un Wi-Fi correct.
- Aucune authentification : toute personne sur le réseau peut voir le flux (acceptable pour un TP).
