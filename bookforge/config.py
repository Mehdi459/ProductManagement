"""Réglages globaux."""
import os
from pathlib import Path

MODEL = os.environ.get("BOOKFORGE_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("BOOKFORGE_EFFORT", "high")
PROJECTS_DIR = Path(os.environ.get("BOOKFORGE_PROJECTS", "projets"))

WORDS_PER_PAGE = 250  # format poche/broché standard (~250 mots par page)

GENRES = {
    "roman": "Roman (fiction narrative)",
    "essai": "Essai (argumentation, idées)",
    "guide": "Guide pratique / Manuel",
    "jeunesse": "Livre d'histoires pour enfants",
    "developpement_personnel": "Développement personnel",
    "business": "Business / Entrepreneuriat",
    "biographie": "Biographie / Récit de vie",
    "thriller": "Thriller / Policier",
    "fantasy": "Fantasy / Science-fiction",
    "cuisine": "Cuisine / Recettes",
}
