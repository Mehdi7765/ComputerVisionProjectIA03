# Checklist de démonstration — IA03

Objectif : le prof se connecte au réseau avec son téléphone, ouvre une adresse et voit le flux annoté **sans qu'on touche à rien** (critère B, 3 points).

## La veille

- [ ] Le binôme est ajouté comme **collaborateur** du dépôt privé (GitHub → Settings → Collaborators), et a fait `git clone` + installation (voir README § 3) sur **son** PC.
- [ ] Sur chaque PC, test en solo : `python lecture_http.py --source 0` → l'interface s'affiche sur `http://localhost:8000/` avec des boîtes.
- [ ] **Pare-feu** ouvert sur les deux PC (ports 5000 et 8000 en entrée). Windows : PowerShell administrateur
      `New-NetFirewallRule -DisplayName "IA03" -Direction Inbound -LocalPort 5000,8000 -Protocol TCP -Action Allow`
      Linux : `sudo ufw allow 5000,8000/tcp` (ou rien si `ufw` est absent).
- [ ] Test à deux PC sur le réseau prévu : capture sur l'un, analyse sur l'autre, consultation depuis un téléphone. Si le `ping` entre les PC échoue → le réseau isole les clients : prévoir un **partage de connexion** (voir plan B).
- [ ] Chargeurs branchés le jour J (l'analyse consomme du CPU, un portable sur batterie ralentit).
- [ ] Une vidéo de secours sur le PC capture (`--camera video.mp4`) si la webcam pose problème.

## Le jour J, dans l'ordre

1. **Réseau** : les deux PC et le téléphone du prof sur le **même Wi-Fi**. Si le Wi-Fi de l'école isole les clients, ouvrir un partage de connexion sur un téléphone et y connecter les deux PC ; le prof s'y connectera aussi (lui donner le mot de passe du partage).
2. **PC capture** : `python diffusion_http.py` → noter l'adresse affichée (`http://<IP>:5000/video_feed`). Vérifier dans son navigateur que `http://localhost:5000/` montre la webcam.
3. **PC analyse** : `python lecture_http.py --source http://<IP capture>:5000/video_feed` → attendre « PC ANALYSE prêt ». Le terminal affiche l'adresse `http://<IP analyse>:8000/` **et un QR code**.
4. **Vérification croisée** avant l'arrivée du prof : ouvrir `http://<IP analyse>:8000/` depuis un téléphone à nous. Si ça marche, ça marchera pour le prof.
5. **Prof** : lui montrer le QR code (ou lui dicter l'adresse). Ne rien toucher.

## Ce qu'on montre, dans l'ordre (5 minutes)

1. Les **trois appareils** : webcam sur le PC capture, terminal du PC analyse, téléphone du prof (critère A3 : capture, analyse et consultation sur des machines distinctes).
2. Les **boîtes** qui suivent les objets en direct (A2) et le badge « source connectée ».
3. Les **indicateurs** : images/s, latence, compteur par classe.
4. Un **réglage à chaud** : monter le seuil à 0.8 → moins de boîtes ; taper `person` dans le filtre → seules les personnes restent.
5. **Changement de modèle** dans la liste déroulante → le flux ne s'interrompt pas, la latence change.
6. **Taille d'entrée** 320 → 608 : latence et précision évoluent en direct.
7. **Deuxième spectateur** : ouvrir la page sur un second téléphone / PC en même temps.
8. **Reprise automatique** : Ctrl+C sur le PC capture → badge « source coupée » ; relancer → le flux revient tout seul, sans toucher au téléphone.
9. Si le temps le permet : la **variante H.264** (`python diffusion_rtsp_ffmpeg.py` puis `lecture_http.py --source http://<IP capture>:8554/stream`) pour appuyer la justification des choix du rapport.

## Plans B

| Problème | Réaction |
|---|---|
| Le téléphone du prof n'atteint pas le PC analyse | Vérifier qu'il est sur le même Wi-Fi ; basculer tout le monde sur le partage de connexion |
| Le PC analyse n'atteint pas le PC capture (badge rouge) | `ping <IP capture>` ; si échec → pare-feu ou isolation ; relire l'IP affichée par `diffusion_http.py` (elle change avec le réseau) |
| La webcam ne s'ouvre pas | Fermer Teams/Zoom/navigateur ; `--camera 1` ; sinon `--camera video.mp4` |
| Image saccadée | `--taille 320` sur l'analyse, ou `--largeur 320 --hauteur 240` sur la capture |
| Un des deux PC lâche | Tout sur un seul PC : `python diffusion_http.py` + `python lecture_http.py --source http://127.0.0.1:5000/video_feed` (le téléphone reste un appareil distinct) |

## Phrases utiles pour les questions

- *Pourquoi MJPEG et pas RTSP ?* → Lisible par un navigateur sans logiciel (critère B), un seul port, multi-clients ; on a implémenté et mesuré les variantes H.264 (ffmpeg, GStreamer) avant de choisir.
- *Pourquoi YOLOv4-tiny ?* → Temps réel sur CPU, aucune dépendance lourde, poids dans le dépôt ; YOLOv8 aurait demandé 2 Go de PyTorch.
- *Le traitement est-il vraiment déporté ?* → Oui : le PC capture ne fait que diffuser (montrer `top` / le gestionnaire de tâches), le modèle tourne sur le PC analyse, le téléphone n'exécute rien.
- *Que se passe-t-il si la caméra est plus rapide que le modèle ?* → On ne traite que la dernière image reçue, le retard ne s'accumule pas.
