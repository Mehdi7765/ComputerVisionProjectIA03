"""
lecture_http.py — script fourni en TP, adapté.  RÔLE : ANALYSE
===============================================================
Version d'origine : lit le flux HTTP du PC capture, écrit un texte sur chaque
image et l'affiche dans une fenêtre.

Version adaptée : à l'endroit prévu pour "modifier l'image", le texte fixe est
remplacé par la DÉTECTION D'OBJETS YOLO, et l'image annotée est REDIFFUSÉE
sur le réseau (même principe que diffusion_http.py) avec une page web :
n'importe quel appareil du réseau la consulte dans un navigateur.

À lancer sur le PC qui fait tourner le modèle (pas besoin de webcam) :
    python3 lecture_http.py                                          # source = config.URL_FLUX_BRUT
    python3 lecture_http.py --source http://172.20.10.11:5000/video_feed
    python3 lecture_http.py --source rtsp://172.20.10.11:8554/stream   # variante ffmpeg
    python3 lecture_http.py --source 0                               # webcam locale (1 seul PC)
    python3 lecture_http.py --sans-fenetre                           # sans fenêtre locale

Pages servies (port 8000 par défaut) :
    /             interface web : flux annoté, statistiques, réglages
    /video_feed   le flux MJPEG annoté
    /stats        statistiques en JSON (images/s, latence, objets...)
    /parametres   GET = réglages courants, POST = les modifier à chaud

Modifications par rapport à la version d'origine (repérées par [MODIF]) :
  1. détection YOLO à la place du texte fixe (module detecteur.py) ;
  2. rediffusion de l'image annotée + serveur web (modules diffuseur.py, templates/) ;
  3. lecture "dernière image seulement" pour ne pas accumuler de retard ;
  4. reconnexion automatique si le flux coupe ;
  5. la fenêtre locale devient optionnelle (inutile sur un serveur sans écran) ;
  6. l'adresse du flux vient de config.py / de la ligne de commande.
La version d'origine est conservée dans docs/scripts_origine/.
"""
import argparse      # [MODIF]
import collections   # [MODIF]
import sys           # [MODIF]
import threading     # [MODIF]
import time          # [MODIF]

import cv2
from flask import Flask, jsonify, render_template, request   # [MODIF]

import config                                                # [MODIF]
from detecteur import DetecteurYOLO                          # [MODIF]
from diffuseur import DiffuseurMJPEG                         # [MODIF]
from utilitaires import (adresse_ip_locale, source_video, ouvrir_source,   # [MODIF]
                         LecteurDerniereImage, CompteurFPS, reduire_logs_flask)

# [MODIF] Serveur web de consultation et objets partagés
app = Flask(__name__)
diffuseur = DiffuseurMJPEG(qualite_jpeg=config.QUALITE_JPEG)
detecteur = None            # créé au lancement (chargement du modèle)
compteur = CompteurFPS()
stats = {
    "source": "", "source_connectee": False, "resolution": "",
    "fps": 0.0, "latence_ms": 0, "nb_objets": 0, "objets_par_classe": {},
}


def read_http_stream(url, afficher=True):
    # [MODIF] boucle externe : si le flux coupe, on retente au lieu de quitter
    while True:
        # Ouvrir le flux vidéo HTTP avec OpenCV
        cap = ouvrir_source(url)   # [MODIF] accepte aussi RTSP, GStreamer, fichier, webcam
        if not cap.isOpened():
            stats["source_connectee"] = False
            print(f"Source {url!r} injoignable, nouvel essai dans {config.DELAI_RECONNEXION:.0f} s")
            time.sleep(config.DELAI_RECONNEXION)
            continue

        # [MODIF] lecture dans un thread qui ne garde que la dernière image
        lecteur = LecteurDerniereImage(cap)
        lecteur.start()
        stats["source_connectee"] = True
        print(f"Connecté à {url!r}")

        while True:
            # Lire les images du flux
            ret, frame = lecteur.lire()   # [MODIF] à la place de cap.read()
            if not ret:
                print("Erreur de lecture du flux vidéo.")
                break

            # modifier l'image
            # [MODIF] le texte fixe est remplacé par la détection d'objets :
            # YOLO localise les objets, on dessine les boîtes et étiquettes
            debut = time.time()
            detections = detecteur.detecter(frame)
            latence_ms = (time.time() - debut) * 1000
            detecteur.annoter(frame, detections)
            compteur.tic()

            text = f"{compteur.fps:.1f} img/s | {latence_ms:.0f} ms | {len(detections)} objet(s)"
            position = (10, 25)              # Position du texte (x, y)
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            color = (0, 255, 0)              # Couleur du texte en BGR (vert ici)
            thickness = 2
            cv2.putText(frame, text, position, font, font_scale, color, thickness)

            # [MODIF] rediffusion de l'image annotée vers les navigateurs,
            # et statistiques pour la page web
            diffuseur.publier(frame)
            stats.update({
                "source_connectee": True,
                "resolution": f"{frame.shape[1]}x{frame.shape[0]}",
                "fps": round(compteur.fps, 1),
                "latence_ms": round(latence_ms),
                "nb_objets": len(detections),
                "objets_par_classe": dict(collections.Counter(d["classe"] for d in detections).most_common()),
            })

            # Afficher l'image
            if afficher:   # [MODIF] fenêtre optionnelle
                try:
                    cv2.imshow('Video Stream', frame)
                    # Quitter avec 'q'
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        lecteur.arreter()
                        cv2.destroyAllWindows()
                        return
                except cv2.error:
                    # Pas d'écran (machine sans interface graphique) : on
                    # continue sans fenêtre, la page web suffit.
                    afficher = False

        # Libérer les ressources (le lecteur libère la capture lui-même)
        lecteur.arreter()
        stats["source_connectee"] = False
        print(f"Flux interrompu, nouvelle tentative dans {config.DELAI_RECONNEXION:.0f} s")
        time.sleep(config.DELAI_RECONNEXION)


