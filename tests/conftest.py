"""Shared fixtures for the test suite."""

from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.parser import Node, SmartCriteria, TimeEntry, TrackingConfig


@pytest.fixture()
def tmp_md(tmp_path: Path):
    """Return a helper that writes Markdown content to a temp file."""

    def _write(content: str) -> Path:
        p: Path = tmp_path / "goals.md"
        p.write_text(textwrap.dedent(content), encoding="utf-8")
        return p

    return _write


@pytest.fixture()
def leaf_node() -> Node:
    """A minimal leaf node with cumulative tracking."""
    return Node(
        node_id="task-01",
        title="Read the book",
        tracking=TrackingConfig(mode="cumulative", target=100.0, unit="pages"),
    )


@pytest.fixture()
def done_leaf() -> Node:
    """A leaf node marked as done."""
    return Node(
        node_id="task-02",
        title="Finished task",
        status="done",
        tracking=TrackingConfig(mode="cumulative", target=50.0, unit="pages"),
    )


@pytest.fixture()
def parent_node() -> Node:
    """A parent node with two leaf children."""
    return Node(
        node_id="goal-01",
        title="Big goal",
        children=[
            Node(
                node_id="sub-01",
                title="Sub one",
                status="done",
                tracking=TrackingConfig(mode="cumulative", target=40.0, unit="pages"),
            ),
            Node(
                node_id="sub-02",
                title="Sub two",
                tracking=TrackingConfig(mode="cumulative", target=60.0, unit="pages"),
            ),
        ],
    )


@pytest.fixture()
def sample_entries() -> list[TimeEntry]:
    """Journal entries spanning several days."""
    return [
        TimeEntry(date=date(2026, 1, 10), node_id="task-01", quantity=20.0),
        TimeEntry(date=date(2026, 1, 15), node_id="task-01", quantity=30.0),
        TimeEntry(date=date(2026, 1, 20), node_id="task-01", quantity=10.0),
    ]
