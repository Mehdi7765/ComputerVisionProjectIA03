"""
CONFIGURATION CENTRALE DU PROJET
================================
Tous les paramètres réseau et modèle sont regroupés ici : aucune adresse,
aucun port n'est écrit en dur dans les autres fichiers.

Chaque script accepte aussi des options en ligne de commande (--source,
--port, --camera...) qui PRENNENT LE DESSUS sur ces valeurs. En séance, on
peut donc changer d'adresse sans toucher à ce fichier :
    python3 lecture_http.py --source http://192.168.1.42:5000/video_feed
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

# Adresse IP (réseau local) du PC qui diffuse la caméra. À adapter à votre
# réseau : diffusion_http.py l'affiche au démarrage ; sinon `hostname -I`
# (Linux), `ipconfig` (Windows), `ifconfig` (macOS).
ADRESSE_PC_CAPTURE = "172.20.10.11"

# --- Diffusion principale : HTTP / MJPEG (diffusion_http.py) ---
CAPTURE_PORT = 5000
URL_FLUX_BRUT = f"http://{ADRESSE_PC_CAPTURE}:{CAPTURE_PORT}/video_feed"

# --- Variante : H.264 via ffmpeg (diffusion_rtsp_ffmpeg.py) ---
RTSP_PORT = 8554
URL_FLUX_FFMPEG = f"http://{ADRESSE_PC_CAPTURE}:{RTSP_PORT}/stream"   # mode http (défaut)
URL_FLUX_RTSP = f"rtsp://{ADRESSE_PC_CAPTURE}:{RTSP_PORT}/stream"     # mode rtsp (serveur externe)
# Sous Windows, ffmpeg a besoin du NOM de la webcam (pas d'un index) :
#   ffmpeg -list_devices true -f dshow -i dummy
CAMERA_WINDOWS_DSHOW = "Integrated Camera"

# --- Variante : H.264 sur TCP via GStreamer (diffusion_gstreamer.py) ---
# Nécessite un OpenCV compilé avec GStreamer (paquet python3-opencv de
# Debian/Ubuntu : oui ; opencv-python de pip : non).
GSTREAMER_PORT = 8555
PIPELINE_LECTURE_GSTREAMER = (
    f"tcpclientsrc host={ADRESSE_PC_CAPTURE} port={GSTREAMER_PORT} ! gdpdepay ! "
    "rtph264depay ! avdec_h264 ! videoconvert ! appsink drop=true max-buffers=1"
)

# --- Analyse : interface web + flux annoté (lecture_http.py) ---
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
IMAGES_PAR_SECONDE = 25   # utilisé par les variantes ffmpeg / GStreamer

# Qualité de compression JPEG (1-100) du flux MJPEG. Plus bas = moins de
# débit réseau, mais image plus dégradée. 80 est un bon compromis.
QUALITE_JPEG = 80

# ---------------------------------------------------------------------------
#  MODÈLE YOLO
# ---------------------------------------------------------------------------
DOSSIER_MODELES = os.path.join(DOSSIER_PROJET, "modeles")
FICHIER_CLASSES = os.path.join(DOSSIER_MODELES, "coco.names")   # 80 classes, communes aux modèles

# Modèles disponibles (changement possible à chaud depuis l'interface web).
# Tous sont au format Darknet (.cfg + .weights) et entraînés sur COCO.
MODELES = {
    "yolov4-tiny": {"cfg": "yolov4-tiny.cfg", "poids": "yolov4-tiny.weights",
                    "description": "équilibré, le plus précis des deux (défaut)"},
    "yolov3-tiny": {"cfg": "yolov3-tiny.cfg", "poids": "yolov3-tiny.weights",
                    "description": "plus ancien, un peu plus rapide, moins précis"},
}
MODELE_DEFAUT = "yolov4-tiny"


def chemins_modele(nom):
    """Renvoie (chemin_cfg, chemin_poids) du modèle `nom` (clé de MODELES)."""
    m = MODELES[nom]
    return (os.path.join(DOSSIER_MODELES, m["cfg"]),
            os.path.join(DOSSIER_MODELES, m["poids"]))


FICHIER_CFG, FICHIER_POIDS = chemins_modele(MODELE_DEFAUT)

# Taille de l'image en entrée du réseau. Compromis vitesse / précision :
#   320 = rapide, 416 = équilibré, 608 = précis mais lent.
# Modifiable à chaud depuis l'interface web.
TAILLE_ENTREE = 416
TAILLES_ENTREE_POSSIBLES = (320, 416, 608)

# Confiance minimale (0-1) pour conserver une détection. Modifiable à chaud.
SEUIL_CONFIANCE = 0.5

# Seuil de recouvrement pour la suppression des boîtes en double (NMS).
SEUIL_NMS = 0.4
