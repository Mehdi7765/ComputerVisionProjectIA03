import cv2
from flask import Flask, Response

app = Flask(__name__)

def generate_frames():
    camera = cv2.VideoCapture("rtsp://184.72.239.149/vod/mp4:BigBuckBunny_175k.mov")  # Indice de la caméra (0 pour la première caméra détectée)

    while True:
        # Capture frame-by-frame
        success, frame = camera.read()
        if not success:
            break
        else:
            # Encode the frame in JPEG format
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # Yield the output frame in byte format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    # Route for the video feed
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('/')
# def index():
#     # Main page with the video feed
#     return '''
#     <html>
#     <head>
#         <title>USB Camera Stream</title>
#     </head>
#     <body>
#         <h1>USB Camera Stream</h1>
#         <img src="/video_feed" width="640" height="480">
#     </body>
#     </html>
#     '''

# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # Démarrer le serveur Flask sur localhost et le port 8080
    app.run(host='0.0.0.0', port=5000)