import cv2

def start_rtsp_stream():
    # Ouvrir le flux de la caméra USB (généralement /dev/video0 sur Linux, 0 pour la première caméra sur Windows/macOS)
    cap = cv2.VideoCapture(0)  # Remplacez 0 par l'index de votre caméra USB si nécessaire

    # Vérifiez si la caméra est ouverte correctement
    if not cap.isOpened():
        print("Erreur : Impossible d'ouvrir la caméra")
        return

    # Paramètres de GStreamer pour diffuser en RTSP
    gst_str = (
        "appsrc ! videoconvert ! video/x-raw,format=BGR ! queue ! "
        "x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! "
        "rtph264pay config-interval=1 pt=96 ! "
        "gdppay ! tcpserversink host=127.0.0.1 port=8554 sync=false async=false"
    )

    # Ouvrir un flux vidéo à l'aide de GStreamer
    out = cv2.VideoWriter(gst_str, cv2.CAP_GSTREAMER, 0, 30, (640, 480), True)

    if not out.isOpened():
        print("Erreur : Impossible d'ouvrir le flux RTSP")
        cap.release()
        return

    print("Diffusion en direct sur rtsp://127.0.0.1:8554")

    while True:
        # Capture d'image par image
        ret, frame = cap.read()
        if not ret:
            print("Erreur : Impossible de lire une image de la caméra")
            break

        # Affichage local (optionnel)
        cv2.imshow('USB Camera', frame)

        # Diffusion du frame via RTSP
        out.write(frame)

        # Arrêter la diffusion si l'utilisateur appuie sur 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Libérer les ressources
    cap.release()
    out.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_rtsp_stream()