# --------------------------------------------------------------------------- #
#  [MODIF] Routes HTTP de l'interface de consultation
# --------------------------------------------------------------------------- #
@app.route("/")
def accueil():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return diffuseur.reponse_http()


@app.route("/stats")
def stats_json():
    return jsonify(stats)


def parametres_courants():
    return {
        "seuil_confiance": detecteur.seuil_confiance,
        "taille_entree": detecteur.taille_entree,
        "tailles_possibles": list(config.TAILLES_ENTREE_POSSIBLES),
        "classes_filtre": sorted(detecteur.classes_filtre),
        "toutes_les_classes": detecteur.classes,
    }


@app.route("/parametres", methods=["GET", "POST"])
def parametres():
    """Lecture (GET) ou modification à chaud (POST, corps JSON) des réglages."""
    if request.method == "POST":
        donnees = request.get_json(silent=True) or {}
        erreurs = []

        if "seuil_confiance" in donnees:
            try:
                seuil = float(donnees["seuil_confiance"])
                if not 0.05 <= seuil <= 0.95:
                    raise ValueError
                detecteur.seuil_confiance = seuil
            except (TypeError, ValueError):
                erreurs.append("seuil_confiance doit être un nombre entre 0.05 et 0.95")

        if "taille_entree" in donnees:
            try:
                taille = int(donnees["taille_entree"])
                if taille not in config.TAILLES_ENTREE_POSSIBLES:
                    raise ValueError
                detecteur.taille_entree = taille
            except (TypeError, ValueError):
                erreurs.append(f"taille_entree doit être parmi {config.TAILLES_ENTREE_POSSIBLES}")

        if "classes" in donnees:
            brut = donnees["classes"]
            noms = brut if isinstance(brut, list) else str(brut).split(",")
            noms = [n.strip().lower() for n in noms if n.strip()]
            inconnues = [n for n in noms if n not in detecteur.classes]
            if inconnues:
                erreurs.append(f"classes inconnues : {', '.join(inconnues)}")
            else:
                detecteur.classes_filtre = set(noms)

        reponse = parametres_courants()
        reponse["erreurs"] = erreurs
        return jsonify(reponse), (400 if erreurs else 200)

    return jsonify(parametres_courants())


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)

    # [MODIF] options de lancement (prennent le dessus sur config.py)
    parseur = argparse.ArgumentParser(description="Applique YOLO à un flux vidéo et rediffuse le résultat.")
    parseur.add_argument("--source", default=config.URL_FLUX_BRUT,
                         help="URL du flux (http:// ou rtsp://), fichier, ou index de webcam locale (0)")
    parseur.add_argument("--port", type=int, default=config.ANALYSE_PORT)
    parseur.add_argument("--seuil", type=float, default=config.SEUIL_CONFIANCE)
    parseur.add_argument("--taille", type=int, default=config.TAILLE_ENTREE,
                         choices=config.TAILLES_ENTREE_POSSIBLES)
    parseur.add_argument("--sans-fenetre", action="store_true",
                         help="ne pas ouvrir de fenêtre locale (la page web suffit)")
    args = parseur.parse_args()

    print("Chargement du modèle YOLOv4-tiny...")
    detecteur = DetecteurYOLO(config.FICHIER_CFG, config.FICHIER_POIDS, config.FICHIER_CLASSES,
                              taille_entree=args.taille, seuil_confiance=args.seuil,
                              seuil_nms=config.SEUIL_NMS)
    reduire_logs_flask()

    # [MODIF] le serveur web tourne dans un thread de fond ; la lecture reste
    # dans le thread principal (cv2.imshow l'exige sur certains systèmes)
    threading.Thread(target=lambda: app.run(host=config.HOTE_ECOUTE, port=args.port,
                                            threaded=True, use_reloader=False),
                     daemon=True).start()

    # URL du flux vidéo HTTP
    video_url = source_video(args.source)   # [MODIF] config.py / --source au lieu de localhost en dur
    stats["source"] = str(video_url)

    ip = adresse_ip_locale()
    print("=" * 62)
    print("  PC ANALYSE prêt (lecture_http.py)")
    print(f"  Source vidéo :        {video_url}")
    print(f"  Interface web :       http://{ip}:{args.port}/   <- à ouvrir sur n'importe quel appareil")
    print(f"  Flux annoté seul :    http://{ip}:{args.port}/video_feed")
    print("  (touche q dans la fenêtre ou Ctrl+C pour arrêter)")
    print("=" * 62)

    read_http_stream(video_url, afficher=not args.sans_fenetre)
