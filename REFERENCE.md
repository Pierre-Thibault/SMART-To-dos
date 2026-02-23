# Référence de structure — objectifs.md

Ce document décrit la structure complète du fichier `objectifs.md` et
toutes les valeurs acceptées par le système.

## Principe fondamental

Le système repose sur un **modèle récursif unifié**. Chaque élément —
objectif, sous-objectif, sous-tâche — est défini par un heading
Markdown suivi de métadonnées YAML. La hiérarchie est donnée par
le niveau du heading :

- **Avec enfants** → sa progression est calculée à partir de ses enfants
- **Sans enfants** → sa progression vient de son propre suivi (tracking + journal)

Cette logique s'applique à tous les niveaux de profondeur.

## Vue d'ensemble du fichier

```
objectifs.md
├── Frontmatter YAML (optionnel)
├── ## id : Objectif                  ← niveau 1
│   ├── Métadonnées (liste YAML)
│   ├── ### id : Sous-objectif        ← niveau 2
│   │   ├── Métadonnées
│   │   ├── #### id : Sous-tâche      ← niveau 3
│   │   │   └── Métadonnées
│   │   └── #### id : Sous-tâche
│   ├── ### id : Sous-objectif
│   └── ### Journal de temps          ← tableau Markdown
├── ## id : Autre objectif
│   └── ...
```

---

## Format d'un élément

Chaque élément est un heading Markdown avec le format :

```
## identifiant : Titre
```

L'identifiant est une chaîne sans espaces (lettres, chiffres, tirets).
Le heading `#` (niveau 1) est ignoré par le parser.

Les niveaux correspondent à :

| Heading  | Rôle                    |
|----------|-------------------------|
| `##`     | Objectif de niveau 1    |
| `###`    | Enfant direct           |
| `####`   | Petit-enfant            |
| `#####`  | Arrière-petit-enfant    |
| `######` | Profondeur maximale (5) |

### Métadonnées

Liste YAML directement sous le heading. Tous les champs sont optionnels.

