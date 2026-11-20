"""Chaîne complète : marché → plan → manuscrit → illustrations → couvertures → formation → prix → exports."""
from __future__ import annotations

from typing import Callable

from . import course, export, illustrations, pricing, trends, writer
from .project import BookProject

Progress = Callable[[float, str], None]


def update_prices(p: BookProject) -> dict:
    duree = int((p.formation or {}).get("udemy", {}).get("duree_totale_min") or 0)
    pages = p.pages if p.mots else p.pages_cible
    p.prix = pricing.compute_prices(p.genre, pages, couleur=p.illustre and p.genre == "jeunesse",
                                    duree_formation_min=duree, market=p.marche)
    p.prix["scenarios"] = pricing.scenarios(p.prix)
    p.save()
    return p.prix


def run_all(p: BookProject, etude_marche: bool = True, progress: Progress | None = None, on_text=None) -> dict:
    say = progress or (lambda f, m: None)
    if etude_marche and not p.marche:
        say(0.0, "Étude de marché (recherche web)…")
        p.marche = trends.market_research(config_genre(p), p.langue, mots_cles=p.sujet)
        p.save()
    if not p.chapitres:
        say(0.05, "Plan détaillé et bible de continuité…")
        writer.create_outline(p)
    writer.write_book(p, progress=lambda f, m: say(0.1 + 0.6 * f, m), on_text=on_text)
    if p.illustre:
        illustrations.illustrate_all(p, progress=lambda f, m: say(0.7 + 0.1 * f, m))
    say(0.8, "Couverture et quatrième de couverture…")
    if not p.couverture_svg:
        illustrations.make_cover(p)
    if not p.formation:
        say(0.85, "Formation Udemy / Skillshare…")
        course.make_course(p)
    if not p.quatrieme:
        illustrations.write_back_cover(p)
    say(0.95, "Prix de vente…")
    update_prices(p)
    files = export.export_all(p)
    say(1.0, "Terminé")
    return files


def config_genre(p: BookProject) -> str:
    from . import config
    return config.GENRES.get(p.genre, p.genre)
