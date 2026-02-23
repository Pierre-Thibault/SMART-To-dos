# SMART Goals Tracker

Goal tracking system with web dashboard, Gantt chart and predictions.
Everything in a single Markdown file, editable in any text editor.

## Concept

The system relies on a unified recursive model. Each element (goal,
sub-goal, sub-task) follows the same logic:

- **With children** → progress calculated from its children
- **Without children** → progress tracked via its own tracking and journal

Depth is unlimited, but in practice 1 to 3 levels are sufficient.

## Features

- **Single file** `objectifs.md`
- **Recursive tree**: unlimited depth, same logic at each level
- **Optional SMART** on any element
- **Two tracking modes**: cumulative (sum) and performance (maximum)
- **Fixed dates**: automatic time-based progress (`end: YYYY-MM-DD!`)
- **Free-form units**: pages, hours, minutes, %, km, chapters...
- **Priorities**: optional, low, medium, high, capital (inherited from parent)
- **Multiple dependencies** between elements at the same level
- **Predictions from 2 entries** in the journal
- **Weighted progress** by target for homogeneous units
- **Auto-derived status**: parents from children, leaves from entries
- **Open goals** (`type: open`) excluded from parent calculation
- **Sorting**: file order, by name, by priority and name
- **Filters**: by priority and by category (tags)
- **Light/dark theme** automatic based on system preferences
- **Web dashboard**: Overview, Gantt, Predictions

## Installation

### With Nix

```bash
nix develop
```

### Without Nix

```bash
pip install -r requirements.txt --break-system-packages
```

## Configuration

Copy the preferences file and customize it:

```bash
cp src/preferences_template.py src/preferences.py
```

Edit `src/preferences.py`:

```python
GOALS_FILE = "/path/to/my/objectifs.md"
```

This file is ignored by git.

## Usage

```bash
PYTHONPATH=src uvicorn app.main:app --reload
```

With Nix, `PYTHONPATH` is configured automatically:

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000.

Without `preferences.py`, the application uses `./sample_vault/objectifs.md`.

## Tests

Run the test suite:

```bash
PYTHONPATH=src python -m pytest tests/ -v
```

With coverage:

```bash
PYTHONPATH=src python -m pytest tests/ --cov=app --cov-report=term-missing
```

Tests cover:

- **parser.py**: value/unit extraction, dates, YAML metadata,
  time journal, section splitting, tree construction,
  priority inheritance, full integration.
- **analytics.py**: current value, velocity, prediction, leaf percentage,
  subtree weight, units, weighted/predicted progress,
  status derivation, open goals, fixed dates, on-track.
- **main.py**: JSON serialization, API endpoints (`/api/goals`,
  `/api/goals/{id}`, `/api/gantt`), HTML dashboard.

## Documentation

See [REFERENCE.md](REFERENCE.md) for the complete file structure
and all possible values.

## Architecture

```
smart-goals/
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── parser.py              # Parses the Markdown file (recursive)
│   │   ├── analytics.py           # Progress, velocity, predictions
│   │   └── main.py                # FastAPI API
│   └── preferences_template.py    # Configuration template
├── tests/
│   ├── conftest.py                # Shared fixtures
│   ├── test_parser.py             # Parser tests
│   ├── test_analytics.py          # Analytics tests
│   ├── test_main.py               # API tests
│   └── test_edge_cases.py         # Edge cases
├── static/
│   ├── index.html                 # HTML structure
│   ├── theme-light.css            # Light theme
│   ├── theme-dark.css             # Dark theme
│   └── app.js                     # Dashboard logic
├── sample_vault/
│   └── objectifs.md               # Example with 3 goals
├── .gitignore
├── flake.nix
├── requirements.txt
├── REFERENCE.md
└── README.md
```

## License

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
