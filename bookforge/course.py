"""Transformation du livre en formation vidéo pour Udemy et Skillshare."""
from __future__ import annotations

from . import llm
from .project import BookProject

PLATFORM_RULES = """Règles plateformes à respecter :
- Udemy : au moins 30 minutes de vidéo et 5 leçons pour un cours payant ; prix fixé par l'instructeur
  sur une grille (de ~19,99 € à ~199,99 €), promotions fréquentes ; titre ≤ 60 caractères,
  sous-titre ≤ 120 caractères ; objectifs d'apprentissage (au moins 4), prérequis, public cible.
- Skillshare : pas de prix par cours (abonnement) — rémunération selon les minutes regardées ;
  formats courts (leçons de 2 à 10 min), un projet de classe obligatoire et concret.
Si ces règles ont évolué, signale-le (tu peux vérifier sur le web)."""


def make_course(p: BookProject) -> dict:
    plan = "\n".join(
        f"Ch. {c.numero} {c.titre} : {c.resume} | sections : " + "; ".join(s.titre for s in c.sections)
        for c in p.chapitres
    )
    data = llm.generate_json(
        f"""Transforme le livre « {p.titre} » ({p.genre}, public {p.public}) en formation vidéo.
Pour un roman ou un livre d'histoires, crée une formation dérivée pertinente (ex. écriture créative,
thèmes du livre, lecture animée pour parents/enseignants, univers et making-of).

Plan du livre :
{plan}

{PLATFORM_RULES}

Format JSON :
{{
 "udemy": {{"titre": "", "sous_titre": "", "description": "", "objectifs": [""], "prerequis": [""],
            "public_cible": [""], "niveau": "", "duree_totale_min": 0,
            "sections": [{{"titre": "", "lecons": [{{"titre": "", "type": "video|quiz|exercice|ressource",
                           "duree_min": 0, "script": ""}}]}}],
            "prix_recommande_eur": 0, "prix_promo_eur": 0, "mots_cles": [""]}},
 "skillshare": {{"titre": "", "description": "", "projet_de_classe": "",
                 "lecons": [{{"titre": "", "duree_min": 0, "points_cles": ""}}]}},
 "tunnel_de_vente": "comment le livre (QR code, 4e de couverture, bonus) amène vers la formation et inversement"
}}
Le champ "script" contient le texte à dire face caméra (80-200 mots), au moins pour chaque vidéo.""",
        system="Tu es concepteur pédagogique expert des formations Udemy et Skillshare à succès.",
        web_search=True,
        max_tokens=64000,
    )
    p.formation = data
    p.save()
    return data
