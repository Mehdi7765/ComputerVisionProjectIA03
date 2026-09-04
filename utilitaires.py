"""
Petits outils partagés par capture.py et analyse.py.
"""
import socket
import time
import logging


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
    autre chose  -> chaîne (URL HTTP/RTSP ou chemin de fichier vidéo)
    """
    texte = str(valeur).strip()
    return int(texte) if texte.isdigit() else texte


class CompteurFPS:
    """Mesure un nombre d'images par seconde lissé sur une fenêtre glissante."""

    def __init__(self, fenetre=30):
        self._instants = []
        self._fenetre = fenetre

    def tic(self):
        """À appeler à chaque image traitée."""
        maintenant = time.time()
        self._instants.append(maintenant)
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
