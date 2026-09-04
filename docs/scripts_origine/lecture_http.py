import cv2

def read_http_stream(url):
    # Ouvrir le flux vidéo HTTP avec OpenCV
    cap = cv2.VideoCapture(url)

    while True:
        # Lire les images du flux
        ret, frame = cap.read()
        if not ret:
            print("Erreur de lecture du flux vidéo.")
            break

        #modifier l'image
        text = "image avec texte"
        position = (50, 50)  # Position du texte (x, y)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        color = (0, 255, 0)  # Couleur du texte en BGR (vert ici)
        thickness = 2
        cv2.putText(frame, text, position, font, font_scale, color, thickness)
        
        
        # Afficher l'image
        cv2.imshow('Video Stream', frame)

        # Quitter avec 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Libérer les ressources
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # URL du flux vidéo HTTP
    video_url = 'http://172.20.10.3:5000/video_feed'
    read_http_stream(video_url)
