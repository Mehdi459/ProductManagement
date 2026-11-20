"""Tests hors-ligne : Claude est remplacé par un faux modèle déterministe."""
import json

import pytest

from bookforge import config, llm, pipeline, pricing, writer
from bookforge.project import BookProject

SVG = '<svg viewBox="0 0 10 10" onload="x()"><script>evil()</script><circle cx="5" cy="5" r="4"/></svg>'


def fake_generate(prompt, system="", max_tokens=0, web_search=False, on_text=None, effort=None):
    if "étude de marché" in prompt:
        return "```json\n" + json.dumps({"best_sellers": [], "tendances": [], "idees_de_livres": [],
                                         "prix_constates": {"ebook": {"median": 6.99}}, "synthese": "ok"}) + "\n```"
    if "Conçois le livre" in prompt:
        n, s = writer.plan_structure(int(prompt.split("Taille visée : ")[1].split(" ")[0]))
        return json.dumps({"titre": "Le Titre", "sous_titre": "Sous", "bible": "Bible",
                           "chapitres": [{"titre": f"C{i}", "resume": "r", "illustration": "scène",
                                          "sections": [{"titre": f"S{j}", "resume": "r"} for j in range(s)]}
                                         for i in range(n)]})
    if "formation vidéo" in prompt:
        return json.dumps({"udemy": {"titre": "Cours", "duree_totale_min": 240,
                                     "sections": [{"titre": "A", "lecons": [{"titre": "L", "type": "video",
                                                                            "duree_min": 5, "script": "Bonjour"}]}]},
                           "skillshare": {"titre": "SK"}, "tunnel_de_vente": "QR code"})
    if "<svg>" in prompt:
        return "Voici :\n" + SVG
    if "quatrième de couverture" in prompt:
        return "Accroche.\nPrésentation."
    mots = int(prompt.split("Écris environ ")[1].split(" ")[0])
    return " ".join(["mot"] * mots)


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "generate", fake_generate)
    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path)


def test_extract_json_variants():
    assert llm.extract_json('blabla ```json\n{"a": 1}\n``` fin') == {"a": 1}
    assert llm.extract_json('Résultat : [1, 2] .') == [1, 2]


def test_plan_structure_scales_with_pages():
    n1, s1 = writer.plan_structure(100)
    n2, s2 = writer.plan_structure(600)
    assert n2 * s2 > n1 * s1


def test_full_pipeline_reaches_target_pages(tmp_path):
    p = BookProject(titre="Essai", genre="guide", sujet="productivité", pages_cible=300)
    files = pipeline.run_all(p)
    assert p.titre == "Le Titre"
    assert all(c.done for c in p.chapitres)
    assert 280 <= p.pages <= 340, p.pages
    assert "script" not in p.couverture_svg and "onload" not in p.couverture_svg
    assert p.quatrieme and p.formation and p.prix["ebook"]["prix"] > 0
    for key in ("html", "markdown", "docx", "formation", "formation_csv"):
        assert files[key].exists()
    assert "pdf" in files and files["pdf"].stat().st_size > 10_000

    assert p.dossier.name == "essai"  # dossier stable malgré le changement de titre
    assert len(list(tmp_path.glob("*/projet.json"))) == 1
    reloaded = BookProject.load(p.dossier / "projet.json")
    assert reloaded.mots == p.mots


def test_resume_only_writes_missing_sections():
    p = BookProject(titre="R", genre="roman", sujet="x", pages_cible=60)
    writer.create_outline(p)
    p.chapitres[0].sections[0].texte = "déjà écrit"
    writer.write_book(p)
    assert p.chapitres[0].sections[0].texte == "déjà écrit"


def test_prices():
    pr = pricing.compute_prices("roman", 350, duree_formation_min=180)
    assert 2.99 <= pr["ebook"]["prix"] <= 9.99
    assert pr["broche"]["redevance_par_vente"] > 0
    assert pr["udemy"]["prix_catalogue"] in pricing.UDEMY_TIERS
    assert str(pr["broche"]["prix"]).endswith(".9")
    big = pricing.compute_prices("roman", 800, couleur=True)
    assert big["broche"]["redevance_par_vente"] > 0  # jamais vendu à perte
    assert len(pricing.scenarios(pr)) == 3
