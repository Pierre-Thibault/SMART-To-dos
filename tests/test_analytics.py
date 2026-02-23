"""Tests for :mod:`app.analytics`."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.analytics import (
    PRIORITY_ORDER,
    NodeProgress,
    _current_value,
    _get_entries,
    _leaf_percent,
    _leaf_units,
    _predict,
    _prediction_based_percent,
    _smart_to_dict,
    _subtree_weight,
    _velocity,
    analyze_goal,
    analyze_node,
)
from app.parser import Node, SmartCriteria, TimeEntry, TrackingConfig

# ── _smart_to_dict ───────────────────────────────────────────────────────


class TestSmartToDict:
    def test_none(self) -> None:
        assert _smart_to_dict(None) is None

    def test_filled(self) -> None:
        sc = SmartCriteria(specific="S", measurable="M", time_bound="2026-01-01")
        d = _smart_to_dict(sc)
        assert d is not None
        assert d["specific"] == "S"
        assert d["time_bound"] == "2026-01-01"
        assert d["actionable"] == ""


# ── _get_entries ─────────────────────────────────────────────────────────


class TestGetEntries:
    def test_filters(self, sample_entries: list[TimeEntry]) -> None:
        result = _get_entries(sample_entries, "task-01")
        assert len(result) == 3

    def test_no_match(self, sample_entries: list[TimeEntry]) -> None:
        result = _get_entries(sample_entries, "other")
        assert len(result) == 0


# ── _current_value ───────────────────────────────────────────────────────


class TestCurrentValue:
    def test_cumulative_with_entries(self) -> None:
        tc = TrackingConfig(mode="cumulative")
        entries = [
            TimeEntry(date=date(2026, 1, 1), node_id="x", quantity=10.0),
            TimeEntry(date=date(2026, 1, 2), node_id="x", quantity=20.0),
        ]
        assert _current_value(tc, entries, 0.0) == 30.0

    def test_cumulative_no_entries(self) -> None:
        tc = TrackingConfig(mode="cumulative")
        assert _current_value(tc, [], 5.0) == 5.0

    def test_performance_with_entries(self) -> None:
        tc = TrackingConfig(mode="performance")
        entries = [
            TimeEntry(date=date(2026, 1, 1), node_id="x", quantity=10.0),
            TimeEntry(date=date(2026, 1, 2), node_id="x", quantity=25.0),
            TimeEntry(date=date(2026, 1, 3), node_id="x", quantity=15.0),
        ]
        assert _current_value(tc, entries, 0.0) == 25.0

    def test_performance_no_entries(self) -> None:
        tc = TrackingConfig(mode="performance")
        assert _current_value(tc, [], 12.0) == 12.0


# ── _velocity ────────────────────────────────────────────────────────────


class TestVelocity:
    def test_insufficient_entries(self) -> None:
        tc = TrackingConfig(mode="cumulative")
        entries = [TimeEntry(date=date(2026, 1, 1), node_id="x", quantity=10.0)]
        assert _velocity(tc, entries) is None

    def test_cumulative(self) -> None:
        tc = TrackingConfig(mode="cumulative")
        entries = [
            TimeEntry(date=date(2026, 1, 1), node_id="x", quantity=10.0),
            TimeEntry(date=date(2026, 1, 11), node_id="x", quantity=20.0),
        ]
        vel = _velocity(tc, entries)
        assert vel is not None
        assert vel == pytest.approx(3.0)  # 30 total / 10 days

    def test_same_day(self) -> None:
        tc = TrackingConfig(mode="cumulative")
        entries = [
            TimeEntry(date=date(2026, 1, 1), node_id="x", quantity=10.0),
            TimeEntry(date=date(2026, 1, 1), node_id="x", quantity=20.0),
        ]
        assert _velocity(tc, entries) is None

    def test_performance_regression(self) -> None:
        tc = TrackingConfig(mode="performance")
        entries = [
            TimeEntry(date=date(2026, 1, 1), node_id="x", quantity=10.0),
            TimeEntry(date=date(2026, 1, 11), node_id="x", quantity=20.0),
        ]
        vel = _velocity(tc, entries)
        assert vel is not None
        assert vel > 0


# ── _predict ─────────────────────────────────────────────────────────────


class TestPredict:
    def test_no_target(self) -> None:
        tc = TrackingConfig(target=None)
        assert _predict(tc, 0.0, 5.0, date(2026, 1, 1)) is None

    def test_already_complete(self) -> None:
        tc = TrackingConfig(target=50.0)
        assert _predict(tc, 50.0, 5.0, date(2026, 1, 1)) == date(2026, 1, 1)

    def test_no_velocity(self) -> None:
        tc = TrackingConfig(target=50.0)
        assert _predict(tc, 10.0, None, date(2026, 1, 1)) is None

    def test_zero_velocity(self) -> None:
        tc = TrackingConfig(target=50.0)
        assert _predict(tc, 10.0, 0.0, date(2026, 1, 1)) is None

    def test_normal(self) -> None:
        tc = TrackingConfig(target=100.0)
        # 60 remaining / 10 per day = 6 days + 1
        pred = _predict(tc, 40.0, 10.0, date(2026, 1, 1))
        assert pred == date(2026, 1, 8)


# ── _leaf_percent ────────────────────────────────────────────────────────


class TestLeafPercent:
    def test_done(self) -> None:
        tc = TrackingConfig(target=100.0)
        assert _leaf_percent(tc, 50.0, "done") == 100.0

    def test_not_started_zero(self) -> None:
        tc = TrackingConfig(target=100.0)
        assert _leaf_percent(tc, 0.0, "not_started") == 0.0

    def test_cancelled_zero(self) -> None:
        tc = TrackingConfig(target=100.0)
        assert _leaf_percent(tc, 0.0, "cancelled") == 0.0

    def test_cancelled_with_progress(self) -> None:
        tc = TrackingConfig(target=100.0)
        pct = _leaf_percent(tc, 80.0, "cancelled")
        assert pct <= 99.0

    def test_in_progress_with_target(self) -> None:
        tc = TrackingConfig(target=200.0)
        assert _leaf_percent(tc, 100.0, "in_progress") == 50.0

    def test_in_progress_no_target(self) -> None:
        tc = TrackingConfig(target=None)
        assert _leaf_percent(tc, 0.0, "in_progress") == 50.0

    def test_over_target_capped(self) -> None:
        tc = TrackingConfig(target=50.0)
        assert _leaf_percent(tc, 60.0, "in_progress") == 100.0


# ── _subtree_weight ──────────────────────────────────────────────────────


class TestSubtreeWeight:
    def test_leaf_with_target(self) -> None:
        np = NodeProgress(
            node_id="x",
            title="X",
            status="in_progress",
            priority="medium",
            priority_rank=2,
            has_children=False,
            tracking_mode="cumulative",
            unit_label="pages",
            target=100.0,
            current_value=50.0,
            percent_complete=50.0,
            start=None,
            end=None,
            predicted_end=None,
            prediction_partial=False,
            predicted_remaining=50.0,
            velocity_per_day=5.0,
            depends_on=[],
            has_smart=False,
        )
        assert _subtree_weight(np) == 100.0

    def test_leaf_fixed(self) -> None:
        np = NodeProgress(
            node_id="x",
            title="X",
            status="in_progress",
            priority="medium",
            priority_rank=2,
            has_children=False,
            tracking_mode="fixed",
            unit_label="",
            target=None,
            current_value=50.0,
            percent_complete=50.0,
            start=date(2026, 1, 1),
            end=date(2026, 4, 1),
            predicted_end=date(2026, 4, 1),
            prediction_partial=False,
            predicted_remaining=None,
            velocity_per_day=None,
            depends_on=[],
            has_smart=False,
        )
        assert _subtree_weight(np) == 90.0  # 90 days


# ── _leaf_units ──────────────────────────────────────────────────────────


class TestLeafUnits:
    def test_regular_leaf(self) -> None:
        np = NodeProgress(
            node_id="x",
            title="X",
            status="in_progress",
            priority="medium",
            priority_rank=2,
            has_children=False,
            tracking_mode="cumulative",
            unit_label="pages",
            target=100.0,
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
        assert _leaf_units(np) == {"pages"}

    def test_fixed_leaf(self) -> None:
        np = NodeProgress(
            node_id="x",
            title="X",
            status="in_progress",
            priority="medium",
            priority_rank=2,
            has_children=False,
            tracking_mode="fixed",
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
        assert _leaf_units(np) == {"__fixed__"}


# ── _prediction_based_percent ────────────────────────────────────────────


class TestPredictionBasedPercent:
    def test_none_inputs(self) -> None:
        assert (
            _prediction_based_percent(None, date(2026, 1, 1), date(2026, 2, 1)) is None
        )
        assert (
            _prediction_based_percent(date(2026, 3, 1), None, date(2026, 2, 1)) is None
        )

    def test_normal(self) -> None:
        pct = _prediction_based_percent(
            date(2026, 3, 1),
            date(2026, 1, 1),
            date(2026, 2, 1),
        )
        assert pct is not None
        assert 50.0 < pct < 55.0  # ~31/59 days

    def test_zero_duration(self) -> None:
        pct = _prediction_based_percent(
            date(2026, 1, 1),
            date(2026, 1, 1),
            date(2026, 1, 1),
        )
        assert pct == 100.0


# ── analyze_node ─────────────────────────────────────────────────────────


class TestAnalyzeNode:
    def test_leaf_cumulative(
        self, leaf_node: Node, sample_entries: list[TimeEntry]
    ) -> None:
        today = date(2026, 1, 25)
        result = analyze_node(leaf_node, sample_entries, today)
        assert result.current_value == 60.0  # 20 + 30 + 10
        assert result.percent_complete == 60.0  # 60/100
        assert result.status == "in_progress"  # derived from entries

    def test_leaf_done_overrides_current(self, done_leaf: Node) -> None:
        today = date(2026, 1, 25)
        result = analyze_node(done_leaf, [], today)
        assert result.current_value == 50.0  # target
        assert result.percent_complete == 100.0

    def test_parent_weighted(self, parent_node: Node) -> None:
        today = date(2026, 1, 25)
        result = analyze_node(parent_node, [], today)
        assert result.has_children is True
        # sub-01: done (100%), weight 40
        # sub-02: not_started (0%), weight 60
        # weighted: (40*100 + 60*0)/100 = 40%
        assert result.percent_complete == pytest.approx(40.0, abs=0.5)
        assert result.progress_source == "weighted"

    def test_leaf_fixed_end(self) -> None:
        node = Node(
            node_id="f",
            title="Fixed",
            start=date(2026, 1, 1),
            end=date(2026, 3, 1),
            fixed_end=True,
        )
        today = date(2026, 2, 1)
        result = analyze_node(node, [], today)
        assert result.tracking_mode == "fixed"
        assert result.status == "in_progress"
        assert 50.0 < result.percent_complete < 55.0

    def test_leaf_fixed_end_past(self) -> None:
        node = Node(
            node_id="f",
            title="Fixed",
            start=date(2026, 1, 1),
            end=date(2026, 2, 1),
            fixed_end=True,
        )
        result = analyze_node(node, [], date(2026, 3, 1))
        assert result.status == "done"
        assert result.percent_complete == 100.0

    def test_leaf_fixed_end_before_start(self) -> None:
        node = Node(
            node_id="f",
            title="Fixed",
            start=date(2026, 3, 1),
            end=date(2026, 4, 1),
            fixed_end=True,
        )
        result = analyze_node(node, [], date(2026, 2, 1))
        assert result.percent_complete == 0.0

    def test_cancelled_children_excluded(self) -> None:
        parent = Node(
            node_id="p",
            title="P",
            children=[
                Node(
                    node_id="a",
                    title="A",
                    status="done",
                    tracking=TrackingConfig(target=50.0, unit="pages"),
                ),
                Node(
                    node_id="b",
                    title="B",
                    status="cancelled",
                    tracking=TrackingConfig(target=50.0, unit="pages"),
                ),
            ],
        )
        result = analyze_node(parent, [], date(2026, 1, 1))
        assert result.percent_complete == 100.0
        assert result.status == "done"

    def test_open_children_excluded(self) -> None:
        parent = Node(
            node_id="p",
            title="P",
            children=[
                Node(
                    node_id="a",
                    title="A",
                    status="done",
                    tracking=TrackingConfig(target=50.0, unit="pages"),
                ),
                Node(
                    node_id="o",
                    title="Open",
                    node_type="open",
                    tracking=TrackingConfig(target=100.0, unit="pages"),
                ),
            ],
        )
        result = analyze_node(parent, [], date(2026, 1, 1))
        assert result.percent_complete == 100.0  # open excluded

    def test_status_derivation_all_done(self) -> None:
        parent = Node(
            node_id="p",
            title="P",
            children=[
                Node(
                    node_id="a",
                    title="A",
                    status="done",
                    tracking=TrackingConfig(target=10.0),
                ),
                Node(
                    node_id="b",
                    title="B",
                    status="done",
                    tracking=TrackingConfig(target=10.0),
                ),
            ],
        )
        result = analyze_node(parent, [], date(2026, 1, 1))
        assert result.status == "done"

    def test_status_derivation_mixed(self) -> None:
        parent = Node(
            node_id="p",
            title="P",
            children=[
                Node(
                    node_id="a",
                    title="A",
                    status="done",
                    tracking=TrackingConfig(target=10.0),
                ),
                Node(
                    node_id="b",
                    title="B",
                    status="not_started",
                    tracking=TrackingConfig(target=10.0),
                ),
            ],
        )
        result = analyze_node(parent, [], date(2026, 1, 1))
        assert result.status == "in_progress"

    def test_status_derivation_all_cancelled(self) -> None:
        parent = Node(
            node_id="p",
            title="P",
            children=[
                Node(node_id="a", title="A", status="cancelled"),
                Node(node_id="b", title="B", status="cancelled"),
            ],
        )
        result = analyze_node(parent, [], date(2026, 1, 1))
        assert result.status == "cancelled"

    def test_status_derivation_paused(self) -> None:
        parent = Node(
            node_id="p",
            title="P",
            children=[
                Node(node_id="a", title="A", status="paused"),
                Node(node_id="b", title="B", status="not_started"),
            ],
        )
        result = analyze_node(parent, [], date(2026, 1, 1))
        assert result.status == "paused"

    def test_leaf_derives_in_progress_from_entries(self) -> None:
        node = Node(
            node_id="x",
            title="X",
            tracking=TrackingConfig(target=100.0, unit="pages"),
        )
        entries = [
            TimeEntry(date=date(2026, 1, 1), node_id="x", quantity=10.0),
        ]
        result = analyze_node(node, entries, date(2026, 1, 5))
        assert result.status == "in_progress"

    def test_leaf_derives_done_from_entries(self) -> None:
        node = Node(
            node_id="x",
            title="X",
            tracking=TrackingConfig(target=50.0, unit="pages"),
        )
        entries = [
            TimeEntry(date=date(2026, 1, 1), node_id="x", quantity=50.0),
        ]
        result = analyze_node(node, entries, date(2026, 1, 5))
        assert result.status == "done"

    def test_insufficient_progress_source(self) -> None:
        """Mixed units, no prediction → insufficient."""
        parent = Node(
            node_id="p",
            title="P",
            children=[
                Node(
                    node_id="a",
                    title="A",
                    tracking=TrackingConfig(target=10.0, unit="pages"),
                ),
                Node(
                    node_id="b",
                    title="B",
                    tracking=TrackingConfig(target=60.0, unit="jours"),
                ),
            ],
        )
        result = analyze_node(parent, [], date(2026, 2, 1))
        # pages vs jours → mixed; no entries → no prediction → insufficient
        assert result.progress_source == "insufficient"


# ── analyze_goal ─────────────────────────────────────────────────────────


class TestAnalyzeGoal:
    def test_deadline_from_smart(self) -> None:
        goal = Node(
            node_id="g",
            title="G",
            smart=SmartCriteria(time_bound="2026-06-01"),
            tracking=TrackingConfig(target=100.0, unit="pages"),
        )
        result = analyze_goal(goal, date(2026, 1, 1))
        assert result.deadline == datetime(2026, 6, 1)

    def test_deadline_with_time(self) -> None:
        goal = Node(
            node_id="g",
            title="G",
            smart=SmartCriteria(time_bound="2026-06-01 14:30"),
            tracking=TrackingConfig(target=100.0, unit="pages"),
        )
        result = analyze_goal(goal, date(2026, 1, 1))
        assert result.deadline == datetime(2026, 6, 1, 14, 30)

    def test_on_track_true(self) -> None:
        goal = Node(
            node_id="g",
            title="G",
            status="in_progress",
            smart=SmartCriteria(time_bound="2026-12-31"),
            tracking=TrackingConfig(target=100.0, unit="pages"),
        )
        goal.time_entries = [
            TimeEntry(date=date(2026, 1, 1), node_id="g", quantity=50.0),
            TimeEntry(date=date(2026, 1, 11), node_id="g", quantity=25.0),
        ]
        result = analyze_goal(goal, date(2026, 1, 15))
        assert result.on_track is True

    def test_on_track_false(self) -> None:
        goal = Node(
            node_id="g",
            title="G",
            status="in_progress",
            smart=SmartCriteria(time_bound="2026-01-20"),
            tracking=TrackingConfig(target=1000.0, unit="pages"),
        )
        goal.time_entries = [
            TimeEntry(date=date(2026, 1, 1), node_id="g", quantity=1.0),
            TimeEntry(date=date(2026, 1, 11), node_id="g", quantity=1.0),
        ]
        result = analyze_goal(goal, date(2026, 1, 15))
        assert result.on_track is False

    def test_tags_propagated(self) -> None:
        goal = Node(
            node_id="g",
            title="G",
            tags=["pro", "learning"],
        )
        result = analyze_goal(goal, date(2026, 1, 1))
        assert result.tags == ["pro", "learning"]

    def test_today_defaults(self) -> None:
        goal = Node(node_id="g", title="G")
        result = analyze_goal(goal)
        assert result.node_id == "g"

    def test_child_late_propagates(self) -> None:
        """A late child makes the parent off-track even without full prediction."""
        goal = Node(
            node_id="g",
            title="G",
            smart=SmartCriteria(time_bound="2026-03-01"),
            children=[
                Node(
                    node_id="a",
                    title="A",
                    status="in_progress",
                    tracking=TrackingConfig(target=1000.0, unit="pages"),
                ),
                Node(
                    node_id="b",
                    title="B",
                    tracking=TrackingConfig(target=50.0, unit="pages"),
                ),
            ],
        )
        goal.time_entries = [
            TimeEntry(date=date(2026, 1, 1), node_id="a", quantity=1.0),
            TimeEntry(date=date(2026, 1, 11), node_id="a", quantity=1.0),
        ]
        result = analyze_goal(goal, date(2026, 2, 1))
        assert result.on_track is False
