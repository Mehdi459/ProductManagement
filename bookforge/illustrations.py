"""Illustrations vectorielles (SVG) et couverture, générées par Claude.

Les SVG sont nets à toute taille (impression comme ebook) et ne demandent aucune
clé supplémentaire. Pour des illustrations photoréalistes, les descriptions
(`illustration_prompt`) peuvent aussi être copiées dans un générateur d'images.
"""
from __future__ import annotations

import re

from . import llm
from .project import BookProject, Chapter

_SVG_RE = re.compile(r"<svg\b.*?</svg>", re.DOTALL | re.IGNORECASE)
_DANGEROUS = re.compile(r"<script\b.*?</script>|\son\w+\s*=\s*\"[^\"]*\"|\son\w+\s*=\s*'[^']*'", re.DOTALL | re.IGNORECASE)


def clean_svg(text: str) -> str:
    m = _SVG_RE.search(text)
    if not m:
        raise llm.GenerationError("Aucun SVG dans la réponse")
    svg = _DANGEROUS.sub("", m.group(0))
    if "xmlns=" not in svg[:200]:
        svg = svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return svg


STYLE = {
    "jeunesse": "style album jeunesse, formes rondes, couleurs vives et chaleureuses",
    "roman": "style gravure/aquarelle élégante, palette restreinte",
    "thriller": "style noir graphique, contrastes forts, ombres",
    "fantasy": "style épique, lumière dramatique, paysages",
    "guide": "infographie / schéma pédagogique clair avec légendes",
    "essai": "illustration conceptuelle minimaliste",
    "business": "infographie moderne et sobre",
    "cuisine": "illustration culinaire gourmande et colorée",
}


def illustrate_chapter(p: BookProject, chap: Chapter) -> str:
    text = llm.generate(
        f"""Crée une illustration SVG pour le chapitre {chap.numero} « {chap.titre} » du livre « {p.titre} ».
Scène / schéma : {chap.illustration_prompt or chap.resume}
Style : {STYLE.get(p.genre, "illustration éditoriale soignée")}.
Contraintes : viewBox="0 0 800 600", formes vectorielles détaillées (dégradés, superpositions,
profondeur), pas d'image externe, pas de script, texte limité aux légendes utiles.
Réponds uniquement avec le code <svg>…</svg>.""",
        max_tokens=32000,
        effort="medium",
    )
    chap.illustration_svg = clean_svg(text)
    p.save()
    return chap.illustration_svg


def illustrate_all(p: BookProject, progress=None) -> None:
    todo = [c for c in p.chapitres if not c.illustration_svg]
    for i, c in enumerate(todo):
        if progress:
            progress(i / max(1, len(todo)), f"Illustration du chapitre {c.numero}")
        illustrate_chapter(p, c)


def make_cover(p: BookProject) -> str:
    text = llm.generate(
        f"""Crée la couverture avant d'un livre en SVG.
Titre : {p.titre}
Sous-titre : {p.sous_titre}
Auteur : {p.auteur}
Genre : {p.genre} — Public : {p.public}
Pitch : {p.sujet}
Contraintes : viewBox="0 0 1600 2560" (ratio Kindle 1:1.6), visuel fort et lisible en vignette,
typographie hiérarchisée (titre très lisible), codes graphiques du genre, aucune image externe,
aucun script. Réponds uniquement avec le code <svg>…</svg>.""",
        max_tokens=32000,
    )
    p.couverture_svg = clean_svg(text)
    p.save()
    return p.couverture_svg


def write_back_cover(p: BookProject) -> str:
    plan = "\n".join(f"- {c.titre} : {c.resume}" for c in p.chapitres)
    p.quatrieme = llm.generate(
        f"""Rédige la quatrième de couverture du livre « {p.titre} » ({p.sous_titre}), genre {p.genre},
public {p.public}.
Plan :
{plan}

Structure : une accroche percutante, 120 à 180 mots de présentation qui donnent envie sans
tout dévoiler (fiction) ou qui listent les bénéfices concrets (non-fiction), puis 2 lignes sur
l'auteur « {p.auteur} » (génériques et modifiables). Si une formation est associée, termine par une
ligne invitant à la formation vidéo. Texte brut, sans titre.""",
        max_tokens=4000,
    )
    p.save()
    return p.quatrieme
