"""
diffusion_rtsp_ffmpeg.py — script fourni en TP, adapté.  RÔLE : CAPTURE (variante)
====================================================================================
Variante de diffusion : ffmpeg capture la webcam, l'encode en H.264 (débit
bien plus faible que le MJPEG) et la sert sur le réseau.

Lancement :
    python3 diffusion_rtsp_ffmpeg.py                 # webcam 0, HTTP/MPEG-TS sur le port 8554
    python3 diffusion_rtsp_ffmpeg.py --camera test   # mire de test, sans webcam
    python3 diffusion_rtsp_ffmpeg.py --mode rtsp --serveur-rtsp rtsp://127.0.0.1:8554/stream
Lecture côté analyse :
    python3 lecture_http.py --source http://<IP capture>:8554/stream    (mode http)
    python3 lecture_http.py --source rtsp://<IP capture>:8554/stream    (mode rtsp)

Modifications par rapport à la version d'origine (repérées par [MODIF]) :
  1. entrée selon le système : la version d'origine utilisait "avfoundation",
     qui n'existe que sur macOS ; on choisit v4l2 (Linux) / dshow (Windows) ;
  2. mode de sortie : la version d'origine comptait sur "-rtsp_flags listen"
     pour que ffmpeg serve lui-même le RTSP. Testé avec ffmpeg 5.1 : ce
     drapeau n'agit que sur la LECTURE RTSP ; en écriture ffmpeg se comporte
     en client et échoue ("Connection refused") s'il n'y a pas de serveur RTSP.
     Deux modes sont donc proposés :
       --mode http (défaut) : ffmpeg sert lui-même le flux H.264 (MPEG-TS) en
                              HTTP grâce à "-listen 1". Rien d'autre à installer.
       --mode rtsp          : ffmpeg POUSSE vers un serveur RTSP externe
                              (par ex. mediamtx) lancé à part.
  3. ffmpeg est relancé automatiquement s'il s'arrête (en mode http, ffmpeg
     quitte dès que son unique client se déconnecte) ;
  4. paramètres depuis config.py / ligne de commande ; "--camera test" pour
     tester sans webcam.
Limite du mode http : un seul lecteur à la fois (le PC d'analyse), ce qui
suffit puisque la consultation passe par lecture_http.py.
La version d'origine est conservée dans docs/scripts_origine/.
"""
import argparse    # [MODIF]
import platform    # [MODIF]
import subprocess
import sys         # [MODIF]
import time        # [MODIF]

import config                              # [MODIF]
from utilitaires import adresse_ip_locale  # [MODIF]


def options_entree(camera, largeur, hauteur, fps):
    """[MODIF] Options d'entrée ffmpeg adaptées au système d'exploitation."""
    taille = f"{largeur}x{hauteur}"
    if camera == "test":                       # mire de test intégrée à ffmpeg
        return ["-re", "-f", "lavfi", "-i", f"testsrc=size={taille}:rate={fps}"]

    systeme = platform.system()
    if systeme == "Darwin":                    # macOS : version d'origine
        return ["-f", "avfoundation", "-framerate", str(fps), "-video_size", taille, "-i", camera]
    if systeme == "Windows":                   # Windows : ffmpeg veut le NOM de la webcam
        nom = config.CAMERA_WINDOWS_DSHOW if camera.isdigit() else camera
        return ["-f", "dshow", "-framerate", str(fps), "-video_size", taille, "-i", f"video={nom}"]
    peripherique = f"/dev/video{camera}" if camera.isdigit() else camera   # Linux
    return ["-f", "v4l2", "-framerate", str(fps), "-video_size", taille, "-i", peripherique]


def start_ffmpeg_rtsp_stream(camera, mode, port, serveur_rtsp, largeur, hauteur, fps):
    # Commande FFmpeg pour capturer le flux de la caméra USB et le diffuser
    ffmpeg_command = [
        "ffmpeg",
        "-loglevel", "warning",
        *options_entree(camera, largeur, hauteur, fps),   # [MODIF] selon l'OS
        "-vcodec", "libx264",          # Encodeur vidéo H.264
        "-preset", "ultrafast",        # Paramètre de vitesse pour minimiser la latence
        "-tune", "zerolatency",        # Optimise pour une faible latence
        "-pix_fmt", "yuv420p",         # [MODIF] format de pixels accepté par tous les décodeurs
        "-g", str(fps),                # [MODIF] une image clé par seconde : un lecteur accroche vite
    ]
    ip = adresse_ip_locale()
    if mode == "http":
        # [MODIF] ffmpeg sert lui-même le flux (un client à la fois)
        ffmpeg_command += ["-f", "mpegts", "-listen", "1", f"http://0.0.0.0:{port}/stream"]
        url_lecture = f"http://{ip}:{port}/stream"
    else:
        # [MODIF] ffmpeg pousse vers un serveur RTSP externe (mediamtx, etc.)
        ffmpeg_command += ["-f", "rtsp", "-rtsp_transport", "tcp", serveur_rtsp]
        url_lecture = serveur_rtsp

    print("=" * 62)
    print(f"  PC CAPTURE prêt (diffusion_rtsp_ffmpeg.py, mode {mode}, H.264)")
    print(f"  Le PC d'analyse lance : python3 lecture_http.py --source {url_lecture}")
    print("  (Ctrl+C pour arrêter)")
    print("=" * 62)

    # [MODIF] boucle de relance : en mode http, ffmpeg quitte quand son client
    # se déconnecte ; on le relance pour que l'analyse puisse se reconnecter.
    while True:
        try:
            resultat = subprocess.run(ffmpeg_command)
        except FileNotFoundError:
            print("Erreur : ffmpeg introuvable. Installez-le (apt install ffmpeg, brew install ffmpeg, "
                  "winget install ffmpeg) et vérifiez qu'il est dans le PATH.")
            return
        except KeyboardInterrupt:
            print("\nArrêt demandé.")
            return
        except Exception as e:
            print(f"Erreur lors de l'exécution de FFmpeg : {e}")
            return
        print(f"ffmpeg s'est arrêté (code {resultat.returncode}), relance dans "
              f"{config.DELAI_RECONNEXION:.0f} s...")
        time.sleep(config.DELAI_RECONNEXION)


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    parseur = argparse.ArgumentParser(description="Diffuse la webcam en H.264 avec ffmpeg.")   # [MODIF]
    parseur.add_argument("--camera", default=str(config.INDEX_CAMERA),
                         help="index de webcam (0, 1...), chemin/nom de périphérique, ou 'test' (mire)")
    parseur.add_argument("--mode", choices=("http", "rtsp"), default="http")
    parseur.add_argument("--port", type=int, default=config.RTSP_PORT, help="port d'écoute en mode http")
    parseur.add_argument("--serveur-rtsp", default=f"rtsp://127.0.0.1:{config.RTSP_PORT}/stream",
                         help="URL du serveur RTSP externe (mode rtsp)")
    parseur.add_argument("--largeur", type=int, default=config.LARGEUR_CAPTURE)
    parseur.add_argument("--hauteur", type=int, default=config.HAUTEUR_CAPTURE)
    args = parseur.parse_args()
    start_ffmpeg_rtsp_stream(args.camera, args.mode, args.port, args.serveur_rtsp,
                             args.largeur, args.hauteur, config.IMAGES_PAR_SECONDE)
