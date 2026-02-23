"""
Analytics engine for the recursive goal tree.

Every node is analysed with the same logic:

* **Parent nodes** derive their progress from their children —
  either via a weighted average (homogeneous units) or a
  prediction-based estimate (mixed units).
* **Leaf nodes** compute progress from their own
  :class:`~app.parser.TrackingConfig` and the time-journal entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from .parser import Node, SmartCriteria, TimeEntry, TrackingConfig

PRIORITY_ORDER: dict[str, int] = {
    "optional": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "capital": 4,
}
"""Map from priority label to its numeric rank (higher is more important)."""


# ── Result data class ────────────────────────────────────────────────────


@dataclass
class NodeProgress:
    """Result of analysing a single node in the goal tree.

    Instances are produced by :func:`analyze_node` and enriched by
    :func:`analyze_goal` for top-level goals.

    :param node_id: Unique identifier of the source node.
    :param title: Human-readable title.
    :param status: Derived or explicit status string.
    :param priority: Resolved priority label (never ``None``).
    :param priority_rank: Numeric rank from :pydata:`PRIORITY_ORDER`.
    :param has_children: ``True`` when the node has child nodes.
    :param tracking_mode: ``"cumulative"``, ``"performance"``, or
        ``"fixed"`` for date-bounded leaves.
    :param unit_label: Free-form unit (e.g. ``"pages"``).
    :param target: Numeric target value, if any.
    :param current_value: Current progress value.
    :param percent_complete: Progress as a percentage (0–100).
    :param start: Start date, if declared.
    :param end: End date, if declared.
    :param predicted_end: Statistically predicted completion date.
    :param prediction_partial: ``True`` when some children lack predictions.
    :param predicted_remaining: Remaining quantity to reach *target*.
    :param velocity_per_day: Observed velocity in *unit* per day.
    :param depends_on: List of sibling node ids this node depends on.
    :param has_smart: ``True`` when SMART criteria are present.
    :param smart_data: Serialised SMART criteria dictionary.
    :param node_type: ``"bounded"`` or ``"open"``.
    :param progress_source: How *percent_complete* was computed —
        ``"tracking"``, ``"weighted"``, ``"predicted"``, or
        ``"insufficient"``.
    :param children: Analysed child nodes (empty for leaves).
    :param deadline: Deadline from SMART *time_bound* (top-level only).
    :param on_track: Whether the predicted end is before the deadline
        (top-level only; ``None`` when undetermined).
    :param tags: Tag list (top-level only).
    """

    node_id: str
    title: str
    status: str
    priority: str
    priority_rank: int
    has_children: bool
    tracking_mode: str
    unit_label: str
    target: Optional[float]
    current_value: float
    percent_complete: float
    start: Optional[date]
    end: Optional[date]
    predicted_end: Optional[date]
    prediction_partial: bool
    predicted_remaining: Optional[float]
    velocity_per_day: Optional[float]
    depends_on: list[str]
    has_smart: bool
    smart_data: Optional[dict[str, str]] = None
    node_type: str = "bounded"
    progress_source: str = "tracking"
    children: list[NodeProgress] = field(default_factory=list)

    deadline: Optional[datetime] = None
    on_track: Optional[bool] = None
    tags: list[str] = field(default_factory=list)


# ── Computation helpers ──────────────────────────────────────────────────


def _smart_to_dict(
    smart: Optional[SmartCriteria],
) -> Optional[dict[str, str]]:
    """Serialise a :class:`~app.parser.SmartCriteria` to a plain dict.

    :param smart: The criteria to convert, or ``None``.
    :returns: A five-key dictionary, or ``None``.
    """
    if smart is None:
        return None
    return {
        "specific": smart.specific or "",
        "measurable": smart.measurable or "",
        "actionable": smart.actionable or "",
        "relevant": smart.relevant or "",
        "time_bound": smart.time_bound or "",
    }


def _get_entries(
    all_entries: list[TimeEntry],
    node_id: str,
) -> list[TimeEntry]:
    """Filter journal entries for a specific node.

    :param all_entries: Complete entry list for the parent goal.
    :param node_id: Node to filter on.
    :returns: Matching entries (order preserved).
    """
    return [e for e in all_entries if e.node_id == node_id]


def _current_value(
    tracking: TrackingConfig,
    entries: list[TimeEntry],
    stored: float,
) -> float:
    """Compute the current progress value from journal entries.

    * **Cumulative** mode: sum of all entry quantities.
    * **Performance** mode: maximum entry quantity.

    Falls back to *stored* when no entries exist.

    :param tracking: Tracking configuration.
    :param entries: Journal entries for this node.
    :param stored: Pre-existing ``actual`` value from metadata.
    :returns: Current numeric progress.
    """
    if tracking.mode == "performance":
        return max((e.quantity for e in entries), default=stored)
    else:
        return sum(e.quantity for e in entries) if entries else stored


def _velocity(
    tracking: TrackingConfig,
    entries: list[TimeEntry],
) -> Optional[float]:
    """Estimate daily velocity from at least two journal entries.

    * **Cumulative**: total quantity / total days.
    * **Performance**: slope of a least-squares linear regression.

    :param tracking: Tracking configuration.
    :param entries: Journal entries for this node.
    :returns: Units per day, or ``None`` if insufficient data.
    """
    if len(entries) < 2:
        return None
    sorted_e: list[TimeEntry] = sorted(entries, key=lambda e: e.date)
    first: date = sorted_e[0].date
    last: date = sorted_e[-1].date
    span: int = (last - first).days
    if span == 0:
        return None

    if tracking.mode == "performance":
        n: int = len(sorted_e)
        xs: list[int] = [(e.date - first).days for e in sorted_e]
        ys: list[float] = [e.quantity for e in sorted_e]
        xm: float = sum(xs) / n
        ym: float = sum(ys) / n
        num: float = sum((x - xm) * (y - ym) for x, y in zip(xs, ys))
        den: float = sum((x - xm) ** 2 for x in xs)
        if den == 0:
            return None
        return max(0.0, num / den)
    else:
        return sum(e.quantity for e in sorted_e) / span


def _predict(
    tracking: TrackingConfig,
    current: float,
    vel: Optional[float],
    today: date,
) -> Optional[date]:
    """Predict the completion date from current value and velocity.

    :param tracking: Tracking configuration (must have a positive target).
    :param current: Current progress value.
    :param vel: Daily velocity (``None`` means unpredictable).
    :param today: Reference date.
    :returns: Predicted completion date, or ``None``.
    """
    if tracking.target is None or tracking.target <= 0:
        return None
    if current >= tracking.target:
        return today
    if vel is None or vel <= 0:
        return None
    remaining: float = tracking.target - current
    days: int = int(remaining / vel) + 1
    return today + timedelta(days=days)


def _leaf_percent(
    tracking: TrackingConfig,
    current: float,
    status: str,
) -> float:
    """Compute the percentage for a leaf node.

    Special cases:

    * ``done`` → always 100 %.
    * ``cancelled`` with no progress → 0 %.
    * ``cancelled`` with progress → capped at 99 %.
    * ``in_progress`` without a target → 50 % (indeterminate).

    :param tracking: Tracking configuration.
    :param current: Current progress value.
    :param status: Node status string.
    :returns: Percentage between 0 and 100.
    """
    if status == "done":
        return 100.0
    if status in ("not_started", "cancelled") and current == 0:
        return 0.0
    if status == "cancelled":
        if tracking.target and tracking.target > 0:
            return min(99.0, (current / tracking.target) * 100.0)
        return 0.0
    if tracking.target and tracking.target > 0:
        return min(100.0, (current / tracking.target) * 100.0)
    return 50.0 if status == "in_progress" else 0.0


# ── Subtree helpers ──────────────────────────────────────────────────────


def _subtree_weight(node: NodeProgress) -> float:
    """Compute the weight of a subtree for weighted-average progress.

    Leaf weight is its :pyattr:`~NodeProgress.target` (or, for
    ``fixed`` nodes, the duration in days).  Parent weight is the
    recursive sum of its active children's weights.

    :param node: Root of the subtree.
    :returns: Non-negative weight.
    """
    if not node.children:
        if node.tracking_mode == "fixed" and node.start and node.end:
            return float(max(1, (node.end - node.start).days))
        return node.target if node.target and node.target > 0 else 0.0
    return sum(
        _subtree_weight(c)
        for c in node.children
        if c.status != "cancelled" and c.node_type != "open"
    )


def _leaf_units(node: NodeProgress) -> set[str]:
    """Collect distinct unit labels from all leaves in a subtree.

    Fixed-end leaves contribute the sentinel ``"__fixed__"`` instead of
    an actual unit string.

    :param node: Root of the subtree.
    :returns: Set of unit strings.
    """
    if not node.children:
        if node.tracking_mode == "fixed":
            return {"__fixed__"}
        return {node.unit_label} if node.unit_label else set()
    units: set[str] = set()
    for child in node.children:
        if child.status != "cancelled" and child.node_type != "open":
            units |= _leaf_units(child)
    return units


def _prediction_based_percent(
    predicted_end: Optional[date],
    earliest_start: Optional[date],
    today: date,
) -> Optional[float]:
    """Estimate progress as elapsed time over predicted total duration.

    Used when child units are mixed and a prediction exists.

    :param predicted_end: Latest predicted end among children.
    :param earliest_start: Earliest start date among children.
    :param today: Reference date.
    :returns: Percentage (0–100), or ``None`` if inputs are missing.
    """
    if not predicted_end or not earliest_start:
        return None
    total_days: int = (predicted_end - earliest_start).days
    if total_days <= 0:
        return 100.0
    elapsed: int = (today - earliest_start).days
    return min(100.0, max(0.0, (elapsed / total_days) * 100))


# ── Recursive analysis ───────────────────────────────────────────────────


def analyze_node(
    node: Node,
    all_entries: list[TimeEntry],
    today: date,
) -> NodeProgress:
    """Recursively analyse a node and all its descendants.

    * **Parent nodes**: progress is a weighted average when child units
      are homogeneous, or a prediction-based estimate when mixed.
    * **Leaf nodes**: progress comes from journal entries and the
      node's :class:`~app.parser.TrackingConfig`.

    :param node: The :class:`~app.parser.Node` to analyse.
    :param all_entries: Journal entries for the entire parent goal.
    :param today: Reference date for predictions and fixed-end progress.
    :returns: A fully populated :class:`NodeProgress`.
    """

    if node.has_children:
        # ── Parent node ──────────────────────────────────────────────
        child_progress: list[NodeProgress] = [
            analyze_node(child, all_entries, today) for child in node.children
        ]

        child_types: dict[str, str] = {
            child.node_id: child.node_type for child in node.children
        }

        # Active children (exclude cancelled and open)
        active: list[NodeProgress] = [
            c
            for c in child_progress
            if c.status != "cancelled" and child_types.get(c.node_id) != "open"
        ]

        # Unit homogeneity check
        units: set[str] = set()
        for child_node in active:
            units |= _leaf_units(child_node)
        units.discard("")
        homogeneous: bool = len(units) <= 1

        # Predicted completion from bounded, non-done children
        active_children: list[NodeProgress] = [
            c
            for c in child_progress
            if c.status not in ("done", "cancelled")
            and child_types.get(c.node_id) != "open"
        ]
        active_with_pred: list[NodeProgress] = [
            c for c in active_children if c.predicted_end
        ]
        all_predicted: bool = len(active_children) == len(active_with_pred)

        pred_dates: list[date] = [
            c.predicted_end for c in active_with_pred if c.predicted_end
        ]
        done_dates: list[date] = [
            c.end for c in child_progress if c.status == "done" and c.end
        ]
        all_dates: list[date] = pred_dates + done_dates

        predicted_end: Optional[date]
        prediction_partial: bool
        if all_dates and all_predicted:
            predicted_end = max(all_dates)
            prediction_partial = False
        elif all_dates:
            predicted_end = max(all_dates)
            prediction_partial = True
        else:
            predicted_end = None
            prediction_partial = False

        # Progress computation
        percent: float
        progress_source: str
        if homogeneous and active:
            weights: list[float] = [_subtree_weight(c) for c in active]
            total_weight: float = sum(weights)
            if total_weight > 0:
                percent = (
                    sum(w * c.percent_complete for w, c in zip(weights, active))
                    / total_weight
                )
            else:
                percent = sum(c.percent_complete for c in active) / len(active)
            progress_source = "weighted"
        elif predicted_end:
            starts: list[date] = [c.start for c in child_progress if c.start]
            earliest_start: Optional[date] = min(starts) if starts else None
            pred_pct: Optional[float] = _prediction_based_percent(
                predicted_end,
                earliest_start,
                today,
            )
            if pred_pct is not None:
                percent = pred_pct
                progress_source = "predicted"
            else:
                percent = 0.0
                progress_source = "insufficient"
        else:
            percent = 0.0
            progress_source = "insufficient" if active else "tracking"

        # Derive status from bounded children
        bounded_children: list[NodeProgress] = [
            c for c in child_progress if child_types.get(c.node_id) != "open"
        ]
        child_statuses: set[str] = (
            {c.status for c in bounded_children} if bounded_children else set()
        )

        derived_status: str
        if child_statuses == {"done"}:
            derived_status = "done"
        elif child_statuses == {"cancelled"}:
            derived_status = "cancelled"
        elif child_statuses <= {"not_started", "cancelled"}:
            derived_status = "not_started"
        elif child_statuses <= {"done", "cancelled"}:
            derived_status = "done"
        elif child_statuses <= {"paused", "not_started", "cancelled"}:
            derived_status = "paused"
        else:
            derived_status = "in_progress"

        return NodeProgress(
            node_id=node.node_id,
            title=node.title,
            status=derived_status,
            priority=node.priority or "medium",
            priority_rank=PRIORITY_ORDER.get(node.priority or "medium", 2),
            has_children=True,
            tracking_mode=node.tracking.mode,
            unit_label=node.tracking.unit,
            target=node.tracking.target,
            current_value=round(percent, 1),
            percent_complete=round(percent, 1),
            start=node.start,
            end=node.end,
            predicted_end=predicted_end,
            prediction_partial=prediction_partial,
            predicted_remaining=None,
            velocity_per_day=None,
            depends_on=node.depends_on,
            has_smart=node.smart is not None,
            smart_data=_smart_to_dict(node.smart),
            node_type=node.node_type,
            progress_source=progress_source,
            children=child_progress,
        )

    else:
        # ── Leaf node ────────────────────────────────────────────────
        status: str = node.status
        entries: list[TimeEntry] = _get_entries(all_entries, node.node_id)

        # Fixed end: progression is time-based
        if node.fixed_end and node.start and node.end:
            total_days: int = (node.end - node.start).days
            percent: float
            if total_days <= 0:
                percent = 100.0
                status = "done"
            elif today >= node.end:
                percent = 100.0
                status = "done"
            elif today <= node.start:
                percent = 0.0
            else:
                elapsed: int = (today - node.start).days
                percent = min(100.0, (elapsed / total_days) * 100)
                status = "in_progress"

            return NodeProgress(
                node_id=node.node_id,
                title=node.title,
                status=status,
                priority=node.priority or "medium",
                priority_rank=PRIORITY_ORDER.get(node.priority or "medium", 2),
                has_children=False,
                tracking_mode="fixed",
                unit_label="",
                target=None,
                current_value=round(percent, 1),
                percent_complete=round(percent, 1),
                start=node.start,
                end=node.end,
                predicted_end=node.end,
                prediction_partial=False,
                predicted_remaining=None,
                velocity_per_day=None,
                depends_on=node.depends_on,
                has_smart=node.smart is not None,
                smart_data=_smart_to_dict(node.smart),
                node_type=node.node_type,
                children=[],
            )

        current: float = _current_value(node.tracking, entries, node.actual)

        # Done means complete: override current to match target
        if status == "done" and node.tracking.target and node.tracking.target > 0:
            current = node.tracking.target

        percent = _leaf_percent(node.tracking, current, status)
        vel: Optional[float] = _velocity(node.tracking, entries)

        # Derive status for regular leaves when left at default
        if status == "not_started" and node.node_type != "open":
            if entries:
                if percent >= 100:
                    status = "done"
                else:
                    status = "in_progress"

        pred_end: Optional[date] = None
        pred_remaining: Optional[float] = None
        if status in ("done", "cancelled"):
            pred_end = node.end
        elif node.tracking.target and node.tracking.target > 0:
            pred_end = _predict(node.tracking, current, vel, today)
            rem: float = max(0.0, node.tracking.target - current)
            pred_remaining = round(rem, 2) if rem > 0 else 0.0

        return NodeProgress(
            node_id=node.node_id,
            title=node.title,
            status=status,
            priority=node.priority or "medium",
            priority_rank=PRIORITY_ORDER.get(node.priority or "medium", 2),
            has_children=False,
            tracking_mode=node.tracking.mode,
            unit_label=node.tracking.unit,
            target=node.tracking.target,
            current_value=round(current, 2),
            percent_complete=round(percent, 1),
            start=node.start,
            end=node.end,
            predicted_end=pred_end,
            prediction_partial=False,
            predicted_remaining=pred_remaining,
            velocity_per_day=round(vel, 3) if vel else None,
            depends_on=node.depends_on,
            has_smart=node.smart is not None,
            smart_data=_smart_to_dict(node.smart),
            node_type=node.node_type,
            children=[],
        )


# ── Top-level goal analysis ─────────────────────────────────────────────


def analyze_goal(
    goal: Node,
    today: Optional[date] = None,
) -> NodeProgress:
    """Analyse a top-level goal, adding deadline and on-track fields.

    Delegates to :func:`analyze_node` for the recursive work, then
    resolves the SMART *time_bound* into a :pyattr:`~NodeProgress.deadline`
    and determines whether the goal is on track.

    :param goal: A top-level :class:`~app.parser.Node`.
    :param today: Reference date (defaults to ``date.today()``).
    :returns: An enriched :class:`NodeProgress`.
    """
    if today is None:
        today = date.today()

    all_entries: list[TimeEntry] = goal.time_entries
    progress: NodeProgress = analyze_node(goal, all_entries, today)

    # Top-level metadata
    progress.tags = goal.tags

    # Deadline from SMART time_bound
    if goal.smart and goal.smart.time_bound:
        tb: str = str(goal.smart.time_bound).strip()
        try:
            progress.deadline = datetime.strptime(tb, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                progress.deadline = datetime.strptime(tb, "%Y-%m-%d")
            except ValueError:
                pass

    # On-track determination
    if progress.deadline and progress.predicted_end:
        progress.on_track = progress.predicted_end <= progress.deadline.date()
    elif progress.deadline:
        deadline_date: date = progress.deadline.date()
        any_late: bool = False

        def _check_late(check_node: NodeProgress) -> None:
            nonlocal any_late
            if check_node.predicted_end and check_node.predicted_end > deadline_date:
                any_late = True
            for child in check_node.children:
                _check_late(child)

        _check_late(progress)
        if any_late:
            progress.on_track = False

    return progress
