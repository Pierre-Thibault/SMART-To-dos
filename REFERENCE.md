# Structure Reference — objectifs.md

This document describes the complete structure of the `objectifs.md` file and
all values accepted by the system.

## Fundamental Principle

The system relies on a **unified recursive model**. Each element —
goal, sub-goal, sub-task — is defined by a Markdown heading
followed by YAML metadata. The hierarchy is determined by
the heading level:

- **With children** → its progress is calculated from its children
- **Without children** → its progress comes from its own tracking (tracking + journal)

This logic applies to all depth levels.

## File Overview

```
objectifs.md
├── YAML Frontmatter (optional)
├── ## id : Goal                      ← level 1
│   ├── Metadata (YAML list)
│   ├── ### id : Sub-goal             ← level 2
│   │   ├── Metadata
│   │   ├── #### id : Sub-task        ← level 3
│   │   │   └── Metadata
│   │   └── #### id : Sub-task
│   ├── ### id : Sub-goal
│   └── ### Time Journal              ← Markdown table
├── ## id : Another goal
│   └── ...
```

---

## Element Format

Each element is a Markdown heading with the format:

```
## identifier : Title
```

The identifier is a string without spaces (letters, numbers, hyphens).
The `#` heading (level 1) is ignored by the parser.

The levels correspond to:

| Heading  | Role                    |
|----------|-------------------------|
| `##`     | Level 1 goal            |
| `###`    | Direct child            |
| `####`   | Grandchild              |
| `#####`  | Great-grandchild        |
| `######` | Maximum depth (5)       |

### Metadata

YAML list directly under the heading. All fields are optional.

| Field      | Description                      | Default       |
|------------|----------------------------------|---------------|
| status     | see statuses below               | `not_started` |
| priority   | see priorities below             | inherited from parent, or `medium` |
| type       | `open` or `bounded`              | `bounded`     |
| tracking   | tracking block (if no children)  | —             |
| actual     | current value (number + unit)    | `0`           |
| start      | `YYYY-MM-DD`                     | —             |
| end        | `YYYY-MM-DD` or `YYYY-MM-DD!`    | —             |
| depends_on | list of ids (same level)         | `[]`          |
| smart      | SMART block (see below)          | —             |

The following fields only apply to **level 1** goals (`##`):

| Field   | Description                  | Default   |
|---------|------------------------------|-----------|
| created | `YYYY-MM-DD`                 | —         |
| tags    | `[tag1, tag2]`               | `[]`      |

### Priority Inheritance

If an element does not declare a `priority`, it automatically inherits
the priority of its parent. If a root element (`##`) has no
priority, the default value is `medium`.

A child can always declare its own priority to override
the parent's.

### Progress Rule

If an element has children (lower-level headings under it),
**it must not have `tracking`**. Its progress will be calculated
automatically from its children.

If an element has **no** children, it must have `tracking`
to be tracked via the journal — **except** if it has a fixed
end date (`end` with `!`).

### Progress Sources (parent)

When a parent calculates its progress from its children:

| Source          | Condition                                  | Method                        |
|-----------------|--------------------------------------------|-------------------------------|
| `weighted`      | All leaves have the same unit              | Weighted average by target    |
| `predicted`     | Mixed units + prediction available         | % temporal (elapsed duration) |
| `insufficient`  | Mixed units + not enough data              | No progress displayed         |

### Auto-derived Status

Status can be automatically inferred in two cases:

**Parents** (derived from bounded children, excluding `open` and `cancelled`):

| Bounded children                     | Derived status |
|--------------------------------------|----------------|
| All `done`                           | `done`         |
| All `cancelled`                      | `cancelled`    |
| All `not_started` or `cancelled`     | `not_started`  |
| All `done` or `cancelled`            | `done`         |
| Mix including `in_progress`          | `in_progress`  |

**Leaves** (only if status is `not_started` by default):

