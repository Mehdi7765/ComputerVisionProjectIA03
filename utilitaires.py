"""
Petits outils partagés par les scripts de diffusion et de lecture.
"""
import logging
import os
import socket
import threading
import time

# Pour lire un flux RTSP servi par ffmpeg en mode "listen", OpenCV doit
# utiliser le transport TCP (par défaut il tente l'UDP). Cette variable est
# lue par OpenCV au moment d'ouvrir la source ; on ne l'impose que si
# l'utilisateur ne l'a pas déjà définie.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

import cv2  # noqa: E402  (après la variable d'environnement ci-dessus)

# OpenCV affiche des avertissements internes à chaque tentative de connexion
# ratée ; on ne garde que les vraies erreurs.
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except AttributeError:
    pass


def adresse_ip_locale():
    """Renvoie l'adresse IP de cette machine sur le réseau local.

    Astuce classique : on "prépare" une connexion UDP vers une adresse
    extérieure (aucun paquet n'est réellement envoyé) et on lit l'adresse
    source que le système aurait utilisée. Fonctionne sous Linux, Windows et
    macOS, même sans accès Internet.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def source_video(valeur):
    """Convertit l'argument --source / --camera en source utilisable par OpenCV.

    "0", "1"...  -> entier (index de webcam)
    autre chose  -> chaîne (URL HTTP/RTSP, chemin de fichier, pipeline GStreamer)
    """
    texte = str(valeur).strip()
    return int(texte) if texte.isdigit() else texte


def ouvrir_source(source):
    """Ouvre une source vidéo avec le bon moteur OpenCV.

    - entier                      : webcam
    - "http://…", "rtsp://…", fichier : moteur FFMPEG (défaut d'OpenCV)
    - chaîne contenant " ! "      : pipeline GStreamer (variante diffusion_gstreamer.py)
    """
    if isinstance(source, str) and " ! " in source:
        return cv2.VideoCapture(source, cv2.CAP_GSTREAMER)
    if isinstance(source, str) and "://" in source:
        # moteur FFMPEG imposé : évite qu'OpenCV essaie d'autres moteurs
        # (et affiche des erreurs) quand la source est momentanément coupée
        return cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    return cv2.VideoCapture(source)


class LecteurDerniereImage(threading.Thread):
    """Lit une source en continu dans un thread et ne garde que la DERNIÈRE image.

    Pourquoi : cv2.VideoCapture met les images reçues en file d'attente. Si le
    traitement (YOLO) est plus lent que la caméra, cette file grossit et le
    retard s'accumule (plusieurs secondes après une minute). Ici on lit le flux
    au rythme de la caméra et on jette les images non traitées : le traitement
    porte toujours sur l'image la plus récente.

    Utilisation : `ret, image = lecteur.lire()` à la place de `ret, image = cap.read()`.
    Le thread libère lui-même la capture quand il s'arrête.
    """

    DELAI_SANS_IMAGE = 5.0   # secondes sans image avant de considérer le flux perdu

    def __init__(self, capture):
        super().__init__(daemon=True)
        self._capture = capture
        self._condition = threading.Condition()
        self._image = None
        self._numero = 0
        self._terminee = False
        self._arret_demande = False

    def run(self):
        while not self._arret_demande:
            ok, image = self._capture.read()
            if not ok:
                break
            with self._condition:
                self._image = image
                self._numero += 1
                self._condition.notify_all()
        self._capture.release()
        with self._condition:
            self._terminee = True
            self._condition.notify_all()

    def lire(self):
        """Attend une image plus récente que la précédente. Renvoie (False, None) si le flux est fini."""
        with self._condition:
            dernier = self._numero
            ok = self._condition.wait_for(
                lambda: self._numero != dernier or self._terminee,
                timeout=self.DELAI_SANS_IMAGE)
            if self._terminee or not ok:
                return False, None
            return True, self._image.copy()

    def arreter(self):
        self._arret_demande = True
        self.join(timeout=5)


class CompteurFPS:
    """Mesure un nombre d'images par seconde lissé sur une fenêtre glissante."""

    def __init__(self, fenetre=30):
        self._instants = []
        self._fenetre = fenetre

    def tic(self):
        """À appeler à chaque image traitée."""
        self._instants.append(time.time())
        if len(self._instants) > self._fenetre:
            self._instants.pop(0)

    @property
    def fps(self):
        if len(self._instants) < 2:
            return 0.0
        duree = self._instants[-1] - self._instants[0]
        return (len(self._instants) - 1) / duree if duree > 0 else 0.0


def reduire_logs_flask():
    """Évite que Flask affiche une ligne à chaque requête HTTP (bruit inutile)."""
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
