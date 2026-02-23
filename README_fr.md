# SMART Goals Tracker

Système de suivi d'objectifs avec dashboard web, diagramme de Gantt et prédictions.
Tout dans un seul fichier Markdown, éditable dans n'importe quel éditeur de texte.

## Principe

Le système repose sur un modèle récursif unifié. Chaque élément (objectif,
sous-objectif, sous-tâche) suit la même logique :

- **Avec enfants** → progression calculée à partir de ses enfants
- **Sans enfants** → progression suivie via son propre tracking et le journal

La profondeur est illimitée, mais en pratique 1 à 3 niveaux suffisent.

## Fonctionnalités

- **Un seul fichier** `objectifs.md`
- **Arbre récursif** : profondeur illimitée, même logique à chaque niveau
- **SMART optionnel** sur n'importe quel élément
- **Deux modes de suivi** : cumulatif (somme) et performance (maximum)
- **Dates fixes** : progression temporelle automatique (`end: YYYY-MM-DD!`)
- **Unités libres** : pages, heures, minutes, %, km, chapitres...
- **Priorités** : optional, low, medium, high, capital (héritées du parent)
- **Dépendances multiples** entre éléments du même niveau
- **Prédictions dès 2 entrées** dans le journal
- **Progression pondérée** par cible pour unités homogènes
- **Statut auto-dérivé** : parents depuis enfants, feuilles depuis entrées
- **Objectifs ouverts** (`type: open`) exclus du calcul parent
- **Tri** : ordre du fichier, par nom, par priorité et nom
- **Filtres** : par priorité et par catégorie (tags)
- **Thème clair/sombre** automatique selon les préférences système
- **Dashboard web** : Vue d'ensemble, Gantt, Prédictions
- **Gestion des erreurs** : affichage explicite des problèmes de syntaxe avec numéros de ligne

## Installation

### Avec Nix

```bash
nix develop
```

### Sans Nix

```bash
pip install -r requirements.txt --break-system-packages
```

## Configuration

Copier le fichier de préférences et l'adapter :

```bash
cp src/preferences_template.py src/preferences.py
```

Modifier `src/preferences.py` :

```python
GOALS_FILE = "/chemin/vers/mon/objectifs.md"
```

Ce fichier est ignoré par git.

## Utilisation

```bash
PYTHONPATH=src uvicorn app.main:app --reload
```

Avec Nix, le `PYTHONPATH` est configuré automatiquement :

```bash
uvicorn app.main:app --reload
```

Ouvrir http://localhost:8000.

Sans `preferences.py`, l'application utilise `./sample_vault/objectifs.md`.

## Tests

Lancer la suite de tests :

```bash
PYTHONPATH=src python -m pytest tests/ -v
```

Avec couverture :

```bash
PYTHONPATH=src python -m pytest tests/ --cov=app --cov-report=term-missing
```

Les tests couvrent :

- **parser.py** : extraction valeur/unité, dates, métadonnées YAML,
  journal de temps, découpage en sections, construction d'arbre,
  héritage de priorité, intégration complète.
- **analytics.py** : valeur courante, vélocité, prédiction, pourcentage
  feuille, poids de sous-arbre, unités, progression pondérée/prédite,
  dérivation de statut, objectifs ouverts, dates fixes, on-track.
- **main.py** : sérialisation JSON, endpoints API (`/api/goals`,
  `/api/goals/{id}`, `/api/gantt`), dashboard HTML.

## Documentation

Voir [REFERENCE.md](REFERENCE.md) pour la structure complète du fichier
et toutes les valeurs possibles.

## Architecture

```
smart-goals/
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── parser.py              # Parse le fichier Markdown (récursif)
│   │   ├── analytics.py           # Progression, vélocité, prédictions
│   │   └── main.py                # API FastAPI
│   └── preferences_template.py    # Template de configuration
├── tests/
│   ├── conftest.py                # Fixtures partagées
│   ├── test_parser.py             # Tests du parser
│   ├── test_analytics.py          # Tests de l'analytique
│   ├── test_main.py               # Tests de l'API
│   └── test_edge_cases.py         # Cas limites
├── static/
│   ├── index.html                 # Structure HTML
│   ├── theme-light.css            # Thème clair
│   ├── theme-dark.css             # Thème sombre
│   └── app.js                     # Logique du dashboard
├── sample_vault/
│   └── objectifs.md               # Exemple avec 3 objectifs
├── .gitignore
├── flake.nix
├── requirements.txt
├── REFERENCE.md
└── README.md
```

## Licence

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
