"""
FastAPI application for the SMART Goals Dashboard.

Serves three API endpoints (``/api/goals``, ``/api/goals/{goal_id}``,
``/api/gantt``) and a single-page HTML dashboard at ``/``.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Union

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .analytics import NodeProgress, analyze_goal
from .parser import Node, ParseError, ParseResult, parse_goals_file

# ── Preferences ──────────────────────────────────────────────────────────

try:
    import preferences  # type: ignore[import-untyped]

    GOALS_FILE: Path = Path(preferences.GOALS_FILE)
except ImportError:
    GOALS_FILE = Path("./sample_vault/objectifs.md")
"""Path to the Markdown goals file.

Resolved from the user-supplied ``preferences`` module when available,
otherwise falls back to the sample vault.
"""

# ── Application ──────────────────────────────────────────────────────────

app: FastAPI = FastAPI(title="SMART Goals Tracker", version="0.4.0")
"""Main FastAPI application instance."""

STATIC_DIR: Path = Path(__file__).parent.parent.parent / "static"
"""Absolute path to the ``static/`` directory served at ``/static``."""

if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )


# ── Helpers ──────────────────────────────────────────────────────────────


def _load_goals() -> tuple[list[Node], list[ParseError]]:
    """Parse the goals file and return top-level nodes with any errors.

    :returns: Tuple of (nodes, errors). Nodes may be empty on fatal errors.
    """
    result: ParseResult = parse_goals_file(GOALS_FILE)
    return result.goals, result.errors


def _node_to_dict(node: NodeProgress) -> dict[str, Any]:
    """Serialise a :class:`~app.analytics.NodeProgress` tree to a JSON-ready dict.

    Children are serialised recursively.  Top-level-only fields
    (``tags``, ``deadline``, ``on_track``) are included only when
    present.

    :param node: The analysed node to convert.
    :returns: A nested dictionary suitable for JSON serialisation.
    """
    result: dict[str, Any] = {
        "id": node.node_id,
        "title": node.title,
        "status": node.status,
        "priority": node.priority,
        "priority_rank": node.priority_rank,
        "has_children": node.has_children,
        "type": node.node_type,
        "tracking_mode": node.tracking_mode,
        "unit_label": node.unit_label,
        "target": node.target,
        "current_value": node.current_value,
        "percent_complete": node.percent_complete,
        "start": node.start.isoformat() if node.start else None,
        "end": node.end.isoformat() if node.end else None,
        "predicted_end": (
            node.predicted_end.isoformat() if node.predicted_end else None
        ),
        "prediction_partial": node.prediction_partial,
        "predicted_remaining": node.predicted_remaining,
        "velocity_per_day": node.velocity_per_day,
        "depends_on": node.depends_on,
        "has_smart": node.has_smart,
        "smart": node.smart_data,
        "progress_source": node.progress_source,
        "children": [_node_to_dict(c) for c in node.children],
    }
    if node.tags is not None and len(node.tags) > 0:
        result["tags"] = node.tags
    if node.deadline is not None:
        result["deadline"] = node.deadline.isoformat()
    if node.on_track is not None:
        result["on_track"] = node.on_track
    return result


# ── API routes ───────────────────────────────────────────────────────────


@app.get("/api/goals")
async def get_goals() -> dict[str, Any]:
    """Return all goals with their full analysis tree.

    :returns: ``{"goals": [...], "errors": [...], "as_of": "YYYY-MM-DD"}``.
    """
    goals: list[Node]
    errors: list[ParseError]
    goals, errors = _load_goals()
    today: date = date.today()
    return {
        "goals": [_node_to_dict(analyze_goal(g, today)) for g in goals],
        "errors": [e.to_dict() for e in errors],
        "as_of": today.isoformat(),
    }


@app.get("/api/goals/{goal_id}")
async def get_goal(goal_id: str) -> dict[str, Any]:
    """Return a single goal by its identifier.

    :param goal_id: The :pyattr:`~app.parser.Node.node_id` to look up.
    :returns: Serialised goal dict, or ``{"error": "Goal not found"}``.
    """
    goals: list[Node]
    errors: list[ParseError]
    goals, errors = _load_goals()
    today: date = date.today()
    for goal in goals:
        if goal.node_id == goal_id:
            result = _node_to_dict(analyze_goal(goal, today))
            result["errors"] = [e.to_dict() for e in errors]
            return result
    return {"error": "Goal not found", "errors": [e.to_dict() for e in errors]}


# ── Gantt helpers ────────────────────────────────────────────────────────


def _flatten_for_gantt(
    node: NodeProgress,
    parent_id: Optional[str],
    goal_start: date,
    goal_end: Union[date, datetime],
) -> list[dict[str, Any]]:
    """Recursively flatten a node tree into a list of Gantt task dicts.

    Each task carries the fields expected by the front-end Gantt view
    (``id``, ``name``, ``start``, ``end``, ``progress``, etc.).

    :param node: Current node to flatten.
    :param parent_id: Identifier of the parent task (``None`` for roots).
    :param goal_start: Fallback start when the node has none.
    :param goal_end: Fallback end when neither an explicit end nor a
        prediction is available.
    :returns: Flat list of task dictionaries.
    """
    tasks: list[dict[str, Any]] = []
    node_start: date = node.start or goal_start
    node_end: date
    if node.status in ("done", "cancelled") and node.end:
        node_end = node.end
    elif node.predicted_end:
        node_end = node.predicted_end
    else:
        node_end = goal_end if isinstance(goal_end, date) else goal_end.date()

    task: dict[str, Any] = {
        "id": node.node_id,
        "name": node.title,
        "start": node_start.isoformat(),
        "end": node_end.isoformat(),
        "progress": node.percent_complete,
        "type": "goal" if parent_id is None else "sub",
        "parent": parent_id,
        "priority": node.priority,
        "status": node.status,
        "has_children": node.has_children,
        "dependencies": node.depends_on,
    }
    tasks.append(task)

    for child in node.children:
        tasks.extend(
            _flatten_for_gantt(child, node.node_id, node_start, node_end),
        )

    return tasks


@app.get("/api/gantt")
async def get_gantt_data() -> dict[str, Any]:
    """Return a flat list of Gantt tasks for every goal.

    :returns: ``{"tasks": [...], "errors": [...], "as_of": "YYYY-MM-DD"}``.
    """
    goals: list[Node]
    errors: list[ParseError]
    goals, errors = _load_goals()
    today: date = date.today()
    tasks: list[dict[str, Any]] = []

    for goal in goals:
        progress: NodeProgress = analyze_goal(goal, today)
        goal_start: date = goal.created or today
        goal_end: Union[date, datetime] = (
            progress.deadline or progress.predicted_end or (today + timedelta(days=90))
        )
        tasks.extend(
            _flatten_for_gantt(progress, None, goal_start, goal_end),
        )

    return {
        "tasks": tasks,
        "errors": [e.to_dict() for e in errors],
        "as_of": today.isoformat(),
    }


# ── Dashboard ────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard() -> HTMLResponse:
    """Serve the single-page HTML dashboard.

    :returns: The contents of ``static/index.html``, or a fallback
        message when the file is missing.
    """
    index_path: Path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(
        content="<h1>SMART Goals Tracker</h1><p>Static files not found.</p>",
    )
