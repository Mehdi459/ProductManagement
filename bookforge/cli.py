"""Ligne de commande.

    python -m bookforge.cli tendances --genre guide --mots-cles "IA, productivité"
    python -m bookforge.cli livre --titre "Mon livre" --genre roman --sujet "..." --pages 300
    python -m bookforge.cli reprendre projets/mon-livre/projet.json
"""
from __future__ import annotations

import argparse
import json
import sys

from . import config, pipeline, trends
from .project import BookProject


def _progress(f: float, msg: str) -> None:
    print(f"[{f:5.0%}] {msg}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="bookforge", description="Générateur de livres et de formations")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("tendances", help="Best-sellers et idées de livres en tendance")
    t.add_argument("--genre", default="tous genres")
    t.add_argument("--langue", default="français")
    t.add_argument("--marche", default="France")
    t.add_argument("--mots-cles", default="")

    b = sub.add_parser("livre", help="Générer un livre complet")
    b.add_argument("--titre", required=True)
    b.add_argument("--genre", choices=list(config.GENRES), required=True)
    b.add_argument("--sujet", required=True)
    b.add_argument("--pages", type=int, default=200)
    b.add_argument("--public", default="adultes")
    b.add_argument("--auteur", default="Auteur")
    b.add_argument("--ton", default="")
    b.add_argument("--langue", default="français")
    b.add_argument("--sans-illustrations", action="store_true")
    b.add_argument("--sans-etude-marche", action="store_true")

    r = sub.add_parser("reprendre", help="Reprendre un projet interrompu")
    r.add_argument("projet")

    a = ap.parse_args(argv)
    if a.cmd == "tendances":
        print(json.dumps(trends.market_research(a.genre, a.langue, a.marche, a.mots_cles), ensure_ascii=False, indent=2))
        return
    if a.cmd == "livre":
        p = BookProject(titre=a.titre, genre=a.genre, sujet=a.sujet, pages_cible=a.pages, public=a.public,
                        auteur=a.auteur, ton=a.ton, langue=a.langue, illustre=not a.sans_illustrations)
        p.save()
        etude = not a.sans_etude_marche
    else:
        p = BookProject.load(a.projet)
        etude = False
    files = pipeline.run_all(p, etude_marche=etude, progress=_progress)
    print(f"\n{p.titre} — {p.pages} pages, {p.mots} mots")
    for k, v in files.items():
        print(f"  {k:14} {v}")
    print(json.dumps({k: p.prix[k] for k in ("ebook", "broche", "udemy")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
