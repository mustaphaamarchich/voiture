# 🚗 Mon Voiture

Application Streamlit pour conducteurs, techniciens et experts automobiles.

## Fonctionnalités
- Création de compte avec choix du métier (Conducteur, Technicien / Mécanicien, Expert automobile)
- Mes voitures et kilométrage
- Rappels de dates (visite technique, vidange, assurance...) avec code couleur
- Conseils par partie de la voiture, avec photos
- Demandes de service avec offres de prix des techniciens (façon inDrive)
- Discussions : communauté, experts & techniciens, salon privé par mission
- Vidéos pour réparer soi-même

## Fichiers
| Fichier | Rôle |
|---|---|
| `app.py` | Application complète |
| `dataset.csv` | Conseils et vidéos (colonnes : type, categorie, titre, contenu, lien, image) |
| `requirements.txt` | Dépendances |
| `README.md` | Ce fichier |
| `carte.png`, `reglages.png`, `recharge.png` | Images utilisées dans l'interface |

La base `mycar.db` est créée automatiquement au premier lancement.

## Installation
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Personnalisation
- **Images** : colonne `image` de `dataset.csv`. Mettez une URL, ou un nom de fichier (ex. `freins.jpg`) placé dans le même dossier que `app.py`.
- **Vidéos** : colonne `lien`. Une URL `https://www.youtube.com/watch?v=...` se lit directement dans l'application.
