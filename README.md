# 📚 BookForge

Une application qui **écrit des livres complets de plusieurs centaines de pages** (roman, essai, guide,
livre d'histoires pour enfants, thriller, fantasy, business, développement personnel, biographie, cuisine),
avec **illustrations**, **couverture**, **quatrième de couverture**, et qui les transforme en
**formation Udemy et Skillshare**. Elle **calcule le prix de vente** et fait une **étude de marché
sur le web** (best-sellers, tendances, sujets porteurs) pour choisir quoi écrire.

Le texte est généré par Claude (API Anthropic).

## Fonctionnalités

| Onglet | Ce qu'il fait |
|---|---|
| 🔎 **Tendances** | Recherche web sur Amazon/Kindle, Fnac, Apple Books, Kobo, Babelio/Goodreads, Udemy, Skillshare : best-sellers, sujets en hausse et leur concurrence, formations populaires, prix constatés, **idées de livres classées par potentiel**. Un clic envoie une idée vers « Nouveau livre ». |
| ✍️ **Nouveau livre** | Choix du genre, du sujet, du public, du ton et du **nombre de pages (20 à 900)**. Génère un titre vendeur, un plan détaillé (chapitres + sections) et une **bible de continuité** (personnages, univers, thèse, style) que vous pouvez modifier. |
| 📖 **Écriture** | Rédaction section par section, affichée en direct et **sauvegardée en continu** : si vous fermez l'application, le projet reprend là où il s'était arrêté. Chaque section peut être réécrite. |
| 🎨 **Illustrations & couvertures** | Une illustration vectorielle (SVG) par chapitre dans le style du genre, une couverture avant (format Kindle 1:1,6) et la quatrième de couverture (modifiable). |
| 🎓 **Formation** | Cours Udemy complet (sections, leçons, **scripts vidéo**, quiz, objectifs, prérequis, prix) + version Skillshare (leçons courtes + projet de classe) + tunnel de vente livre ↔ formation. |
| 💶 **Prix** | Prix ebook (dans la fourchette 70 % KDP), prix broché (couvre le coût d'impression avec marge), prix Udemy (grille officielle), redevance par vente et projection de revenus mensuels. Utilise les prix médians de l'étude de marché quand elle existe. |
| 📦 **Exports** | **PDF** imprimable (6×9 pouces, avec couverture et illustrations), **Word .docx** (accepté par Amazon KDP), HTML, Markdown, SVG des illustrations, plan de formation en Markdown et **CSV** du programme Udemy. |

## Installation

Python 3.10 ou plus.

```bash
pip install -r requirements.txt
```

Clé API Anthropic (créée sur console.anthropic.com) :

```bash
export ANTHROPIC_API_KEY="votre-clé"
```

## Utilisation

### Interface graphique

```bash
streamlit run app.py
```

Puis ouvrez http://localhost:8501.

Parcours conseillé : **Tendances** → choisir une idée → **Nouveau livre** → relire la bible → **Écriture**
(ou le bouton « 🚀 Tout générer ») → **Prix** → **Exports**.

### Ligne de commande

Étude de marché :

```bash
python -m bookforge.cli tendances --genre "Guide pratique" --mots-cles "IA, productivité"
```

Livre complet (manuscrit, illustrations, couvertures, formation, prix, exports) :

```bash
python -m bookforge.cli livre --titre "Le Jardin des Étoiles" --genre jeunesse --sujet "Une petite fille qui cultive des étoiles" --pages 60 --public "enfants 6-9 ans"
```

Reprendre un projet interrompu :

```bash
python -m bookforge.cli reprendre projets/le-jardin-des-etoiles/projet.json
```

Les fichiers produits se trouvent dans `projets/<nom-du-livre>/`.

## Coût et durée indicatifs

Un livre de 300 pages fait environ 75 000 mots. Avec le modèle par défaut (`claude-opus-5-5`), comptez
de l'ordre de **10 à 25 $ d'API** et **2 à 4 heures** de génération pour le livre complet avec illustrations
et formation. Pour réduire les coûts : `export BOOKFORGE_EFFORT=medium`, ou désactivez les illustrations.

## Réglages (variables d'environnement)

| Variable | Défaut | Rôle |
|---|---|---|
| `BOOKFORGE_MODEL` | `claude-opus-5-5` | Modèle Claude utilisé |
| `BOOKFORGE_EFFORT` | `high` | Profondeur de réflexion (`low`, `medium`, `high`, `xhigh`, `max`) |
| `BOOKFORGE_PROJECTS` | `projets` | Dossier de sauvegarde des projets |

## À savoir

- **Relisez avant de publier.** Le texte est original mais doit être relu (cohérence, faits, chiffres).
  Amazon KDP demande de **déclarer le contenu généré par IA** lors de la publication.
- **Barèmes de prix** (impression KDP, redevances, grille Udemy) : ce sont des approximations
  centralisées dans `bookforge/pricing.py`, à vérifier car elles changent. En France, le **prix
  unique du livre** (loi Lang) s'applique.
- **Illustrations** : vectorielles, générées sous forme de code SVG (nettes à toute taille, sans clé
  supplémentaire). Pour un rendu photoréaliste, la description de chaque illustration est conservée
  dans `projet.json` (`illustration_prompt`) et peut être utilisée dans un générateur d'images.
- **Étude de marché** : les classements viennent de recherches web en direct, avec leurs sources ;
  les plateformes ne publient pas toutes leurs chiffres de vente, certains sont donc estimés (et signalés comme tels).
- En cas de refus du modèle sur une demande, l'application bascule automatiquement sur un modèle de
  repli (`fallbacks="default"`).

## Tests

```bash
python -m pytest -q
```

Les tests tournent hors-ligne (le modèle est simulé) et vérifient la chaîne complète jusqu'au PDF.

## Structure

```
app.py                     interface Streamlit
bookforge/
  config.py                réglages, genres
  llm.py                   appels à Claude (streaming, JSON, recherche web, repli)
  trends.py                étude de marché / best-sellers / idées
  project.py               projet sauvegardé sur disque (reprise)
  writer.py                plan, bible, rédaction section par section
  illustrations.py         illustrations SVG, couverture, 4e de couverture
  course.py                formation Udemy + Skillshare
  pricing.py               prix de vente et redevances
  export.py                PDF, DOCX, HTML, Markdown, CSV
  pipeline.py              enchaînement complet
  cli.py                   ligne de commande
tests/                     tests hors-ligne
```
