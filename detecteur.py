"""
DÉTECTEUR D'OBJETS YOLOv4-tiny (module DNN d'OpenCV)
====================================================
Charge le modèle une fois, puis :
  - `detecter(image)`  -> liste des objets trouvés (classe, confiance, boîte)
  - `annoter(image, detections)` -> dessine les boîtes et étiquettes

Les réglages `seuil_confiance`, `taille_entree` et `classes_filtre` peuvent
être modifiés à tout moment (c'est ce que fait l'interface web).
"""
import cv2
import numpy as np


class DetecteurYOLO:

    def __init__(self, chemin_cfg, chemin_poids, chemin_classes,
                 taille_entree=416, seuil_confiance=0.5, seuil_nms=0.4):
        with open(chemin_classes, encoding="utf-8") as f:
            self.classes = [ligne.strip() for ligne in f if ligne.strip()]

        # Reconstruction du réseau à partir de l'architecture (.cfg) et des
        # poids appris (.weights), exécution sur CPU.
        self._reseau = cv2.dnn.readNetFromDarknet(chemin_cfg, chemin_poids)
        self._reseau.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self._reseau.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self._couches_sortie = self._reseau.getUnconnectedOutLayersNames()

        # Réglages modifiables à chaud
        self.taille_entree = taille_entree
        self.seuil_confiance = seuil_confiance
        self.seuil_nms = seuil_nms
        self.classes_filtre = set()   # vide = toutes les classes

        # Une couleur fixe par classe, pour des boîtes stables à l'écran
        generateur = np.random.default_rng(42)
        self._couleurs = generateur.integers(80, 255, size=(len(self.classes), 3))

    # ------------------------------------------------------------------ #
    def detecter(self, image):
        """Renvoie une liste de dict : {"classe", "confiance", "boite": (x, y, w, h)}."""
        hauteur, largeur = image.shape[:2]
        taille = int(self.taille_entree)
        seuil = float(self.seuil_confiance)

        # 1) Préparation : pixels ramenés dans [0,1], redimensionnement à la
        #    taille attendue, passage BGR (OpenCV) -> RGB (YOLO).
        blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (taille, taille),
                                     swapRB=True, crop=False)
        self._reseau.setInput(blob)

        # 2) Passage dans le réseau
        sorties = self._reseau.forward(self._couches_sortie)

        # 3) Décodage : chaque ligne = [cx, cy, w, h, objectness, score_classe_0..79]
        boites, confiances, indices_classes = [], [], []
        for sortie in sorties:
            for detection in sortie:
                scores = detection[5:]
                indice = int(np.argmax(scores))
                confiance = float(scores[indice])
                if confiance < seuil:
                    continue
                if self.classes_filtre and self.classes[indice] not in self.classes_filtre:
                    continue
                # Coordonnées normalisées (0-1) -> pixels, centre -> coin haut-gauche
                cx, cy = detection[0] * largeur, detection[1] * hauteur
                w, h = detection[2] * largeur, detection[3] * hauteur
                boites.append([int(cx - w / 2), int(cy - h / 2), int(w), int(h)])
                confiances.append(confiance)
                indices_classes.append(indice)

        # 4) NMS : un même objet est souvent détecté plusieurs fois,
        #    on ne garde que la meilleure boîte pour chacun.
        retenus = cv2.dnn.NMSBoxes(boites, confiances, seuil, self.seuil_nms)
        resultats = []
        for i in np.array(retenus).flatten():
            resultats.append({
                "classe": self.classes[indices_classes[i]],
                "confiance": confiances[i],
                "boite": tuple(boites[i]),
                "_indice": indices_classes[i],
            })
        return resultats

    # ------------------------------------------------------------------ #
    def annoter(self, image, detections):
        """Dessine les boîtes et étiquettes sur l'image (modifiée en place)."""
        for d in detections:
            x, y, w, h = d["boite"]
            couleur = tuple(int(c) for c in self._couleurs[d["_indice"]])
            etiquette = f'{d["classe"]} {d["confiance"]:.0%}'
            cv2.rectangle(image, (x, y), (x + w, y + h), couleur, 2)
            # Fond plein derrière le texte pour rester lisible sur toute image
            (tw, th), _ = cv2.getTextSize(etiquette, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(image, (x, y - th - 8), (x + tw + 6, y), couleur, -1)
            cv2.putText(image, etiquette, (x + 3, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
        return image
