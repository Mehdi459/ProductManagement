"""Étude de marché : best-sellers, tendances et idées de livres rentables (recherche web)."""
from __future__ import annotations

from datetime import date

from . import llm

SYSTEM = (
    "Tu es analyste du marché de l'édition et de la formation en ligne. "
    "Tu utilises la recherche web pour obtenir des données RÉCENTES et vérifiables "
    "(classements Amazon/Kindle, Fnac, Babelio, Edistat, Livres Hebdo, Goodreads, "
    "Google Trends, TikTok/BookTok, Udemy, Skillshare). Tu cites tes sources (URL). "
    "Tu ne fabriques jamais de chiffres : si une donnée est estimée, indique-le."
)

PLATFORMS = [
    "Amazon (Kindle & broché)", "Fnac", "Apple Books", "Kobo", "Goodreads/Babelio",
    "Udemy", "Skillshare",
]


def market_research(
    genre: str = "tous genres",
    langue: str = "français",
    marche: str = "France",
    mots_cles: str = "",
) -> dict:
    prompt = f"""Date du jour : {date.today().isoformat()}.
Fais une étude de marché pour un auteur indépendant.
- Genre ciblé : {genre}
- Langue : {langue} — Marché : {marche}
- Mots-clés / centres d'intérêt : {mots_cles or "aucun"}
- Plateformes à examiner : {", ".join(PLATFORMS)}

Recherche sur le web :
1. Les livres les plus vendus actuellement dans ce genre (au moins 10).
2. Les sujets en tendance (montée des recherches, BookTok, actualité) et les niches peu concurrentielles.
3. Les formations Udemy et Skillshare les plus populaires liées à ces sujets, avec leurs prix.
4. Les fourchettes de prix constatées (ebook, broché, formation).

Structure JSON attendue :
{{
  "best_sellers": [{{"titre": "", "auteur": "", "plateforme": "", "categorie": "", "prix": "", "pourquoi_ca_marche": "", "source": ""}}],
  "tendances": [{{"sujet": "", "score_tendance": 0, "concurrence": "faible|moyenne|forte", "explication": "", "source": ""}}],
  "formations_populaires": [{{"titre": "", "plateforme": "Udemy|Skillshare", "prix": "", "eleves_ou_avis": "", "source": ""}}],
  "prix_constates": {{"ebook": {{"min": 0, "median": 0, "max": 0}}, "broche": {{"min": 0, "median": 0, "max": 0}}, "formation_udemy": {{"min": 0, "median": 0, "max": 0}}}},
  "idees_de_livres": [{{"titre": "", "sous_titre": "", "genre": "", "public_cible": "", "angle_unique": "", "potentiel": 0, "formation_associee": ""}}],
  "synthese": ""
}}
`score_tendance` et `potentiel` sont des notes de 0 à 100. Propose au moins 8 idées de livres
classées par potentiel décroissant. Les prix sont en euros (nombres)."""
    return llm.generate_json(prompt, system=SYSTEM, web_search=True, max_tokens=48000)