| Condition                         | Derived status |
|-----------------------------------|----------------|
| Journal entries + 100% progress   | `done`         |
| Journal entries + progress < 100% | `in_progress`  |
| No entries                        | `not_started`  |

### Goal Marked `done`

When a leaf goal is explicitly marked `done`, its current
value automatically equals its target, regardless of the
activity journal. Progress is always 100%.

### Fixed End Date

Adding `!` after the `end` date indicates that the task ends
at a predetermined date. Progress is then purely
time-based and requires no journal entries.

```yaml
- start: 2026-02-01
- end: 2026-04-30!
```

Behavior:

- Progress increases linearly from `start` to `end`
- Completion prediction is always the `end` date
- There cannot be delay
- After the `end` date, status automatically becomes `done`
- No `tracking` or journal entries required

Typical use cases: courses with known end date, trial period,
subscription, administrative deadline.

---

## Examples

### Goal with Sub-goals

```markdown
## japanese : Learn Japanese N4

- type: open
- status: in_progress
- priority: high
- created: 2026-01-05
- tags: [languages, personal]

### jp-01 : Master kana

- status: done
- tracking:
    mode: cumulative
- actual: 12 hours
- start: 2026-01-05
- end: 2026-01-20

### jp-02 : Complete Genki I

- depends_on: [jp-01]
- start: 2026-01-21

### Time Journal

| Date       | Task   | Value      | Notes     |
|------------|--------|------------|-----------|
| 2026-01-05 | jp-01  | 0.75 hours | Hiragana  |
```

In this example, `jp-02` inherits the `high` priority from the parent
`japanese`. Its status will be automatically derived from the
journal entries.

### Goal without Sub-goals (journal at leaf level)

```markdown
## running : Run 60 minutes without stopping

- type: bounded
- status: in_progress
- priority: medium
- created: 2026-01-10
- tracking:
    mode: performance
    target: 60 minutes

### Time Journal

| Date       | Value      | Notes              |
|------------|------------|--------------------|
| 2026-01-10 | 12 minutes | First run          |
| 2026-01-13 | 15 minutes | A bit better       |
```

Here the Task column is absent because the goal has no
children. The `running` identifier is automatically inferred.

### Mixed Journals (goal level and leaf level)

```markdown
## reading : Reading Program

- created: 2026-01-01

### reading-01 : Read Dune

- tracking:
    target: 412 pages

#### Time Journal

| Date       | Value    | Notes      |
|------------|----------|------------|
| 2026-01-10 | 35 pages | Chapter 1  |
| 2026-01-15 | 42 pages | Chapter 2  |

### reading-02 : Read Neuromancer

- tracking:
    target: 271 pages

### Time Journal

| Date       | Task       | Value    | Notes      |
|------------|------------|----------|------------|
| 2026-01-20 | reading-02 | 30 pages | Start      |
```

In this example:

- `reading-01` has its own journal (short format, without Task column)
- The journal at `##` level uses the full format for `reading-02`
- Both formats coexist in the same file

### 3-Level Hierarchy

```markdown
## website : Deploy my website

### website-02 : Develop frontend

- depends_on: [website-01]

#### website-02-01 : Home page

- status: done
- tracking:
    mode: cumulative
    target: 100%
- actual: 100%

#### website-02-02 : Projects page

- tracking:
    mode: cumulative
    target: 100%
```

In this example:

- `website-02` derives its progress from its children (`website-02-01` and `website-02-02`)
- `website` derives its progress from all its `###` sub-goals
- No status is declared — everything is derived automatically

### Sub-goal with Fixed Date

```markdown
### spanish-01 : Follow intermediate course

- start: 2026-02-01
- end: 2026-04-30!
```

No `tracking` or journal required. Progress
goes from 0% to 100% between February 1st and April 30th.

---

## Reference Values

### `status`

| Value         | Description       |
|---------------|-------------------|
| `not_started` | Not yet started   |
| `in_progress` | In progress       |
| `done`        | Completed         |
| `paused`      | On hold           |
| `cancelled`   | Cancelled         |

