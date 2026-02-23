"""Tests for :mod:`app.main` — FastAPI endpoints."""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import _node_to_dict, app
from app.analytics import NodeProgress, analyze_goal
from app.parser import Node, SmartCriteria, TimeEntry, TrackingConfig


@pytest.fixture()
def client() -> TestClient:
    """A test client bound to the FastAPI app."""
    return TestClient(app)


# ── _node_to_dict ────────────────────────────────────────────────────────


class TestNodeToDict:
    def test_basic_fields(self) -> None:
        np = NodeProgress(
            node_id="x",
            title="X",
            status="in_progress",
            priority="high",
            priority_rank=3,
            has_children=False,
            tracking_mode="cumulative",
            unit_label="pages",
            target=100.0,
            current_value=50.0,
            percent_complete=50.0,
            start=date(2026, 1, 1),
            end=date(2026, 6, 1),
            predicted_end=date(2026, 4, 1),
            prediction_partial=False,
            predicted_remaining=50.0,
            velocity_per_day=2.5,
            depends_on=["y"],
            has_smart=True,
            smart_data={
                "specific": "S",
                "measurable": "",
                "actionable": "",
                "relevant": "",
                "time_bound": "",
            },
        )
        d: dict[str, Any] = _node_to_dict(np)
        assert d["id"] == "x"
        assert d["status"] == "in_progress"
        assert d["start"] == "2026-01-01"
        assert d["predicted_end"] == "2026-04-01"
        assert d["children"] == []

    def test_optional_fields_absent(self) -> None:
        np = NodeProgress(
            node_id="x",
            title="X",
            status="not_started",
            priority="medium",
            priority_rank=2,
            has_children=False,
            tracking_mode="cumulative",
            unit_label="",
            target=None,
            current_value=0.0,
            percent_complete=0.0,
            start=None,
            end=None,
            predicted_end=None,
            prediction_partial=False,
            predicted_remaining=None,
            velocity_per_day=None,
            depends_on=[],
            has_smart=False,
        )
        d: dict[str, Any] = _node_to_dict(np)
        assert "tags" not in d
        assert "deadline" not in d
        assert "on_track" not in d

    def test_top_level_fields(self) -> None:
        np = NodeProgress(
            node_id="x",
            title="X",
            status="in_progress",
            priority="medium",
            priority_rank=2,
            has_children=False,
            tracking_mode="cumulative",
            unit_label="",
            target=None,
            current_value=0.0,
            percent_complete=0.0,
            start=None,
            end=None,
            predicted_end=None,
            prediction_partial=False,
            predicted_remaining=None,
            velocity_per_day=None,
            depends_on=[],
            has_smart=False,
            tags=["pro"],
            on_track=True,
        )
        from datetime import datetime

        np.deadline = datetime(2026, 6, 1)
        d: dict[str, Any] = _node_to_dict(np)
        assert d["tags"] == ["pro"]
        assert d["on_track"] is True
        assert "deadline" in d

    def test_children_serialised(self) -> None:
        child = NodeProgress(
            node_id="c",
            title="C",
            status="done",
            priority="medium",
            priority_rank=2,
            has_children=False,
            tracking_mode="cumulative",
            unit_label="",
            target=10.0,
            current_value=10.0,
            percent_complete=100.0,
            start=None,
            end=None,
            predicted_end=None,
            prediction_partial=False,
            predicted_remaining=None,
            velocity_per_day=None,
            depends_on=[],
            has_smart=False,
        )
        parent = NodeProgress(
            node_id="p",
            title="P",
            status="in_progress",
            priority="medium",
            priority_rank=2,
            has_children=True,
            tracking_mode="cumulative",
            unit_label="",
            target=None,
            current_value=50.0,
            percent_complete=50.0,
            start=None,
            end=None,
            predicted_end=None,
            prediction_partial=False,
            predicted_remaining=None,
            velocity_per_day=None,
            depends_on=[],
            has_smart=False,
            children=[child],
        )
        d: dict[str, Any] = _node_to_dict(parent)
        assert len(d["children"]) == 1
        assert d["children"][0]["id"] == "c"


# ── API endpoints ────────────────────────────────────────────────────────


class TestAPIEndpoints:
    def _mock_goals(self) -> tuple[list[Node], list]:
        """Return mock goals with empty errors list."""
        return (
            [
                Node(
                    node_id="a",
                    title="Alpha",
                    status="in_progress",
                    priority="high",
                    tags=["test"],
                    tracking=TrackingConfig(target=100.0, unit="pages"),
                ),
            ],
            [],  # No errors
        )

    def test_get_goals(self, client: TestClient) -> None:
        with patch("app.main._load_goals", return_value=self._mock_goals()):
            resp = client.get("/api/goals")
        assert resp.status_code == 200
        data: dict[str, Any] = resp.json()
        assert "goals" in data
        assert "errors" in data
        assert "as_of" in data
        assert len(data["goals"]) == 1
        assert data["goals"][0]["id"] == "a"
        assert len(data["errors"]) == 0

    def test_get_goal_found(self, client: TestClient) -> None:
        with patch("app.main._load_goals", return_value=self._mock_goals()):
            resp = client.get("/api/goals/a")
        assert resp.status_code == 200
        data: dict[str, Any] = resp.json()
        assert data["id"] == "a"
        assert "errors" in data

    def test_get_goal_not_found(self, client: TestClient) -> None:
        with patch("app.main._load_goals", return_value=self._mock_goals()):
            resp = client.get("/api/goals/nonexistent")
        assert resp.status_code == 200
        data: dict[str, Any] = resp.json()
        assert data["error"] == "Goal not found"
        assert "errors" in data

    def test_get_gantt(self, client: TestClient) -> None:
        with patch("app.main._load_goals", return_value=self._mock_goals()):
            resp = client.get("/api/gantt")
        assert resp.status_code == 200
        data: dict[str, Any] = resp.json()
        assert "tasks" in data
        assert "errors" in data
        assert len(data["tasks"]) >= 1

    def test_serve_dashboard(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "SMART Goals Tracker" in resp.text