| Champ      | Description                      | Défaut        |
|------------|----------------------------------|---------------|
| status     | voir statuts ci-dessous          | `not_started` |
| priority   | voir priorités ci-dessous        | hérité du parent, ou `medium` |
| type       | `open` ou `bounded`              | `bounded`     |
| tracking   | bloc de suivi (si pas d'enfants) | —             |
| actual     | valeur actuelle (nombre + unité) | `0`           |
| start      | `YYYY-MM-DD`                     | —             |
| end        | `YYYY-MM-DD` ou `YYYY-MM-DD!`   | —             |
| depends_on | liste d'ids (même niveau)        | `[]`          |
| smart      | bloc SMART (voir plus bas)       | —             |

Les champs suivants ne s'appliquent qu'aux objectifs de **niveau 1** (`##`) :

| Champ   | Description                  | Défaut    |
|---------|------------------------------|-----------|
| created | `YYYY-MM-DD`                 | —         |
| tags    | `[tag1, tag2]`               | `[]`      |

### Héritage de priorité

Si un élément ne déclare pas de `priority`, il hérite automatiquement
de la priorité de son parent. Si un élément racine (`##`) n'a pas de
priorité, la valeur par défaut est `medium`.

Un enfant peut toujours déclarer sa propre priorité pour remplacer
celle du parent.

### Règle de progression

Si un élément a des enfants (headings de niveau inférieur sous lui),
**il ne doit pas avoir de `tracking`**. Sa progression sera calculée
automatiquement à partir de ses enfants.

Si un élément n'a **pas** d'enfants, il doit avoir un `tracking`
pour être suivi via le journal — **sauf** s'il a une date de fin
fixe (`end` avec `!`).

### Sources de progression (parent)

Quand un parent calcule sa progression à partir de ses enfants :

| Source          | Condition                                  | Méthode                       |
|-----------------|--------------------------------------------|-------------------------------|
| `weighted`      | Toutes les feuilles ont la même unité      | Moyenne pondérée par cible    |
| `predicted`     | Unités mixtes + prédiction disponible      | % temporel (durée écoulée)    |
| `insufficient`  | Unités mixtes + pas assez de données       | Pas de progression affichée   |

### Statut auto-dérivé

Le statut peut être déduit automatiquement dans deux cas :

**Parents** (déduit des enfants bornés, hors `open` et `cancelled`) :

| Enfants bornés                       | Statut déduit  |
|--------------------------------------|----------------|
| Tous `done`                          | `done`         |
| Tous `cancelled`                     | `cancelled`    |
| Tous `not_started` ou `cancelled`    | `not_started`  |
| Tous `done` ou `cancelled`           | `done`         |
| Mélange incluant `in_progress`       | `in_progress`  |

**Feuilles** (seulement si le statut est `not_started` par défaut) :

| Condition                         | Statut déduit  |
|-----------------------------------|----------------|
| Entrées journal + progression 100% | `done`         |
| Entrées journal + progression < 100% | `in_progress` |
| Aucune entrée                     | `not_started`  |

### Objectif marqué `done`

Quand un objectif feuille est explicitement marqué `done`, sa valeur
courante est automatiquement égale à sa cible, indépendamment du
journal d'activité. La progression est toujours 100%.

### Date de fin fixe

Ajouter `!` après la date `end` indique que la tâche se termine
à une date prédéterminée. La progression est alors purement
temporelle et ne nécessite aucune entrée dans le journal.

```yaml
- start: 2026-02-01
- end: 2026-04-30!
```

Comportement :

- La progression augmente linéairement de `start` à `end`
- La prédiction de complétion est toujours la date `end`
- Il ne peut pas y avoir de retard
- Passé la date `end`, le statut passe automatiquement à `done`
- Aucun `tracking` ni entrée dans le journal n'est requis

Cas d'usage typiques : cours avec date de fin connue, période
d'essai, abonnement, délai administratif.

---

## Exemples

### Objectif avec sous-objectifs

```markdown
## japonais : Apprendre le japonais N4

- type: open
- status: in_progress
- priority: high
- created: 2026-01-05
- tags: [langues, personnel]

### jp-01 : Maîtriser les kana

- status: done
- tracking:
    mode: cumulative
- actual: 12 heures
- start: 2026-01-05
- end: 2026-01-20

### jp-02 : Compléter Genki I

- depends_on: [jp-01]
- start: 2026-01-21

### Journal de temps

| Date       | Tâche  | Valeur     | Notes      |
|------------|--------|------------|------------|
| 2026-01-05 | jp-01  | 0.75 heures | Hiragana  |
```

Dans cet exemple, `jp-02` hérite de la priorité `high` du parent
`japonais`. Son statut sera déduit automatiquement des entrées
du journal.

### Objectif sans sous-objectifs (journal au niveau feuille)

```markdown
## course : Courir 60 minutes sans arrêt

- type: bounded
- status: in_progress
- priority: medium
- created: 2026-01-10
- tracking:
    mode: performance
    target: 60 minutes

### Journal de temps

| Date       | Valeur     | Notes              |
|------------|------------|--------------------|
| 2026-01-10 | 12 minutes | Première course    |
| 2026-01-13 | 15 minutes | Un peu mieux       |
```

Ici la colonne Tâche est absente car l'objectif n'a pas
d'enfants. L'identifiant `course` est déduit automatiquement.

### Journaux mixtes (niveau objectif et niveau feuille)

```markdown
## lire : Programme de lecture

- created: 2026-01-01

### lire-01 : Lire Dune

- tracking:
    target: 412 pages

#### Journal de temps

| Date       | Valeur   | Notes      |
|------------|----------|------------|
| 2026-01-10 | 35 pages | Chapitre 1 |
| 2026-01-15 | 42 pages | Chapitre 2 |

### lire-02 : Lire Neuromancer

- tracking:
    target: 271 pages

### Journal de temps

| Date       | Tâche    | Valeur   | Notes      |
|------------|----------|----------|------------|
| 2026-01-20 | lire-02  | 30 pages | Début      |
```

Dans cet exemple :

- `lire-01` a son propre journal (format court, sans colonne Tâche)
- Le journal au niveau `##` utilise le format complet pour `lire-02`
- Les deux formats coexistent dans le même fichier

### Hiérarchie à 3 niveaux

```markdown
## site : Déployer mon site

### site-02 : Développer le frontend

- depends_on: [site-01]

#### site-02-01 : Page d'accueil

- status: done
- tracking:
    mode: cumulative
    target: 100%
- actual: 100%

#### site-02-02 : Page projets

- tracking:
    mode: cumulative
    target: 100%
```

Dans cet exemple :

- `site-02` tire sa progression de ses enfants (`site-02-01` et `site-02-02`)
- `site` tire sa progression de tous ses sous-objectifs `###`
- Aucun statut n'est déclaré — tout est dérivé automatiquement

### Sous-objectif à date fixe

```markdown
### espagnol-01 : Suivre le cours intermédiaire

- start: 2026-02-01
- end: 2026-04-30!
```

Pas de `tracking` ni de journal nécessaire. La progression
passe de 0% à 100% entre le 1er février et le 30 avril.

---

## Valeurs de référence

### `status`

| Valeur        | Description         |
|---------------|---------------------|
| `not_started` | Pas encore commencé |
| `in_progress` | En cours            |
| `done`        | Terminé             |
| `paused`      | En pause            |
| `cancelled`   | Annulé              |

Les éléments `cancelled` sont exclus du calcul de progression
de leur parent.

### `priority`

| Valeur     | Rang | Description                       |
|------------|------|-----------------------------------|
| `optional` | 0    | Facultatif                        |
| `low`      | 1    | Peu urgent                        |
| `medium`   | 2    | Priorité normale (défaut)         |
| `high`     | 3    | Important                         |
| `capital`  | 4    | Critique, à traiter en premier    |

Si non déclarée, la priorité est **héritée du parent**. Les
objectifs racine sans priorité reçoivent `medium`.

### `type`

| Valeur    | Description                                             |
|-----------|---------------------------------------------------------|
| `bounded` | Objectif avec une fin définie (défaut)                  |
| `open`    | Objectif continu, sans fin prévue                       |

Le type peut être défini à **n'importe quel niveau**. Un élément
de type `open` :

- Est exclu du calcul de progression de son parent
- N'affiche pas de barre de progression dans la vue d'ensemble
- Affiche ses sous-objectifs dans les prédictions
- Affiche « Objectif ouvert » au lieu d'un résumé de prédiction

---

## Bloc `tracking`

Le tracking ne s'applique qu'aux éléments **sans enfants** (feuilles
de l'arbre).

```yaml
- tracking:
    mode: cumulative
    target: 382 pages
```

| Champ  | Obligatoire | Description                   | Défaut       |
|--------|-------------|-------------------------------|--------------|
| mode   | non         | `cumulative` ou `performance` | `cumulative` |
| target | non         | nombre + unité                | —            |

### Modes

| Mode          | Comportement                                          | Exemple                |
|---------------|-------------------------------------------------------|------------------------|
| `cumulative`  | Les entrées du journal s'additionnent vers la cible   | 200/382 pages lues     |
| `performance` | Chaque entrée est indépendante, le **maximum** compte | Record : 32/60 minutes |
| `fixed`       | Progression temporelle automatique (date de fin `!`)  | Cours : 16/100 jours   |

Le mode `fixed` est attribué automatiquement aux éléments dont la
date `end` se termine par `!`. Il ne se configure pas dans le bloc
`tracking`.

### Unités

Les unités sont du **texte libre**. Écrivez ce que vous voulez après
le nombre :

```
target: 382 pages
target: 30 heures
target: 60 minutes
target: 100%
target: 50 chapitres
target: 12 modules
target: 200 km
```

### Champ `actual`

Valeur initiale de progression. Même format : nombre + unité.

```yaml
- actual: 180 pages
- actual: 55%
- actual: 12 heures
```

Si des entrées existent dans le journal pour cet élément, elles
remplacent la valeur de `actual` (somme pour cumulatif, max pour
performance).

---

## Bloc SMART (optionnel)

Peut être défini sur n'importe quel élément, à n'importe quel niveau.

```yaml
- smart:
    specific: "Description précise de l'objectif"
    measurable: "Comment mesurer le succès"
    actionable: "Comment l'objectif peut être atteint"
    relevant: "Pourquoi c'est pertinent"
    time_bound: "YYYY-MM-DD"
```

Tous les champs sont optionnels. Le champ `time_bound` sert de
date limite pour les prédictions du dashboard. Une heure peut
optionnellement être ajoutée :

```yaml
time_bound: "2026-04-15"
time_bound: "2026-04-15 14:30"
```

---

## Journal de temps

Le journal est un heading « Journal de temps » qui contient un
tableau Markdown d'entrées d'activité. Il peut être placé à
**n'importe quel niveau** de la hiérarchie.

### Règles de placement

| Contexte                       | Format requis | Colonne Tâche |
|--------------------------------|---------------|---------------|
| Sous une **feuille** (pas d'enfants) | Court         | Absente (id implicite) |
| Sous un **nœud avec enfants**  | Complet       | Obligatoire   |

**Validation des identifiants** : chaque entrée doit référencer un
identifiant **déjà défini** plus haut dans le fichier. Les entrées
dont l'identifiant est inconnu ou défini plus bas sont silencieusement
ignorées.

### Format complet (avec colonne Tâche)

Utilisé sous un nœud qui a des enfants. La colonne Tâche peut
référencer n'importe quel descendant, quelle que soit la profondeur.

```markdown
## g : Mon objectif

### a : Tâche A

- tracking:
    target: 100 pages

### b : Tâche B

- tracking:
    target: 50 pages

### Journal de temps

| Date       | Tâche | Valeur   | Notes      |
|------------|-------|----------|------------|
| 2026-01-22 | a     | 12 pages | Chapitre 1 |
| 2026-02-10 | b     | 8 pages  |            |
```

| Colonne | Format                                      |
|---------|---------------------------------------------|
| Date    | `YYYY-MM-DD`                                |
| Tâche   | id d'un élément défini avant le journal      |
| Valeur  | nombre + unité en texte libre               |
| Notes   | texte libre (optionnel)                     |

Le journal peut aussi être placé à un niveau intermédiaire. Par
exemple, sous un `###` qui a ses propres enfants `####` :

```markdown
### parent : Module principal

#### sub-a : Partie A

- tracking:
    target: 40 pages

#### sub-b : Partie B

- tracking:
    target: 60 pages

#### Journal de temps

| Date       | Tâche | Valeur   | Notes |
|------------|-------|----------|-------|
| 2026-01-10 | sub-a | 10 pages |       |
| 2026-01-15 | sub-b | 5 pages  |       |
```

### Format court (sans colonne Tâche)

Utilisé sous une feuille (élément sans enfants). L'identifiant
est déduit automatiquement du parent.

```markdown
### task-01 : Lire le livre

- tracking:
    target: 382 pages

#### Journal de temps

| Date       | Valeur   | Notes      |
|------------|----------|------------|
| 2026-01-22 | 35 pages | Chapitre 1 |
| 2026-01-25 | 42 pages | Chapitre 2 |
```

| Colonne | Format                        |
|---------|-------------------------------|
| Date    | `YYYY-MM-DD`                  |
| Valeur  | nombre + unité en texte libre |
| Notes   | texte libre (optionnel)       |

Le format minimal à deux colonnes (sans Notes) est aussi accepté :

```markdown
#### Journal de temps

| Date       | Valeur     |
|------------|------------|
| 2026-01-10 | 12 minutes |
| 2026-01-13 | 15 minutes |
```

### Détection automatique du format

Le parser détecte le format (complet ou court) de deux façons :

1. **Par la ligne d'en-tête** : si les colonnes incluent « Tâche »
   ou « Task », c'est le format complet ; sinon, c'est le format
   court.
2. **Par le nombre de colonnes** : en l'absence d'en-tête, un
   tableau de 2–3 colonnes sous une feuille est interprété comme
   format court.

### Coexistence des formats

Plusieurs journaux peuvent coexister dans le même objectif, à
différents niveaux. Chaque feuille peut avoir son propre journal
court, et un journal complet peut exister à un niveau supérieur :

```markdown
## lire : Programme de lecture

### lire-01 : Lire Dune

- tracking:
    target: 412 pages

#### Journal de temps

| Date       | Valeur   |
|------------|----------|
| 2026-01-10 | 35 pages |

### lire-02 : Lire Neuromancer

- tracking:
    target: 271 pages

### Journal de temps

| Date       | Tâche   | Valeur   | Notes |
|------------|---------|----------|-------|
| 2026-01-20 | lire-02 | 30 pages |       |
```

---

## Dépendances

Les dépendances fonctionnent entre éléments du **même niveau** :

```yaml
- depends_on: [jp-01, jp-02]
```

Les dépendances inter-niveaux ne sont pas supportées.

---

## Prédictions

Le dashboard calcule des prédictions à partir de **2 entrées minimum**
dans le journal.

| Mode        | Calcul de vélocité                                              |
|-------------|-----------------------------------------------------------------|
| cumulative  | total accumulé ÷ jours entre première et dernière entrée       |
| performance | pente de la droite de régression linéaire sur les entrées       |

Pour les éléments avec enfants, la date de complétion prédite est
la plus tardive parmi les prédictions de ses enfants actifs.

Si certains enfants n'ont pas encore de prédiction (pas assez de
données), la prédiction du parent est marquée comme **partielle** —
elle représente le minimum connu mais n'est pas définitive.

Les éléments `cancelled` et `open` sont exclus de tous les calculs.

---

## Dashboard

### Vue d'ensemble

Affiche les statistiques globales et chaque objectif avec sa barre
de progression, ses sous-objectifs et sa mini-timeline. Les objectifs
ouverts n'affichent pas de barre de progression.

### Gantt

Diagramme de Gantt montrant la durée prévue de chaque objectif et
sous-objectif. Les éléments annulés sont exclus.

### Prédictions

Cartes détaillées avec la timeline de chaque sous-objectif et un
résumé (en bonne voie / en retard). Les dates fixes affichent
« Fin: » au lieu de « Prédit: ». Les objectifs ouverts affichent
leurs sous-objectifs mais indiquent « Objectif ouvert » en résumé.

### Tri

Le sélecteur en haut à droite permet de trier les objectifs :

- **Ordre du fichier** (défaut)
- **Par nom** (alphabétique)
- **Par priorité et nom** (priorité décroissante, puis alphabétique)

Le tri s'applique aux trois vues simultanément.

### Filtres

La barre de filtres sous le titre permet de filtrer par priorité
et par catégorie (tags). Les boutons sont des toggles : cliquer
active/désactive le filtre. Aucun filtre actif = tout visible.
