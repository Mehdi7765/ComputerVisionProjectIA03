import subprocess

def start_ffmpeg_rtsp_stream():
    camera_index = "0"

    # Commande FFmpeg pour capturer le flux de la caméra USB et le diffuser en RTSP
    ffmpeg_command = [
        "ffmpeg",
        "-f", "avfoundation",          # Utiliser avfoundation pour capturer la vidéo sur macOS
        "-framerate", "25",            # Framerate supporté par la caméra
        "-video_size", "320x240",      # Résolution supportée par la caméra
        "-i", camera_index,            # Indice de la caméra détectée
        "-vcodec", "libx264",          # Encodeur vidéo H.264
        "-preset", "ultrafast",        # Paramètre de vitesse pour minimiser la latence
        "-tune", "zerolatency",        # Optimise pour une faible latence
        "-f", "rtsp",                  # Format de sortie RTSP
        "-rtsp_flags", "listen",       # Indique à FFmpeg d'écouter les connexions entrantes RTSP
        "-rtsp_transport", "tcp",      # Utiliser TCP pour la transmission RTSP
        "rtsp://127.0.0.1:8554/stream"   # URL du flux RTSP (0.0.0.0 écoute sur toutes les interfaces)
    ]

    try:
        subprocess.run(ffmpeg_command)
    except Exception as e:
        print(f"Erreur lors de l'exécution de FFmpeg : {e}")

if __name__ == "__main__":
    start_ffmpeg_rtsp_stream()