`cancelled` elements are excluded from their parent's progress
calculation.

### `priority`

| Value      | Rank | Description                       |
|------------|------|-----------------------------------|
| `optional` | 0    | Optional                          |
| `low`      | 1    | Low urgency                       |
| `medium`   | 2    | Normal priority (default)         |
| `high`     | 3    | Important                         |
| `capital`  | 4    | Critical, to be handled first     |

If not declared, priority is **inherited from parent**. Root
goals without priority receive `medium`.

### `type`

| Value     | Description                                             |
|-----------|---------------------------------------------------------|
| `bounded` | Goal with a defined end (default)                       |
| `open`    | Continuous goal, with no planned end                    |

Type can be defined at **any level**. An `open` element:

- Is excluded from its parent's progress calculation
- Does not display a progress bar in the overview
- Shows its sub-goals in predictions
- Displays "Open goal" instead of a prediction summary

---

## `tracking` Block

Tracking only applies to elements **without children** (tree
leaves).

```yaml
- tracking:
    mode: cumulative
    target: 382 pages
```

| Field  | Required | Description                   | Default      |
|--------|----------|-------------------------------|--------------|
| mode   | no       | `cumulative` or `performance` | `cumulative` |
| target | no       | number + unit                 | —            |

### Modes

| Mode          | Behavior                                              | Example                |
|---------------|-------------------------------------------------------|------------------------|
| `cumulative`  | Journal entries add up towards the target             | 200/382 pages read     |
| `performance` | Each entry is independent, **maximum** counts         | Record: 32/60 minutes  |
| `fixed`       | Automatic time-based progress (end date with `!`)     | Course: 16/100 days    |

The `fixed` mode is automatically assigned to elements whose
`end` date ends with `!`. It is not configured in the
`tracking` block.

### Units

Units are **free text**. Write whatever you want after
the number:

```
target: 382 pages
target: 30 hours
target: 60 minutes
target: 100%
target: 50 chapters
target: 12 modules
target: 200 km
```

### `actual` Field

Initial progress value. Same format: number + unit.

```yaml
- actual: 180 pages
- actual: 55%
- actual: 12 hours
```

If journal entries exist for this element, they
replace the `actual` value (sum for cumulative, max for
performance).

---

## SMART Block (optional)

Can be defined on any element, at any level.

```yaml
- smart:
    specific: "Precise description of the goal"
    measurable: "How to measure success"
    actionable: "How the goal can be achieved"
    relevant: "Why it's relevant"
    time_bound: "YYYY-MM-DD"
```

All fields are optional. The `time_bound` field serves as
the deadline for dashboard predictions. A time can
optionally be added:

```yaml
time_bound: "2026-04-15"
time_bound: "2026-04-15 14:30"
```

---

## Time Journal

The journal is a "Time Journal" heading that contains a
Markdown table of activity entries. It can be placed at
**any level** of the hierarchy.

### Placement Rules

| Context                              | Required format | Task column |
|--------------------------------------|-----------------|-------------|
| Under a **leaf** (no children)       | Short           | Absent (implicit id) |
| Under a **node with children**       | Full            | Required    |

**Identifier validation**: each entry must reference an
identifier **already defined** earlier in the file. Entries
whose identifier is unknown or defined later are silently
ignored.

### Full Format (with Task column)

Used under a node that has children. The Task column can
reference any descendant, regardless of depth.

```markdown
## g : My goal

### a : Task A

- tracking:
    target: 100 pages

### b : Task B

- tracking:
    target: 50 pages

### Time Journal

| Date       | Task | Value    | Notes      |
|------------|------|----------|------------|
| 2026-01-22 | a    | 12 pages | Chapter 1  |
| 2026-02-10 | b    | 8 pages  |            |
```

