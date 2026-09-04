"""
RÔLE 2 — ANALYSE : applique YOLO au flux distant et sert le résultat annoté.
============================================================================
À lancer sur le PC qui fait tourner le modèle (pas besoin de webcam).

    python3 analyse.py                                        # source = config.URL_FLUX_BRUT
    python3 analyse.py --source http://172.20.10.11:5000/video_feed
    python3 analyse.py --source 0                             # webcam locale (test sur 1 seul PC)
    python3 analyse.py --port 8000 --seuil 0.6 --taille 320

Le résultat est consultable depuis N'IMPORTE QUEL appareil du réseau
(téléphone, autre PC) avec un simple navigateur :  http://<ip de ce PC>:8000/

Pages servies :
    /             interface web : flux annoté, statistiques, réglages
    /video_feed   le flux MJPEG annoté
    /stats        statistiques en JSON (images/s, latence, objets...)
    /parametres   GET = réglages courants, POST = les modifier à chaud

Organisation interne (3 fils d'exécution) :
    LecteurFlux   lit la source réseau en continu et garde SEULEMENT la
                  dernière image reçue (pas de file d'attente => si le modèle
                  est plus lent que la caméra, on saute des images plutôt que
                  d'accumuler du retard). Se reconnecte tout seul si ça coupe.
    analyse       prend la dernière image, détecte, annote, publie.
    Flask         sert les pages et le flux aux spectateurs.
"""
import argparse
import collections
import sys
import threading
import time

import cv2
from flask import Flask, jsonify, render_template, request

import config
from detecteur import DetecteurYOLO
from diffuseur import DiffuseurMJPEG
from utilitaires import adresse_ip_locale, source_video, CompteurFPS, reduire_logs_flask

app = Flask(__name__)
detecteur = None
diffuseur = None
compteur = CompteurFPS()

# Dernière image reçue de la source, partagée entre le lecteur et l'analyse
_condition = threading.Condition()
_derniere = {"image": None, "numero": 0}

# Statistiques exposées à l'interface web (remplacées d'un bloc, jamais
# modifiées champ par champ, pour rester cohérentes entre threads)
stats = {
    "source": "", "source_connectee": False, "resolution": "",
    "fps": 0.0, "latence_ms": 0.0, "nb_objets": 0, "objets_par_classe": {},
}


# --------------------------------------------------------------------------- #
#  Thread 1 : lecture de la source
# --------------------------------------------------------------------------- #
class LecteurFlux(threading.Thread):

    def __init__(self, source):
        super().__init__(daemon=True)
        self.source = source
        self.connectee = False

    def run(self):
        while True:
            capture = cv2.VideoCapture(self.source)
            if not capture.isOpened():
                self.connectee = False
                print(f"[lecteur] source {self.source!r} injoignable, "
                      f"nouvel essai dans {config.DELAI_RECONNEXION:.0f} s")
                time.sleep(config.DELAI_RECONNEXION)
                continue

            self.connectee = True
            print(f"[lecteur] connecté à {self.source!r}")
            while True:
                ok, image = capture.read()
                if not ok:
                    break
                with _condition:
                    _derniere["image"] = image      # on écrase : seule la dernière compte
                    _derniere["numero"] += 1
                    _condition.notify_all()

            capture.release()
            self.connectee = False
            print("[lecteur] flux interrompu, reconnexion...")
            time.sleep(config.DELAI_RECONNEXION)


# --------------------------------------------------------------------------- #
#  Thread 2 : analyse (YOLO) + annotation + publication
# --------------------------------------------------------------------------- #
def boucle_analyse(lecteur):
    dernier_traite = 0
    while True:
        with _condition:
            _condition.wait_for(lambda: _derniere["numero"] != dernier_traite, timeout=1.0)
            if _derniere["image"] is None or _derniere["numero"] == dernier_traite:
                # Pas de nouvelle image (source coupée) : on met juste l'état à jour
                stats.update({"source_connectee": lecteur.connectee})
                continue
            image = _derniere["image"].copy()
            dernier_traite = _derniere["numero"]

        debut = time.time()
        detections = detecteur.detecter(image)
        latence_ms = (time.time() - debut) * 1000
        detecteur.annoter(image, detections)
        compteur.tic()

        # Bandeau d'information incrusté (utile quand on regarde /video_feed seul)
        texte = f"{compteur.fps:.1f} img/s | {latence_ms:.0f} ms | {len(detections)} objet(s)"
        cv2.rectangle(image, (0, 0), (len(texte) * 11 + 10, 26), (0, 0, 0), -1)
        cv2.putText(image, texte, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (0, 255, 255), 1, cv2.LINE_AA)

        diffuseur.publier(image)

        compte = collections.Counter(d["classe"] for d in detections)
        stats.update({
            "source_connectee": lecteur.connectee,
            "resolution": f"{image.shape[1]}x{image.shape[0]}",
            "fps": round(compteur.fps, 1),
            "latence_ms": round(latence_ms),
            "nb_objets": len(detections),
            "objets_par_classe": dict(compte.most_common()),
        })


# --------------------------------------------------------------------------- #
#  Routes HTTP
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


# --------------------------------------------------------------------------- #
def main():
    global detecteur, diffuseur
    sys.stdout.reconfigure(line_buffering=True)   # messages visibles même si la sortie est redirigée

    parseur = argparse.ArgumentParser(description="Applique YOLO à un flux vidéo et rediffuse le résultat.")
    parseur.add_argument("--source", default=config.URL_FLUX_BRUT,
                         help="URL du flux du PC capture, ou index de webcam locale (0)")
    parseur.add_argument("--port", type=int, default=config.ANALYSE_PORT)
    parseur.add_argument("--seuil", type=float, default=config.SEUIL_CONFIANCE)
    parseur.add_argument("--taille", type=int, default=config.TAILLE_ENTREE,
                         choices=config.TAILLES_ENTREE_POSSIBLES)
    parseur.add_argument("--qualite", type=int, default=config.QUALITE_JPEG)
    args = parseur.parse_args()

    print("[analyse] chargement du modèle YOLOv4-tiny...")
    detecteur = DetecteurYOLO(config.FICHIER_CFG, config.FICHIER_POIDS, config.FICHIER_CLASSES,
                              taille_entree=args.taille, seuil_confiance=args.seuil,
                              seuil_nms=config.SEUIL_NMS)
    diffuseur = DiffuseurMJPEG(qualite_jpeg=args.qualite)
    reduire_logs_flask()

    source = source_video(args.source)
    stats["source"] = str(source)
    lecteur = LecteurFlux(source)
    lecteur.start()
    threading.Thread(target=boucle_analyse, args=(lecteur,), daemon=True).start()

    ip = adresse_ip_locale()
    print("=" * 62)
    print("  PC ANALYSE prêt")
    print(f"  Source vidéo :        {source}")
    print(f"  Interface web :       http://{ip}:{args.port}/   <- à ouvrir sur n'importe quel appareil")
    print(f"  Flux annoté seul :    http://{ip}:{args.port}/video_feed")
    print("  (Ctrl+C pour arrêter)")
    print("=" * 62)
    app.run(host=config.HOTE_ECOUTE, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
