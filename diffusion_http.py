"""
diffusion_http.py — script fourni en TP, adapté.  RÔLE : CAPTURE
=================================================================
Lit la webcam et la diffuse sur le réseau en MJPEG (une suite d'images JPEG
sur HTTP), lisible par un navigateur et par OpenCV.

À lancer sur le PC qui possède la caméra :
    python3 diffusion_http.py                      # webcam 0, port 5000 (config.py)
    python3 diffusion_http.py --camera 1
    python3 diffusion_http.py --camera video.mp4   # fichier vidéo (test sans webcam)

Pages servies :
    /             page de contrôle (aperçu + adresse à communiquer au PC d'analyse)
    /video_feed   le flux MJPEG brut
    /etat         état en JSON (connexion caméra, résolution, images/s)

Modifications par rapport à la version d'origine (repérées par [MODIF]) :
  1. la caméra est ouverte UNE seule fois et lue par un thread, au lieu d'être
     ouverte dans generate_frames() à chaque client : indispensable pour que
     le PC d'analyse ET un navigateur de contrôle lisent le flux en même temps ;
  2. reprise automatique si la caméra coupe ;
  3. source, résolution, qualité JPEG et port viennent de config.py / de la
     ligne de commande (plus d'adresse en dur) ;
  4. la page d'accueil, présente en commentaire dans l'original, est réactivée ;
  5. route /etat pour le diagnostic.
La version d'origine est conservée dans docs/scripts_origine/.
"""
import argparse    # [MODIF]
import sys         # [MODIF]
import threading   # [MODIF]
import time        # [MODIF]

import cv2
from flask import Flask, Response, jsonify

import config                                                                     # [MODIF]
from utilitaires import adresse_ip_locale, source_video, CompteurFPS, reduire_logs_flask  # [MODIF]

app = Flask(__name__)

# [MODIF] Image courante partagée entre le thread de capture et les clients.
derniere_image = {"frame": None, "numero": 0}
nouvelle_image = threading.Condition()
etat = {"source": None, "connectee": False, "resolution": "", "fps": 0.0}
compteur = CompteurFPS()


def capturer_en_continu(source, largeur, hauteur):
    """[MODIF] Thread de capture : lit la caméra en boucle et publie chaque image."""
    while True:   # boucle externe = reprise automatique si la caméra coupe
        camera = cv2.VideoCapture(source)   # Indice de la caméra (0 pour la première caméra détectée)
        if isinstance(source, int):
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, largeur)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, hauteur)

        if not camera.isOpened():
            etat["connectee"] = False
            print(f"Impossible d'ouvrir la source {source!r}, nouvel essai dans "
                  f"{config.DELAI_RECONNEXION:.0f} s")
            time.sleep(config.DELAI_RECONNEXION)
            continue

        etat["connectee"] = True
        print(f"Source {source!r} ouverte")
        while True:
            # Capture frame-by-frame
            success, frame = camera.read()
            if not success:
                break
            with nouvelle_image:
                derniere_image["frame"] = frame
                derniere_image["numero"] += 1
                nouvelle_image.notify_all()
            etat["resolution"] = f"{frame.shape[1]}x{frame.shape[0]}"
            compteur.tic()
            etat["fps"] = round(compteur.fps, 1)

        camera.release()
        etat["connectee"] = False
        print("Source perdue, reconnexion...")
        time.sleep(config.DELAI_RECONNEXION)


def generate_frames():
    """Génère le flux MJPEG pour UN client (structure d'origine conservée)."""
    dernier_envoye = 0
    while True:
        # [MODIF] on attend une image plus récente que la dernière envoyée à ce
        # client (au lieu de lire la caméra ici) ; le timeout évite de bloquer
        # indéfiniment si la caméra est coupée.
        with nouvelle_image:
            nouvelle_image.wait_for(lambda: derniere_image["numero"] != dernier_envoye, timeout=1.0)
            frame = derniere_image["frame"]
            if frame is None or derniere_image["numero"] == dernier_envoye:
                continue
            dernier_envoye = derniere_image["numero"]

        # Encode the frame in JPEG format
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, config.QUALITE_JPEG])  # [MODIF] qualité réglable
        if not ret:
            continue
        frame = buffer.tobytes()

        # Yield the output frame in byte format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    # Route for the video feed
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    # Main page with the video feed
    # [MODIF] bloc présent en commentaire dans l'original, réactivé et complété
    # avec l'adresse exacte à donner au PC d'analyse.
    ip, port = adresse_ip_locale(), app.config["PORT"]
    return f'''
    <html>
    <head>
        <title>USB Camera Stream</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>body{{font-family:system-ui,sans-serif;background:#111;color:#eee;margin:0;padding:1rem}}
               code{{background:#333;padding:.2rem .4rem;border-radius:4px}} img{{max-width:100%;border-radius:8px}}</style>
    </head>
    <body>
        <h1>USB Camera Stream — flux brut</h1>
        <p>Adresse du flux à donner au PC d'analyse : <code>http://{ip}:{port}/video_feed</code></p>
        <img src="/video_feed" width="640" height="480">
        <p><a href="/etat" style="color:#8cf">/etat</a> (JSON)</p>
    </body>
    </html>
    '''


@app.route('/etat')
def etat_json():
    # [MODIF] état de la capture, pour diagnostiquer depuis une autre machine
    return jsonify(etat)


if __name__ == '__main__':
    sys.stdout.reconfigure(line_buffering=True)

    # [MODIF] source, résolution, qualité et port : config.py ou ligne de commande
    parseur = argparse.ArgumentParser(description="Diffuse la webcam en MJPEG sur le réseau.")
    parseur.add_argument("--camera", default=str(config.INDEX_CAMERA),
                         help="index de webcam (0, 1...), fichier vidéo ou URL")
    parseur.add_argument("--port", type=int, default=config.CAPTURE_PORT)
    parseur.add_argument("--largeur", type=int, default=config.LARGEUR_CAPTURE)
    parseur.add_argument("--hauteur", type=int, default=config.HAUTEUR_CAPTURE)
    args = parseur.parse_args()

    source = source_video(args.camera)
    etat["source"] = str(source)
    app.config["PORT"] = args.port
    reduire_logs_flask()
    threading.Thread(target=capturer_en_continu,
                     args=(source, args.largeur, args.hauteur), daemon=True).start()

    ip = adresse_ip_locale()
    print("=" * 62)
    print("  PC CAPTURE prêt (diffusion_http.py)")
    print(f"  Flux à donner au PC d'analyse :  http://{ip}:{args.port}/video_feed")
    print(f"  Page de contrôle :               http://{ip}:{args.port}/")
    print("  (Ctrl+C pour arrêter)")
    print("=" * 62)

    # Démarrer le serveur Flask : 0.0.0.0 = accessible depuis tout le réseau
    app.run(host=config.HOTE_ECOUTE, port=args.port, threaded=True)
