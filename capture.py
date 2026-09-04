"""
RÔLE 1 — CAPTURE : lit la webcam et la diffuse sur le réseau en MJPEG.
=======================================================================
À lancer sur le PC qui possède la caméra.

    python3 capture.py                      # webcam 0, port 5000 (config.py)
    python3 capture.py --camera 1           # une autre webcam
    python3 capture.py --camera video.mp4   # un fichier vidéo (test sans webcam)
    python3 capture.py --port 5001

Une fois lancé, le flux est disponible pour tout le réseau à l'adresse
affichée au démarrage, par exemple  http://172.20.10.11:5000/video_feed
C'est cette adresse qu'il faut donner au PC d'analyse (--source).

Pages servies :
    /             petite page de contrôle (aperçu du flux + adresse à communiquer)
    /video_feed   le flux MJPEG brut (lu par analyse.py ou un navigateur)
    /etat         état en JSON (connexion caméra, résolution, images/s)
"""
import argparse
import sys
import threading
import time

import cv2
from flask import Flask, jsonify

import config
from diffuseur import DiffuseurMJPEG
from utilitaires import adresse_ip_locale, source_video, CompteurFPS, reduire_logs_flask

app = Flask(__name__)
diffuseur = None                      # créé dans main() avec la qualité choisie
compteur = CompteurFPS()
etat = {"source": None, "connectee": False, "resolution": "", "fps": 0.0}


# --------------------------------------------------------------------------- #
#  Thread de capture : lit la caméra en continu et publie chaque image.
#  Si la caméra coupe (câble débranché, fichier terminé...), on retente
#  automatiquement au lieu de planter : reprise sans intervention.
# --------------------------------------------------------------------------- #
def boucle_capture(source, largeur, hauteur):
    while True:
        capture = cv2.VideoCapture(source)
        if isinstance(source, int):   # résolution réglable seulement pour une webcam
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, largeur)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, hauteur)

        if not capture.isOpened():
            etat["connectee"] = False
            print(f"[capture] impossible d'ouvrir la source {source!r}, "
                  f"nouvel essai dans {config.DELAI_RECONNEXION:.0f} s")
            time.sleep(config.DELAI_RECONNEXION)
            continue

        etat["connectee"] = True
        print(f"[capture] source {source!r} ouverte")
        while True:
            ok, image = capture.read()
            if not ok:
                break
            etat["resolution"] = f"{image.shape[1]}x{image.shape[0]}"
            compteur.tic()
            etat["fps"] = round(compteur.fps, 1)
            diffuseur.publier(image)

        capture.release()
        etat["connectee"] = False
        print("[capture] source perdue, reconnexion...")
        time.sleep(config.DELAI_RECONNEXION)


# --------------------------------------------------------------------------- #
#  Routes HTTP
# --------------------------------------------------------------------------- #
@app.route("/")
def accueil():
    ip = adresse_ip_locale()
    port = app.config["PORT"]
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Capture - flux brut</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{{font-family:system-ui,sans-serif;background:#111;color:#eee;margin:0;padding:1rem}}
code{{background:#333;padding:.2rem .4rem;border-radius:4px}} img{{max-width:100%;border-radius:8px}}</style></head>
<body><h2>PC capture &mdash; flux brut de la webcam</h2>
<p>Adresse du flux à donner au PC d'analyse :
<code>http://{ip}:{port}/video_feed</code></p>
<img src="/video_feed" alt="flux webcam">
<p><a href="/etat" style="color:#8cf">/etat</a> (JSON)</p></body></html>"""


@app.route("/video_feed")
def video_feed():
    return diffuseur.reponse_http()


@app.route("/etat")
def etat_json():
    return jsonify(etat)


# --------------------------------------------------------------------------- #
def main():
    global diffuseur
    sys.stdout.reconfigure(line_buffering=True)   # messages visibles même si la sortie est redirigée

    parseur = argparse.ArgumentParser(description="Diffuse la webcam en MJPEG sur le réseau.")
    parseur.add_argument("--camera", default=str(config.INDEX_CAMERA),
                         help="index de webcam (0, 1...), fichier vidéo ou URL")
    parseur.add_argument("--port", type=int, default=config.CAPTURE_PORT)
    parseur.add_argument("--largeur", type=int, default=config.LARGEUR_CAPTURE)
    parseur.add_argument("--hauteur", type=int, default=config.HAUTEUR_CAPTURE)
    parseur.add_argument("--qualite", type=int, default=config.QUALITE_JPEG,
                         help="qualité JPEG 1-100 (plus bas = moins de débit)")
    args = parseur.parse_args()

    source = source_video(args.camera)
    etat["source"] = str(source)
    diffuseur = DiffuseurMJPEG(qualite_jpeg=args.qualite)
    app.config["PORT"] = args.port
    reduire_logs_flask()

    threading.Thread(target=boucle_capture,
                     args=(source, args.largeur, args.hauteur), daemon=True).start()

    ip = adresse_ip_locale()
    print("=" * 62)
    print("  PC CAPTURE prêt")
    print(f"  Flux à donner au PC d'analyse :  http://{ip}:{args.port}/video_feed")
    print(f"  Page de contrôle :               http://{ip}:{args.port}/")
    print("  (Ctrl+C pour arrêter)")
    print("=" * 62)
    app.run(host=config.HOTE_ECOUTE, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
