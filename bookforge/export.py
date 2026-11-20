"""Exports : HTML imprimable, PDF, DOCX (KDP), Markdown, et formation (Markdown + CSV)."""
from __future__ import annotations

import csv
import html
import io
from pathlib import Path

import markdown as md

from .project import BookProject

CSS = """
@page { size: 152.4mm 228.6mm; margin: 20mm 16mm 22mm 18mm;
        @bottom-center { content: counter(page); font-size: 9pt; color: #555; } }
@page cover { margin: 0; @bottom-center { content: none; } }
body { font-family: 'Georgia', 'Times New Roman', serif; font-size: 11pt; line-height: 1.5;
       color: #111; text-align: justify; hyphens: auto; }
.cover { page: cover; page-break-after: always; height: 228.6mm; }
.cover svg { width: 100%; height: 100%; }
.titlepage { text-align: center; page-break-after: always; padding-top: 30%; }
.titlepage h1 { font-size: 26pt; margin-bottom: .2em; }
.titlepage .subtitle { font-size: 14pt; font-style: italic; }
.titlepage .author { margin-top: 3em; font-size: 13pt; }
.toc { page-break-after: always; } .toc li { margin: .3em 0; list-style: none; }
.chapter { page-break-before: always; }
.chapter h2 { text-align: center; font-size: 18pt; margin: 2em 0 1em; }
.chapter h2 small { display: block; font-size: 11pt; letter-spacing: .2em; color: #666; }
.illustration { text-align: center; margin: 1em 0 2em; page-break-inside: avoid; }
.illustration svg { width: 100%; height: auto; max-height: 120mm; }
p { margin: 0 0 .6em; text-indent: 1.2em; }
.back { page-break-before: always; padding: 20% 8%; font-size: 12pt; }
.back p { text-indent: 0; }
"""


def _svg_block(svg: str, cls: str) -> str:
    return f'<div class="{cls}">{svg}</div>' if svg else ""


def to_html(p: BookProject) -> str:
    parts = [
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>",
        f"<title>{html.escape(p.titre)}</title><style>{CSS}</style></head><body>",
        _svg_block(p.couverture_svg, "cover"),
        "<section class='titlepage'>",
        f"<h1>{html.escape(p.titre)}</h1>",
        f"<div class='subtitle'>{html.escape(p.sous_titre)}</div>",
        f"<div class='author'>{html.escape(p.auteur)}</div></section>",
        "<section class='toc'><h2>Sommaire</h2><ul>",
        *[f"<li>{c.numero}. {html.escape(c.titre)}</li>" for c in p.chapitres],
        "</ul></section>",
    ]
    for c in p.chapitres:
        parts.append(f"<section class='chapter'><h2><small>CHAPITRE {c.numero}</small>{html.escape(c.titre)}</h2>")
        if p.illustre:
            parts.append(_svg_block(c.illustration_svg, "illustration"))
        for s in c.sections:
            parts.append(md.markdown(s.texte, extensions=["extra"]))
        parts.append("</section>")
    if p.quatrieme:
        paras = "".join(f"<p>{html.escape(x)}</p>" for x in p.quatrieme.split("\n") if x.strip())
        parts.append(f"<section class='back'>{paras}</section>")
    parts.append("</body></html>")
    return "\n".join(parts)


def to_markdown(p: BookProject) -> str:
    out = [f"# {p.titre}", f"*{p.sous_titre}*", f"\n{p.auteur}\n"]
    for c in p.chapitres:
        out.append(f"\n## Chapitre {c.numero} — {c.titre}\n")
        out += [s.texte + "\n" for s in c.sections]
    if p.quatrieme:
        out.append("\n---\n## Quatrième de couverture\n\n" + p.quatrieme)
    return "\n".join(out)


def to_pdf(p: BookProject, path: Path) -> Path:
    try:
        from weasyprint import HTML
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("Installez weasyprint pour l'export PDF : pip install weasyprint") from e
    HTML(string=to_html(p)).write_pdf(str(path))
    return path


