"""Écriture du livre : plan détaillé, bible de continuité, puis rédaction section par section."""
from __future__ import annotations

import math
from typing import Callable

from . import config, llm
from .project import BookProject, Chapter, Section

GENRE_GUIDE = {
    "roman": "Narration immersive, dialogues vivants, arcs de personnages, montrer plutôt que dire.",
    "thriller": "Tension constante, cliffhangers en fin de chapitre, fausses pistes, rythme rapide.",
    "fantasy": "Univers cohérent (règles de magie/technologie), worldbuilding distillé dans l'action.",
    "essai": "Thèse claire, arguments structurés, exemples, références, contre-arguments discutés.",
    "guide": "Pédagogique : objectifs, étapes numérotées, exemples concrets, encadrés « À retenir », exercices.",
    "developpement_personnel": "Bienveillant et concret : anecdotes, exercices pratiques, plan d'action.",
    "business": "Cas réels, méthodes actionnables, chiffres sourcés ou présentés comme exemples.",
    "jeunesse": "Phrases courtes, vocabulaire adapté à l'âge, humour, valeurs, scènes très visuelles.",
    "biographie": "Chronologie claire, contexte historique, anecdotes, citations présentées avec prudence.",
    "cuisine": "Recettes complètes (ingrédients, quantités, étapes, temps), astuces et variantes.",
}


def _system(p: BookProject) -> str:
    return (
        f"Tu es un auteur professionnel et un éditeur expérimenté qui écrit en {p.langue}. "
        f"Genre : {config.GENRES.get(p.genre, p.genre)}. Public : {p.public}. "
        f"Consignes de genre : {GENRE_GUIDE.get(p.genre, 'Qualité éditoriale professionnelle.')} "
        f"Ton souhaité : {p.ton or 'adapté au genre'}. "
        "Texte original, sans plagiat, prêt à publier. Pas de méta-commentaires."
    )


def plan_structure(pages: int) -> tuple[int, int]:
    """Nombre de chapitres et de sections par chapitre selon la taille visée."""
    chapitres = max(6, min(40, round(pages / 12)))
    mots_chapitre = pages * config.WORDS_PER_PAGE / chapitres
    sections = max(1, math.ceil(mots_chapitre / 1800))
    return chapitres, sections


def create_outline(p: BookProject) -> BookProject:
    n_chap, n_sec = plan_structure(p.pages_cible)
    data = llm.generate_json(
        f"""Conçois le livre suivant.
Titre provisoire : {p.titre}
Sujet / pitch : {p.sujet}
Taille visée : {p.pages_cible} pages (~{p.mots_cible} mots).

Produis :
- "titre" (accrocheur, vendeur) et "sous_titre"
- "bible" : document de continuité détaillé (personnages avec traits et arcs, lieux, règles de l'univers
  OU thèse, fil conducteur et concepts-clés pour un livre de non-fiction ; style et voix narrative).
- "chapitres" : exactement {n_chap} chapitres, chacun avec "titre", "resume" (5-8 phrases),
  "illustration" (description visuelle précise d'une scène ou d'un schéma du chapitre),
  et "sections" : exactement {n_sec} sections avec "titre" et "resume" (2-4 phrases).

Format : {{"titre": "", "sous_titre": "", "bible": "", "chapitres": [{{"titre": "", "resume": "", "illustration": "", "sections": [{{"titre": "", "resume": ""}}]}}]}}""",
        system=_system(p),
        max_tokens=64000,
    )
    p.titre = data.get("titre") or p.titre
    p.sous_titre = data.get("sous_titre", "")
    p.bible = data.get("bible", "") if isinstance(data.get("bible"), str) else str(data.get("bible"))
    p.chapitres = [
        Chapter(
            numero=i + 1,
            titre=c["titre"],
            resume=c.get("resume", ""),
            illustration_prompt=c.get("illustration", ""),
            sections=[Section(titre=s["titre"], resume=s.get("resume", "")) for s in c.get("sections", [])],
        )
        for i, c in enumerate(data["chapitres"])
    ]
    p.save()
    return p


def _plan_text(p: BookProject) -> str:
    return "\n".join(f"Ch. {c.numero} — {c.titre} : {c.resume}" for c in p.chapitres)


def write_section(p: BookProject, chap: Chapter, idx: int, on_text: Callable[[str], None] | None = None) -> str:
    sec = chap.sections[idx]
    n_sections = sum(len(c.sections) for c in p.chapitres) or 1
    mots = max(600, round(p.mots_cible / n_sections))

    # Contexte : fin du passage précédent pour une transition fluide.
    precedent = ""
    if idx > 0:
        precedent = chap.sections[idx - 1].texte
    elif chap.numero > 1:
        prev = p.chapitres[chap.numero - 2]
        precedent = prev.sections[-1].texte if prev.sections else ""
    precedent = " ".join(precedent.split()[-700:])

    prompt = f"""LIVRE : « {p.titre} » — {p.sous_titre}

BIBLE DE CONTINUITÉ :
{p.bible}

PLAN GÉNÉRAL :
{_plan_text(p)}

CHAPITRE EN COURS : {chap.numero} — {chap.titre}
Résumé du chapitre : {chap.resume}
Sections du chapitre : {"; ".join(s.titre for s in chap.sections)}

FIN DU PASSAGE PRÉCÉDENT :
{precedent or "(début du livre)"}

À ÉCRIRE MAINTENANT : section {idx + 1}/{len(chap.sections)} « {sec.titre} »
Contenu attendu : {sec.resume}

Écris environ {mots} mots, en Markdown (intertitres ### si utile pour la non-fiction, aucun titre
de chapitre). Enchaîne naturellement avec le passage précédent, respecte la bible, n'anticipe pas
les sections suivantes. Écris uniquement le texte de la section."""
    sec.texte = llm.generate(prompt, system=_system(p), max_tokens=max(8000, mots * 3), on_text=on_text)
    p.save()
    return sec.texte


def write_book(
    p: BookProject,
    progress: Callable[[float, str], None] | None = None,
    on_text: Callable[[str], None] | None = None,
) -> BookProject:
    """Écrit toutes les sections manquantes (reprend là où le projet s'est arrêté)."""
    todo = [(c, i) for c in p.chapitres for i, s in enumerate(c.sections) if not s.texte]
    total = sum(len(c.sections) for c in p.chapitres)
    for c, i in todo:
        done = total - len([1 for cc in p.chapitres for s in cc.sections if not s.texte])
        if progress:
            progress(done / total, f"Chapitre {c.numero} — {c.sections[i].titre}")
        write_section(p, c, i, on_text=on_text)
    if progress:
        progress(1.0, "Manuscrit terminé")
    return p
