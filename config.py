"""
CONFIGURATION CENTRALE DU PROJET
================================
Tous les paramètres réseau et modèle sont regroupés ici : aucune adresse,
aucun port n'est écrit en dur dans les autres fichiers.

Chaque script accepte aussi des options en ligne de commande (--source,
--port, --camera...) qui PRENNENT LE DESSUS sur ces valeurs. En séance, on
peut donc changer d'adresse sans toucher à ce fichier :
    python3 analyse.py --source http://192.168.1.42:5000/video_feed
"""
import os

# Dossier du projet (pour retrouver les fichiers quel que soit le répertoire
# depuis lequel on lance les scripts)
DOSSIER_PROJET = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
#  RÉSEAU
# ---------------------------------------------------------------------------
# "0.0.0.0" = le serveur écoute sur TOUTES les interfaces réseau de la machine.
# C'est ce qui le rend accessible depuis les autres PC / téléphones du réseau.
HOTE_ECOUTE = "0.0.0.0"

# --- Rôle CAPTURE : le PC qui possède la webcam ---
CAPTURE_PORT = 5000

# --- Rôle ANALYSE : le PC qui fait tourner YOLO ---
# Adresse IP (réseau local) du PC capture. À adapter à votre réseau :
# sur le PC capture, la commande `hostname -I` (Linux) ou `ipconfig` (Windows)
# donne cette adresse. capture.py l'affiche aussi au démarrage.
ADRESSE_PC_CAPTURE = "172.20.10.11"
URL_FLUX_BRUT = f"http://{ADRESSE_PC_CAPTURE}:{CAPTURE_PORT}/video_feed"
ANALYSE_PORT = 8000

# Temps d'attente (secondes) avant de retenter une connexion à la source
# vidéo si elle coupe (reprise automatique).
DELAI_RECONNEXION = 2.0

# ---------------------------------------------------------------------------
#  CAMÉRA
# ---------------------------------------------------------------------------
INDEX_CAMERA = 0          # 0 = première webcam détectée (1, 2... pour les autres)
LARGEUR_CAPTURE = 640
HAUTEUR_CAPTURE = 480

# Qualité de compression JPEG (1-100). Plus bas = moins de débit réseau,
# mais image plus dégradée. 80 est un bon compromis.
QUALITE_JPEG = 80

# ---------------------------------------------------------------------------
#  MODÈLE YOLO
# ---------------------------------------------------------------------------
DOSSIER_MODELES = os.path.join(DOSSIER_PROJET, "modeles")
FICHIER_CFG     = os.path.join(DOSSIER_MODELES, "yolov4-tiny.cfg")
FICHIER_POIDS   = os.path.join(DOSSIER_MODELES, "yolov4-tiny.weights")
FICHIER_CLASSES = os.path.join(DOSSIER_MODELES, "coco.names")

# Taille de l'image en entrée du réseau. Compromis vitesse / précision :
#   320 = rapide, 416 = équilibré, 608 = précis mais lent.
# Modifiable à chaud depuis l'interface web.
TAILLE_ENTREE = 416
TAILLES_ENTREE_POSSIBLES = (320, 416, 608)

# Confiance minimale (0-1) pour conserver une détection. Modifiable à chaud.
SEUIL_CONFIANCE = 0.5

# Seuil de recouvrement pour la suppression des boîtes en double (NMS).
SEUIL_NMS = 0.4
