"""
DIFFUSEUR MJPEG MULTI-SPECTATEURS
=================================
Utilisé à la fois par capture.py (flux brut) et analyse.py (flux annoté).

Principe :
  - une seule image JPEG "courante" est gardée en mémoire ;
  - le producteur (webcam ou modèle) appelle `publier(image)` à chaque
    nouvelle image ;
  - chaque spectateur connecté en HTTP reçoit cette image dès qu'elle est
    renouvelée.

Conséquences :
  - la source n'est lue et l'image n'est encodée QU'UNE FOIS, quel que soit
    le nombre de spectateurs (téléphone du prof, navigateur, PC analyse...) ;
  - un spectateur lent ne ralentit pas les autres : il saute simplement des
    images, il n'y a pas de file d'attente qui accumule de la latence.

Format envoyé : "multipart/x-mixed-replace" (MJPEG), compris nativement par
tous les navigateurs via une simple balise <img src="/video_feed">, et par
OpenCV via cv2.VideoCapture(url).
"""
import threading
import cv2
from flask import Response


class DiffuseurMJPEG:

    def __init__(self, qualite_jpeg=80):
        self._condition = threading.Condition()   # réveille les spectateurs
        self._jpeg = None                         # dernière image encodée
        self._numero = 0                          # compteur d'images publiées
        self._qualite = qualite_jpeg

    def publier(self, image):
        """Encode l'image en JPEG et la propose à tous les spectateurs."""
        ok, tampon = cv2.imencode(".jpg", image,
                                  [cv2.IMWRITE_JPEG_QUALITY, self._qualite])
        if not ok:
            return
        with self._condition:
            self._jpeg = tampon.tobytes()
            self._numero += 1
            self._condition.notify_all()

    def flux(self):
        """Générateur : produit les morceaux du flux MJPEG pour UN spectateur."""
        dernier_envoye = 0
        while True:
            with self._condition:
                # On attend une image plus récente que la dernière envoyée.
                # Le timeout évite de bloquer pour toujours si la source coupe.
                self._condition.wait_for(
                    lambda: self._numero != dernier_envoye, timeout=1.0)
                if self._jpeg is None or self._numero == dernier_envoye:
                    continue
                jpeg = self._jpeg
                dernier_envoye = self._numero

            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n"
                   b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                   + jpeg + b"\r\n")

    def reponse_http(self):
        """Réponse Flask prête à renvoyer depuis une route."""
        return Response(self.flux(),
                        mimetype="multipart/x-mixed-replace; boundary=frame")