| Column | Format                                      |
|--------|---------------------------------------------|
| Date   | `YYYY-MM-DD`                                |
| Task   | id of an element defined before the journal |
| Value  | number + free text unit                     |
| Notes  | free text (optional)                        |

The journal can also be placed at an intermediate level. For
example, under a `###` that has its own `####` children:

```markdown
### parent : Main module

#### sub-a : Part A

- tracking:
    target: 40 pages

#### sub-b : Part B

- tracking:
    target: 60 pages

#### Time Journal

| Date       | Task  | Value    | Notes |
|------------|-------|----------|-------|
| 2026-01-10 | sub-a | 10 pages |       |
| 2026-01-15 | sub-b | 5 pages  |       |
```

### Short Format (without Task column)

Used under a leaf (element without children). The identifier
is automatically inferred from the parent.

```markdown
### task-01 : Read the book

- tracking:
    target: 382 pages

#### Time Journal

| Date       | Value    | Notes      |
|------------|----------|------------|
| 2026-01-22 | 35 pages | Chapter 1  |
| 2026-01-25 | 42 pages | Chapter 2  |
```

| Column | Format                        |
|--------|-------------------------------|
| Date   | `YYYY-MM-DD`                  |
| Value  | number + free text unit       |
| Notes  | free text (optional)          |

The minimal two-column format (without Notes) is also accepted:

```markdown
#### Time Journal

| Date       | Value      |
|------------|------------|
| 2026-01-10 | 12 minutes |
| 2026-01-13 | 15 minutes |
```

### Automatic Format Detection

The parser detects the format (full or short) in two ways:

1. **By the header line**: if columns include "Tâche"
   or "Task", it's the full format; otherwise, it's the short
   format.
2. **By column count**: in the absence of a header, a
   2-3 column table under a leaf is interpreted as
   short format.

### Format Coexistence

Multiple journals can coexist in the same goal, at
different levels. Each leaf can have its own short
journal, and a full journal can exist at a higher level:

```markdown
## reading : Reading Program

### reading-01 : Read Dune

- tracking:
    target: 412 pages

#### Time Journal

| Date       | Value    |
|------------|----------|
| 2026-01-10 | 35 pages |

### reading-02 : Read Neuromancer

- tracking:
    target: 271 pages

### Time Journal

| Date       | Task      | Value    | Notes |
|------------|-----------|----------|-------|
| 2026-01-20 | reading-02| 30 pages |       |
```

---

## Dependencies

Dependencies work between elements at the **same level**:

```yaml
- depends_on: [jp-01, jp-02]
```

Cross-level dependencies are not supported.

---

## Predictions

The dashboard calculates predictions from **2 entries minimum**
in the journal.

| Mode        | Velocity calculation                                            |
|-------------|-----------------------------------------------------------------|
| cumulative  | total accumulated ÷ days between first and last entry           |
| performance | slope of linear regression line on entries                      |

For elements with children, the predicted completion date is
the latest among the predictions of its active children.

If some children do not yet have a prediction (not enough
data), the parent's prediction is marked as **partial** —
it represents the known minimum but is not definitive.

`cancelled` and `open` elements are excluded from all calculations.

---

## Dashboard

### Overview

Displays global statistics and each goal with its progress
bar, its sub-goals and its mini-timeline. Open goals
do not display a progress bar.

### Gantt

Gantt chart showing the planned duration of each goal and
sub-goal. Cancelled elements are excluded.

### Predictions

Detailed cards with the timeline of each sub-goal and a
summary (on track / behind schedule). Fixed dates display
"End:" instead of "Predicted:". Open goals display
their sub-goals but show "Open goal" in the summary.

### Sorting

The selector at the top right allows sorting goals:

- **File order** (default)
- **By name** (alphabetical)
- **By priority and name** (descending priority, then alphabetical)

Sorting applies to all three views simultaneously.

### Filters

The filter bar below the title allows filtering by priority
and by category (tags). Buttons are toggles: clicking
enables/disables the filter. No active filter = everything visible.