def to_docx(p: BookProject, path: Path) -> Path:
    """Manuscrit Word (accepté par Amazon KDP). Les illustrations SVG sont fournies à part."""
    from docx import Document
    from docx.enum.text import WD_BREAK

    doc = Document()
    doc.add_heading(p.titre, 0)
    if p.sous_titre:
        doc.add_paragraph(p.sous_titre).italic = True
    doc.add_paragraph(p.auteur)
    for c in p.chapitres:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        doc.add_heading(f"Chapitre {c.numero} — {c.titre}", 1)
        for s in c.sections:
            for block in s.texte.split("\n"):
                b = block.strip()
                if not b:
                    continue
                if b.startswith("#"):
                    doc.add_heading(b.lstrip("#").strip(), 3)
                elif b[:2] in ("- ", "* "):
                    doc.add_paragraph(b[2:].replace("**", ""), style="List Bullet")
                else:
                    doc.add_paragraph(b.replace("**", "").replace("*", ""))
    if p.quatrieme:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        doc.add_heading("Quatrième de couverture", 1)
        doc.add_paragraph(p.quatrieme)
    doc.save(str(path))
    return path


def course_markdown(p: BookProject) -> str:
    f = p.formation or {}
    u, s = f.get("udemy", {}), f.get("skillshare", {})
    out = [f"# Formation Udemy — {u.get('titre', '')}", f"*{u.get('sous_titre', '')}*", "", u.get("description", ""), ""]
    for label, key in (("Objectifs", "objectifs"), ("Prérequis", "prerequis"), ("Public cible", "public_cible")):
        out += [f"## {label}", *[f"- {x}" for x in u.get(key, [])], ""]
    out.append(f"**Prix recommandé :** {u.get('prix_recommande_eur', '')} € — durée ≈ {u.get('duree_totale_min', '')} min\n")
    for i, sec in enumerate(u.get("sections", []), 1):
        out.append(f"## Section {i} — {sec.get('titre', '')}")
        for l in sec.get("lecons", []):
            out.append(f"### {l.get('titre', '')} ({l.get('type', '')}, {l.get('duree_min', '')} min)")
            if l.get("script"):
                out.append(f"> {l['script']}")
            out.append("")
    out += [f"\n# Skillshare — {s.get('titre', '')}", s.get("description", ""),
            f"\n**Projet de classe :** {s.get('projet_de_classe', '')}\n"]
    out += [f"- {l.get('titre', '')} ({l.get('duree_min', '')} min) : {l.get('points_cles', '')}" for l in s.get("lecons", [])]
    out += ["\n# Tunnel de vente livre ↔ formation", str(f.get("tunnel_de_vente", ""))]
    return "\n".join(out)


def course_csv(p: BookProject) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["section", "lecon", "type", "duree_min", "script"])
    for sec in (p.formation or {}).get("udemy", {}).get("sections", []):
        for l in sec.get("lecons", []):
            w.writerow([sec.get("titre"), l.get("titre"), l.get("type"), l.get("duree_min"), l.get("script", "")])
    return buf.getvalue()


def export_all(p: BookProject) -> dict[str, Path]:
    d = p.dossier
    d.mkdir(parents=True, exist_ok=True)
    files = {
        "html": d / f"{p.slug}.html",
        "markdown": d / f"{p.slug}.md",
        "docx": d / f"{p.slug}.docx",
    }
    files["html"].write_text(to_html(p), encoding="utf-8")
    files["markdown"].write_text(to_markdown(p), encoding="utf-8")
    to_docx(p, files["docx"])
    try:
        files["pdf"] = to_pdf(p, d / f"{p.slug}.pdf")
    except Exception:  # weasyprint absent ou bibliothèques système manquantes
        pass
    if p.couverture_svg:
        files["couverture"] = d / "couverture.svg"
        files["couverture"].write_text(p.couverture_svg, encoding="utf-8")
    illus = d / "illustrations"
    for c in p.chapitres:
        if c.illustration_svg:
            illus.mkdir(exist_ok=True)
            (illus / f"chapitre-{c.numero:02d}.svg").write_text(c.illustration_svg, encoding="utf-8")
    if p.formation:
        files["formation"] = d / "formation.md"
        files["formation"].write_text(course_markdown(p), encoding="utf-8")
        files["formation_csv"] = d / "formation_udemy.csv"
        files["formation_csv"].write_text(course_csv(p), encoding="utf-8")
    return files
