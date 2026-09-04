"""
diffusion_gstreamer.py — script fourni en TP, adapté.  RÔLE : CAPTURE (variante)
=================================================================================
Variante de diffusion : la webcam est encodée en H.264 par GStreamer et envoyée
sur TCP (paquets RTP encapsulés en GDP). Débit bien plus faible que le MJPEG,
mais NON lisible par un navigateur : c'est pour cela que diffusion_http.py
reste la diffusion principale du projet, celle-ci sert de comparaison.

Prérequis (émetteur ET lecteur) : un OpenCV compilé avec GStreamer
    Debian/Ubuntu : sudo apt install python3-opencv gstreamer1.0-plugins-good \
                        gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav
    (le paquet pip opencv-python ne suffit pas)

Lancement :
    python3 diffusion_gstreamer.py                 # webcam 0, port 8555
Lecture côté analyse (pipeline GStreamer défini dans config.py) :
    python3 lecture_http.py --source "$(python3 -c 'import config; print(config.PIPELINE_LECTURE_GSTREAMER)')"

Modifications par rapport à la version d'origine (repérées par [MODIF]) :
  1. tcpserversink host=127.0.0.1 -> 0.0.0.0 : sinon seule la machine locale
     pouvait se connecter, ce qui rendait la diffusion réseau impossible ;
  2. format vidéo BGR -> I420 avant x264enc : l'encodeur n'accepte pas le BGR,
     la version d'origine échouait à ouvrir le flux ;
  3. redimensionnement systématique à la taille annoncée au VideoWriter (sinon
     les images d'une webcam d'une autre résolution sont silencieusement rejetées) ;
  4. fenêtre locale optionnelle, source et port depuis config.py / ligne de commande.
La version d'origine est conservée dans docs/scripts_origine/.
"""
import argparse   # [MODIF]
import sys        # [MODIF]

import cv2

import config                                             # [MODIF]
from utilitaires import adresse_ip_locale, source_video   # [MODIF]


def start_rtsp_stream(source, port, largeur, hauteur, fps, afficher):
    # Ouvrir le flux de la caméra USB (généralement /dev/video0 sur Linux, 0 pour la première caméra sur Windows/macOS)
    cap = cv2.VideoCapture(source)  # Remplacez 0 par l'index de votre caméra USB si nécessaire

    # Vérifiez si la caméra est ouverte correctement
    if not cap.isOpened():
        print("Erreur : Impossible d'ouvrir la caméra")
        return

    # Paramètres de GStreamer pour diffuser en H.264 sur TCP
    gst_str = (
        "appsrc ! videoconvert ! video/x-raw,format=I420 ! queue ! "                      # [MODIF] I420 au lieu de BGR
        "x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! "
        "rtph264pay config-interval=1 pt=96 ! "
        f"gdppay ! tcpserversink host=0.0.0.0 port={port} sync=false async=false"        # [MODIF] 0.0.0.0 + port config
    )

    # Ouvrir un flux vidéo à l'aide de GStreamer
    out = cv2.VideoWriter(gst_str, cv2.CAP_GSTREAMER, 0, fps, (largeur, hauteur), True)

    if not out.isOpened():
        print("Erreur : Impossible d'ouvrir le flux GStreamer "
              "(OpenCV est-il compilé avec GStreamer ? plugins x264enc/rtph264pay installés ?)")
        cap.release()
        return

    ip = adresse_ip_locale()
    print("=" * 62)
    print("  PC CAPTURE prêt (diffusion_gstreamer.py, H.264 sur TCP)")
    print(f"  Le PC d'analyse doit utiliser ADRESSE_PC_CAPTURE = {ip} dans config.py")
    print(f"  et lancer : python3 lecture_http.py --source \"tcpclientsrc host={ip} port={port} ! "
          "gdpdepay ! rtph264depay ! avdec_h264 ! videoconvert ! appsink drop=true max-buffers=1\"")
    print("  (touche q dans la fenêtre ou Ctrl+C pour arrêter)")
    print("=" * 62)

    while True:
        # Capture d'image par image
        ret, frame = cap.read()
        if not ret:
            print("Erreur : Impossible de lire une image de la caméra")
            break

        # [MODIF] la taille doit être exactement celle annoncée au VideoWriter
        if frame.shape[1] != largeur or frame.shape[0] != hauteur:
            frame = cv2.resize(frame, (largeur, hauteur))

        # Diffusion du frame
        out.write(frame)

        # Affichage local (optionnel)
        if afficher:   # [MODIF]
            try:
                cv2.imshow('USB Camera', frame)
                # Arrêter la diffusion si l'utilisateur appuie sur 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except cv2.error:
                afficher = False   # pas d'écran : on continue sans fenêtre

    # Libérer les ressources
    cap.release()
    out.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    parseur = argparse.ArgumentParser(description="Diffuse la webcam en H.264 sur TCP via GStreamer.")   # [MODIF]
    parseur.add_argument("--camera", default=str(config.INDEX_CAMERA))
    parseur.add_argument("--port", type=int, default=config.GSTREAMER_PORT)
    parseur.add_argument("--largeur", type=int, default=config.LARGEUR_CAPTURE)
    parseur.add_argument("--hauteur", type=int, default=config.HAUTEUR_CAPTURE)
    parseur.add_argument("--sans-fenetre", action="store_true")
    args = parseur.parse_args()
    start_rtsp_stream(source_video(args.camera), args.port, args.largeur, args.hauteur,
                      config.IMAGES_PAR_SECONDE, afficher=not args.sans_fenetre)
