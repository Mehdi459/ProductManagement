"""Projet de livre persistant sur disque (reprise possible à tout moment)."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import config


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "livre"


@dataclass
class Section:
    titre: str
    resume: str
    texte: str = ""


@dataclass
class Chapter:
    numero: int
    titre: str
    resume: str
    sections: list[Section] = field(default_factory=list)
    illustration_prompt: str = ""
    illustration_svg: str = ""

    @property
    def done(self) -> bool:
        return bool(self.sections) and all(s.texte for s in self.sections)

    @property
    def mots(self) -> int:
        return sum(len(s.texte.split()) for s in self.sections)


@dataclass
class BookProject:
    titre: str
    genre: str
    sujet: str
    public: str = "adultes"
    langue: str = "français"
    pages_cible: int = 200
    ton: str = ""
    illustre: bool = True
    auteur: str = "Auteur"
    sous_titre: str = ""
    bible: str = ""                    # personnages, univers, thèse, style… (continuité)
    chapitres: list[Chapter] = field(default_factory=list)
    quatrieme: str = ""                # texte de 4e de couverture
    couverture_svg: str = ""
    formation: dict = field(default_factory=dict)
    prix: dict = field(default_factory=dict)
    marche: dict = field(default_factory=dict)
    id: str = ""                       # nom de dossier fixé à la création

    def __post_init__(self):
        if not self.id:
            self.id = slugify(self.titre)

    # ---------- statistiques ----------
    @property
    def mots_cible(self) -> int:
        return self.pages_cible * config.WORDS_PER_PAGE

    @property
    def mots(self) -> int:
        return sum(c.mots for c in self.chapitres)

    @property
    def pages(self) -> int:
        illus = sum(1 for c in self.chapitres if c.illustration_svg)
        return round(self.mots / config.WORDS_PER_PAGE) + illus + 6  # + pages liminaires

    @property
    def slug(self) -> str:
        return slugify(self.titre)

    @property
    def dossier(self) -> Path:
        return config.PROJECTS_DIR / self.id

    # ---------- persistance ----------
    def save(self) -> Path:
        self.dossier.mkdir(parents=True, exist_ok=True)
        path = self.dossier / "projet.json"
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, data: dict) -> "BookProject":
        chapitres = [
            Chapter(**{**c, "sections": [Section(**s) for s in c.get("sections", [])]})
            for c in data.pop("chapitres", [])
        ]
        return cls(**data, chapitres=chapitres)

    @classmethod
    def load(cls, path: Path) -> "BookProject":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def list_projects() -> list[Path]:
    if not config.PROJECTS_DIR.exists():
        return []
    return sorted(config.PROJECTS_DIR.glob("*/projet.json"))
