# Architecture distribuée pour le traitement d'images — IA03

*Mehdi Ez-Zouak, Paul Louis Ledoux, Clément Menaucourt — UTT, année 2, septembre 2026.*

Détection d'objets **en temps réel** sur un flux vidéo, répartie sur plusieurs machines d'un réseau local :

- une machine **capture** la webcam et la diffuse (`diffusion_http.py`) ;
- une autre machine **analyse** chaque image avec YOLO et rediffuse le flux annoté (`lecture_http.py`) ;
- **n'importe quel appareil** du réseau (téléphone, PC) **consulte** le résultat dans un simple navigateur, sans rien installer.

Le projet est construit **à partir des scripts fournis en TP** (`diffusion_http.py`, `lecture_http.py`, `diffusion_gstreamer.py`, `diffusion_rtsp_ffmpeg.py`), qui gardent leur nom et leur structure. Chaque modification est repérée dans le code par un commentaire **`[MODIF]`** avec sa raison ; les versions d'origine sont conservées telles quelles dans `docs/scripts_origine/` pour comparaison.

Chaque rôle est un script indépendant : **n'importe quel ordinateur peut tenir n'importe quel rôle**, il suffit de lancer le bon script.

---

## 1. Architecture

```
   PC CAPTURE                        PC ANALYSE                            CONSULTATION
 ┌───────────────────┐  HTTP MJPEG   ┌───────────────────────────┐  HTTP MJPEG + page web  ┌────────────────────┐
 │ webcam            │  port 5000    │ YOLOv4-tiny (OpenCV DNN)  │  port 8000              │ navigateur         │
 │ diffusion_http.py │ ────────────▶ │ lecture_http.py           │ ──────────────────────▶ │ téléphone / PC     │
 │                   │  /video_feed  │                           │  /  et  /video_feed     │ aucun logiciel     │
 └───────────────────┘               └───────────────────────────┘                         └────────────────────┘
```

| Rôle | Script | Ce qu'il fait | Port |
|---|---|---|---|
| **Capture** | `diffusion_http.py` | Lit la webcam, diffuse le flux brut en MJPEG | 5000 |
| **Analyse** | `lecture_http.py` | Lit le flux brut, applique YOLO, rediffuse le flux **annoté** + interface web | 8000 |
| **Consultation** | *(aucun)* | Un navigateur ouvre `http://<IP du PC analyse>:8000/` | — |

Les images circulent en **MJPEG sur HTTP** (une suite d'images JPEG), un format lu nativement par tous les navigateurs et par OpenCV. Les statistiques et les réglages passent en **JSON**.

Deux **variantes de diffusion** en H.264 (débit plus faible, mais non lisibles par un navigateur) sont aussi fournies et fonctionnelles, à partir des deux autres scripts du TP : voir la section 6.

---

## 2. Contenu du dépôt

| Fichier / dossier | Origine | Rôle |
|---|---|---|
| `diffusion_http.py` | **TP, adapté** | Rôle capture : diffusion MJPEG de la webcam |
| `lecture_http.py` | **TP, adapté** | Rôle analyse : YOLO + rediffusion annotée + serveur web |
| `diffusion_rtsp_ffmpeg.py` | **TP, adapté** | Variante de capture : H.264 servi par ffmpeg |
| `diffusion_gstreamer.py` | **TP, adapté** | Variante de capture : H.264 servi par GStreamer |
| `config.py` | ajouté | **Tous les paramètres** (adresses, ports, caméra, modèle, seuils) au même endroit |
| `detecteur.py` | ajouté | Classe `DetecteurYOLO` : chargement du modèle, détection, dessin des boîtes |
| `diffuseur.py` | ajouté | Classe `DiffuseurMJPEG` : diffusion d'un flux vers plusieurs spectateurs |
| `utilitaires.py` | ajouté | IP locale, ouverture de source, lecture « dernière image », compteur d'images/s |
| `templates/index.html` | ajouté | Interface web de consultation |
| `modeles/` | ajouté | YOLOv4-tiny et YOLOv3-tiny (`.cfg`, `.weights`) et les 80 classes (`coco.names`) — **inclus, rien à télécharger** |
| `docs/scripts_origine/` | TP | Les 4 scripts **tels que fournis**, non modifiés |
| `docs/rapport.md` / `rapport.pdf` | ajouté | Rapport du projet (description, justification des choix, difficultés, mesures) |
| `docs/checklist_demo.md` | ajouté | Déroulé de la démonstration et plans B |
| `docs/figures/`, `docs/captures/` | ajouté | Schéma d'architecture, captures d'écran de l'interface |
| `docs/` | — | Grille d'évaluation |
| `requirements.txt` | ajouté | Dépendances Python |

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

Au choix, avec les paquets système (recommandé : OpenCV y est compilé avec GStreamer, nécessaire pour la variante GStreamer) :

```bash
sudo apt install python3-opencv python3-flask python3-numpy
```

ou dans un environnement virtuel comme ci-dessus. Si `pip` refuse avec *externally-managed-environment*, c'est qu'il faut passer par le `venv`.

Pour la variante ffmpeg : `sudo apt install ffmpeg` (Linux), `brew install ffmpeg` (macOS), `winget install ffmpeg` (Windows).

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
| `CAPTURE_PORT` | `5000` | Port du flux brut MJPEG |
| `ANALYSE_PORT` | `8000` | Port de l'interface web et du flux annoté |
| `RTSP_PORT`, `GSTREAMER_PORT` | `8554`, `8555` | Ports des variantes H.264 |
| `INDEX_CAMERA` | `0` | Webcam à utiliser (0 = la première) |
| `LARGEUR_CAPTURE` × `HAUTEUR_CAPTURE` | `640×480` | Résolution de capture |
| `QUALITE_JPEG` | `80` | Compression des images MJPEG (plus bas = moins de débit) |
| `TAILLE_ENTREE` | `416` | Taille d'entrée du réseau : 320 (rapide) / 416 / 608 (précis) |
| `SEUIL_CONFIANCE` | `0.5` | Confiance minimale pour afficher une détection |
| `MODELES`, `MODELE_DEFAUT` | `yolov4-tiny` | Modèles disponibles (`yolov4-tiny`, `yolov3-tiny`), changeables depuis l'interface |

**Pas besoin d'éditer le fichier en séance** : chaque script accepte des options qui prennent le dessus, par exemple `--source`, `--port`, `--camera`, `--seuil`, `--taille`, `--modele`. Voir `python lecture_http.py --help`.

### Trouver l'adresse IP d'une machine

- `diffusion_http.py` et `lecture_http.py` **affichent leur adresse au démarrage** : c'est la méthode la plus simple.
- Sinon : `hostname -I` (Linux), `ipconfig` (Windows), `ifconfig` (macOS).

⚠️ Sur un réseau en DHCP (box, partage de connexion), l'adresse d'une machine **peut changer** d'une connexion à l'autre. Vérifiez-la à chaque séance.

---

## 5. Démarrage — dans cet ordre

Toutes les machines doivent être **sur le même réseau Wi-Fi / Ethernet**.

### Étape 1 — PC capture (celui qui a la webcam)

```bash
python diffusion_http.py
```

Le terminal affiche :

```
  PC CAPTURE prêt (diffusion_http.py)
  Flux à donner au PC d'analyse :  http://192.168.1.20:5000/video_feed
  Page de contrôle :               http://192.168.1.20:5000/
```

Notez l'adresse du flux. Vérification : ouvrir `http://localhost:5000/` sur ce même PC, la webcam doit s'afficher.

Options utiles : `--camera 1` (autre webcam), `--camera video.mp4` (fichier vidéo, pour tester sans webcam), `--largeur 320 --hauteur 240` (moins de débit).

### Étape 2 — PC analyse (celui qui fait tourner YOLO, pas besoin de webcam)

```bash
python lecture_http.py --source http://192.168.1.20:5000/video_feed
```

*(remplacez par l'adresse affichée à l'étape 1, ou mettez-la dans `ADRESSE_PC_CAPTURE` de `config.py` et lancez simplement `python lecture_http.py`)*

Le terminal affiche :

```
  PC ANALYSE prêt (lecture_http.py)
  Source vidéo :        http://192.168.1.20:5000/video_feed
  Interface web :       http://192.168.1.30:8000/   <- à ouvrir sur n'importe quel appareil
```

Le terminal affiche aussi un **QR code** de l'interface web : un spectateur n'a qu'à le scanner avec son téléphone (nécessite `pip install qrcode`, inclus dans `requirements.txt`).

Une fenêtre locale montre aussi le résultat (touche `q` pour quitter) ; `--sans-fenetre` la désactive, par exemple sur une machine sans écran. Options utiles : `--taille 320` (plus rapide), `--seuil 0.6` (moins de fausses détections), `--modele yolov3-tiny`.

### Étape 3 — Consultation (téléphone, PC du prof, n'importe quoi)

Se connecter au même Wi-Fi et ouvrir dans un navigateur :

```
http://192.168.1.30:8000/
```

On voit le flux annoté en direct, les images par seconde, la latence, le nombre d'objets, et on peut modifier les réglages. Plusieurs spectateurs peuvent regarder en même temps.

### Plusieurs caméras (ex. deux PC capture, un PC analyse)

Chaque PC capture lance `python diffusion_http.py` (même port 5000, machines différentes). Le PC analyse lance **une analyse par caméra**, sur des ports différents, dans deux terminaux :

```bash
python lecture_http.py --source http://192.168.1.20:5000/video_feed --port 8000
python lecture_http.py --source http://192.168.1.21:5000/video_feed --port 8001
```

Consultation : `http://<IP analyse>:8000/` pour la première caméra, `http://<IP analyse>:8001/` pour la seconde. Ouvrir les ports 8000 et 8001 dans le pare-feu du PC analyse. Deux modèles tournent en parallèle : ajouter `--taille 320` si le PC analyse peine.

### Test sur une seule machine

Pour vérifier l'installation sans réseau, dans deux terminaux :

```bash
python diffusion_http.py
python lecture_http.py --source http://127.0.0.1:5000/video_feed
```

ou même sans diffusion, directement sur la webcam locale :

```bash
python lecture_http.py --source 0
```

---

## 6. Variantes de diffusion (H.264)

Les deux autres scripts du TP proposent une diffusion **encodée en H.264**, beaucoup moins gourmande en bande passante que le MJPEG. Elles sont fonctionnelles, et `lecture_http.py` sait les lire avec `--source` ; leur limite est qu'un navigateur ne peut pas les afficher directement (ce que fait `lecture_http.py` en rediffusant en MJPEG).

| Variante | Script | Lancement côté capture | Lecture côté analyse |
|---|---|---|---|
| ffmpeg, H.264 dans MPEG-TS sur HTTP | `diffusion_rtsp_ffmpeg.py` | `python diffusion_rtsp_ffmpeg.py` | `python lecture_http.py --source http://<IP capture>:8554/stream` |
| GStreamer, H.264/RTP sur TCP | `diffusion_gstreamer.py` | `python diffusion_gstreamer.py` | `python lecture_http.py --source "tcpclientsrc host=<IP capture> port=8555 ! gdpdepay ! rtph264depay ! avdec_h264 ! videoconvert ! appsink drop=true max-buffers=1"` |

Remarques :
- **ffmpeg** : la version d'origine utilisait `-rtsp_flags listen` pour que ffmpeg serve lui-même du RTSP. Avec ffmpeg 5.1 ce drapeau n'agit qu'en lecture : en écriture ffmpeg se comporte en client et échoue s'il n'y a pas de serveur RTSP. Le script sert donc le flux en HTTP (`-listen 1`, un lecteur à la fois) ; `--mode rtsp` permet de pousser vers un serveur RTSP externe (mediamtx…). `--camera test` diffuse une mire sans webcam.
- **GStreamer** : nécessite un OpenCV compilé avec GStreamer **sur les deux machines** (paquet `python3-opencv` de Debian/Ubuntu : oui ; `opencv-python` de pip : non). La version d'origine écoutait sur `127.0.0.1` (inaccessible depuis le réseau) et demandait un format BGR refusé par l'encodeur ; les deux sont corrigés.

---

## 7. Vérifications et dépannage

Deux commandes suffisent pour diagnostiquer, à lancer depuis la machine *cliente* vers la machine *serveur* :

```bash
ping 192.168.1.20                          # la machine est-elle joignable ?
curl -m 5 http://192.168.1.20:5000/etat    # le serveur répond-il ?
```

| Symptôme | Cause probable | Solution |
|---|---|---|
| `Connection refused` immédiat | Le script serveur n'est pas lancé, ou mauvais port | Lancer `diffusion_http.py` / `lecture_http.py`, vérifier le port |
| **Aucune réponse, délai qui expire** (le `ping` peut échouer aussi) | **Pare-feu du PC serveur** qui bloque les connexions entrantes. Cas le plus fréquent, surtout sous Windows | Windows : autoriser Python quand la fenêtre du pare-feu apparaît (réseaux privés), ou en PowerShell administrateur `New-NetFirewallRule -DisplayName "IA03" -Direction Inbound -LocalPort 5000,8000,8001 -Protocol TCP -Action Allow`. Linux : `sudo ufw allow 5000,8000,8001/tcp` |
| Le `ping` passe vers Internet mais pas entre nos PC | Isolation des clients activée sur le point d'accès (fréquent sur les partages de connexion et Wi-Fi publics) | Utiliser une box / un routeur, ou un partage de connexion sans isolation |
| Badge « source coupée, reconnexion… » sur l'interface | `diffusion_http.py` arrêté, ou l'IP du PC capture a changé | Relancer `diffusion_http.py`, relire son adresse, relancer `lecture_http.py --source ...`. La reconnexion est automatique une fois la source revenue |
| « Impossible d'ouvrir la source 0 » | Webcam utilisée par une autre application, ou autre index | Fermer Teams/Zoom/navigateur, essayer `--camera 1` |
| Image saccadée, latence élevée | PC analyse trop lent, ou réseau chargé | `--taille 320`, capture en `--largeur 320 --hauteur 240`, baisser `QUALITE_JPEG` |
| La page s'affiche mais pas la vidéo | Flux non démarré, ou navigateur qui bloque | Recharger la page ; ouvrir `/video_feed` directement pour isoler le problème |

---

## 8. Fonctionnalités

**Chaîne de base**
- Diffusion de la webcam sur le réseau (MJPEG/HTTP).
- Détection d'objets YOLOv4-tiny, 80 classes (personnes, véhicules, animaux, objets du quotidien), boîtes et étiquettes avec le pourcentage de confiance.
- Rediffusion du flux annoté, consultable depuis n'importe quel navigateur.

**Au-delà de la demande**
- **Interface web** claire et adaptée au téléphone : flux, statistiques, réglages.
- **Réglages à chaud** sans redémarrer : seuil de confiance, taille d'entrée du réseau (vitesse ⇄ précision), **filtre des classes** à détecter, **changement de modèle** (YOLOv4-tiny ↔ YOLOv3-tiny) sans interruption du flux.
- **QR code** de l'interface affiché dans le terminal du PC d'analyse.
- **Indicateurs en direct** : images/s, latence d'inférence (ms), nombre d'objets, compteur par classe ; bandeau incrusté dans la vidéo.
- **Plusieurs spectateurs simultanés** : la source n'est lue et encodée qu'une fois, chaque spectateur reçoit la dernière image (un spectateur lent ne ralentit pas les autres).
- **Reprise automatique** : si la webcam ou le flux coupe, capture et analyse se reconnectent seuls ; la page web relance la vidéo d'elle-même.
- **Maîtrise de la latence** : l'analyse ne garde que la dernière image reçue au lieu d'empiler une file d'attente ; si le modèle est plus lent que la caméra, on saute des images plutôt que d'accumuler du retard.
- **Réduction du débit** : qualité JPEG et résolution réglables ; variantes H.264 (ffmpeg, GStreamer).
- **Plusieurs sources** : webcam, fichier vidéo, flux HTTP/RTSP/GStreamer, mire de test ; et une seule machine si besoin (`--source 0`).
- **Portable** : même code sous Linux, Windows et macOS ; paramètres centralisés ; aucune adresse en dur dans le code.

---

## 9. Choix techniques (résumé)

| Décision | Retenu | Pourquoi | Écarté |
|---|---|---|---|
| Protocole de diffusion | **MJPEG sur HTTP** (`diffusion_http.py`) | Lu par tout navigateur sans plugin (critère « accessible avec un simple navigateur »), un seul port TCP donc facile à passer au pare-feu, multi-clients trivial, débogable avec `curl` | H.264 via ffmpeg ou GStreamer (variantes fournies) : débit 5 à 10 fois plus faible, mais **non lisible dans un navigateur**, un seul lecteur (ffmpeg) ou OpenCV spécial (GStreamer). Mesuré en séance, pas seulement lu dans la doc |
| Modèle | **YOLOv4-tiny via `cv2.dnn`** | Aucune dépendance lourde (pas de PyTorch), 15–20 img/s sur un CPU portable, fichiers de 24 Mo inclus dans le dépôt : `git clone` suffit | YOLOv8 (ultralytics) : plus précis mais ~2 Go à installer et plus lent sur CPU |
| Emplacement du traitement | **Sur une machine dédiée** (PC analyse) | Le PC capture reste léger (une webcam suffit, ex. Raspberry Pi), le calcul est sur la machine qui a le CPU, les spectateurs n'ont rien à installer | Traitement sur le PC capture : concentre toute la charge sur une seule machine et empêche l'architecture distribuée |
| Format des échanges | JPEG (images) + JSON (statistiques, réglages) | Standards, lisibles, supportés partout | Flux binaire maison : rien à gagner sur un réseau local |

---

## 10. Limites connues

- Le serveur web est celui de développement de Flask : suffisant pour une démonstration, pas pour une mise en production.
- Le MJPEG consomme plus de bande passante que du H.264 (environ 1 à 2 Mbit/s par spectateur en 640×480) ; le débit croît avec le nombre de spectateurs.
- YOLOv4-tiny est moins précis qu'un modèle complet, surtout sur les petits objets.
- Latence de bout en bout typique : 200 à 500 ms sur un Wi-Fi correct.
- Aucune authentification : toute personne sur le réseau peut voir le flux (acceptable pour un TP).
