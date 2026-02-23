"""
Parser for a single-file SMART goals Markdown document.

All-headings format:

.. code-block:: markdown

    ## id : Title          → top-level goal
    ### id : Title         → child
    #### id : Title        → grandchild

Metadata is a YAML list under each heading.
Journal is a ``###`` (or deeper) heading named *Journal de temps*
under each top-level goal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import yaml

VALID_PRIORITIES: tuple[str, ...] = (
    "optional",
    "low",
    "medium",
    "high",
    "capital",
)
"""Accepted priority values, from lowest to highest."""

VALID_STATUSES: tuple[str, ...] = (
    "not_started",
    "in_progress",
    "done",
    "paused",
    "cancelled",
)
"""Accepted status values."""

JOURNAL_HEADING: str = "journal de temps"
"""Normalised (lower-case) heading text that marks a time-journal section."""


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass
class TrackingConfig:
    """Configuration for how a leaf node tracks its progress.

    :param mode: Tracking mode — ``"cumulative"`` or ``"performance"``.
    :param target: Numeric target value (e.g. ``382`` for 382 pages).
    :param unit: Free-form unit label (e.g. ``"pages"``, ``"minutes"``).
    """

    mode: str = "cumulative"
    target: Optional[float] = None
    unit: str = ""


@dataclass
class SmartCriteria:
    """SMART goal-setting criteria attached to any node.

    :param specific: What exactly will be accomplished.
    :param measurable: How success will be measured.
    :param actionable: Concrete actions to take.
    :param relevant: Why this goal matters.
    :param time_bound: Target date or deadline as free-form text.
    """

    specific: str = ""
    measurable: str = ""
    actionable: str = ""
    relevant: str = ""
    time_bound: Optional[str] = None


@dataclass
class TimeEntry:
    """A single row from the time-journal table.

    :param date: Date of the entry.
    :param node_id: Identifier of the node this entry belongs to.
    :param quantity: Numeric value recorded (e.g. ``35`` pages).
    :param notes: Optional free-text annotation.
    """

    date: date
    node_id: str
    quantity: float
    notes: str = ""


@dataclass
class Node:
    """Unified recursive node for goals, sub-objectives, and tasks.

    A node may represent a top-level goal (heading ``##``), a child
    (``###``), a grandchild (``####``), etc.  Nodes with children derive
    their progress from those children; leaf nodes use their own
    :pyattr:`tracking` configuration and the time journal.

    :param node_id: Unique identifier (the part before ``:`` in the heading).
    :param title: Human-readable title.
    :param node_type: ``"bounded"`` (default) or ``"open"``.
    :param status: Current status — one of :pydata:`VALID_STATUSES`.
    :param priority: Priority level or ``None`` to inherit from parent.
    :param created: Creation date.
    :param tags: Arbitrary tag list (top-level goals only).
    :param smart: Optional SMART criteria block.
    :param tracking: Tracking configuration for leaf nodes.
    :param actual: Initial progress value before any journal entries.
    :param start: Start date.
    :param end: End / deadline date.
    :param fixed_end: ``True`` when the ``end`` date was suffixed with ``!``.
    :param depends_on: List of sibling node ids this node depends on.
    :param children: Nested child nodes.
    :param time_entries: Journal entries (populated at goal level only).
    :param source_file: Path of the Markdown file this node was parsed from.
    """

    node_id: str
    title: str
    node_type: str = "bounded"
    status: str = "not_started"
    priority: Optional[str] = None
    created: Optional[date] = None
    tags: list[str] = field(default_factory=list)
    smart: Optional[SmartCriteria] = None
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    actual: float = 0
    start: Optional[date] = None
    end: Optional[date] = None
    fixed_end: bool = False
    depends_on: list[str] = field(default_factory=list)
    children: list[Node] = field(default_factory=list)
    time_entries: list[TimeEntry] = field(default_factory=list)
    source_file: str = ""

    @property
    def has_children(self) -> bool:
        """Return ``True`` when this node has at least one child."""
        return len(self.children) > 0

    def find_node(self, target_id: str) -> Optional[Node]:
        """Recursively search for a descendant by its identifier.

        :param target_id: The :pyattr:`node_id` to look for.
        :returns: The matching :class:`Node`, or ``None``.
        """
        if self.node_id == target_id:
            return self
        for child in self.children:
            found: Optional[Node] = child.find_node(target_id)
            if found:
                return found
        return None


# ── Value + unit extraction ──────────────────────────────────────────────


def _extract_value_unit(text: Any) -> tuple[Optional[float], str]:
    """Extract a numeric value and its trailing unit from *text*.

    :param text: Raw value such as ``"84 pages"`` or ``"55%"``.
    :returns: A ``(number, unit)`` tuple.  Both may be empty on failure.
    """
    if text is None:
        return None, ""
    text_str: str = str(text).strip()
    if not text_str:
        return None, ""

    match: Optional[re.Match[str]] = re.match(
        r"^([0-9]*\.?[0-9]+)\s*(%)\s*$",
        text_str,
    )
    if match:
        return float(match.group(1)), "%"

    match = re.match(r"^([0-9]*\.?[0-9]+)\s*(.*)", text_str)
    if match:
        return float(match.group(1)), match.group(2).strip()

    return None, ""


# ── Helpers ──────────────────────────────────────────────────────────────


def _parse_date(val: Any) -> Optional[date]:
    """Parse a ``YYYY-MM-DD`` string (or pass through a :class:`date`).

    :param val: Raw value from YAML metadata.
    :returns: A :class:`date` or ``None`` on failure.
    """
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _clean_depends(val: Any) -> list[str]:
    """Normalise a ``depends_on`` value to a list of identifier strings.

    :param val: Raw value — may be a list, a single string, or ``None``.
    :returns: A (possibly empty) list of non-null id strings.
    """
    if val is None or val == "null" or val == "":
        return []
    if isinstance(val, list):
        return [str(v) for v in val if v and str(v) != "null"]
    return [str(val)]


def _clean_priority(val: Any) -> Optional[str]:
    """Validate and return a priority string, or ``None`` if absent/invalid.

    :param val: Raw value from YAML metadata.
    :returns: A member of :pydata:`VALID_PRIORITIES` or ``None``.
    """
    if val is None:
        return None
    priority: str = str(val)
    return priority if priority in VALID_PRIORITIES else None


def _clean_status(val: Any) -> str:
    """Validate and return a status string, defaulting to ``"not_started"``.

    :param val: Raw value from YAML metadata.
    :returns: A member of :pydata:`VALID_STATUSES`.
    """
    status: str = str(val) if val else "not_started"
    return status if status in VALID_STATUSES else "not_started"


def _parse_tracking(data: dict[str, Any]) -> TrackingConfig:
    """Build a :class:`TrackingConfig` from parsed YAML metadata.

    Handles three common formats:

    * ``tracking:\\n    target: 84 pages`` — standard nested dict.
    * ``tracking:\\n  - target: 84 pages`` — list variant.
    * ``tracking: null`` with ``target`` at root level — 2-space indent
      artefact.

    :param data: Flat metadata dictionary.
    :returns: A populated :class:`TrackingConfig`.
    """
    raw: Any = data.get("tracking")

    # Handle case where tracking: null and target/mode are at root level
    if raw is None and "target" in data:
        mode: str = str(data.get("mode", "cumulative"))
        target_num: Optional[float]
        unit: str
        target_num, unit = _extract_value_unit(data.get("target"))
        return TrackingConfig(mode=mode, target=target_num, unit=unit)

    if not raw:
        return TrackingConfig()

    # Handle list format
    if isinstance(raw, list):
        merged: dict[str, Any] = {}
        for item in raw:
            if isinstance(item, dict):
                merged.update(item)
        raw = merged
    if not isinstance(raw, dict):
        return TrackingConfig()

    mode = str(raw.get("mode", "cumulative"))
    target_num, unit = _extract_value_unit(raw.get("target"))
    return TrackingConfig(mode=mode, target=target_num, unit=unit)


def _parse_actual(
    data: dict[str, Any],
    tracking: TrackingConfig,
) -> tuple[float, TrackingConfig]:
    """Extract an ``actual`` value and optionally update the tracking unit.

    :param data: Flat metadata dictionary.
    :param tracking: Current tracking config (may be copied with new unit).
    :returns: ``(numeric_value, possibly_updated_tracking)``.
    """
    raw: Any = data.get("actual")
    if raw is None:
        return 0.0, tracking
    num: Optional[float]
    unit: str
    num, unit = _extract_value_unit(raw)
    if num is None:
        return 0.0, tracking
    if not tracking.unit and unit:
        tracking = TrackingConfig(
            mode=tracking.mode,
            target=tracking.target,
            unit=unit,
        )
    return num, tracking


def _parse_smart(data: dict[str, Any]) -> Optional[SmartCriteria]:
    """Build a :class:`SmartCriteria` from metadata, if present.

    Also accepts the French typo ``mesurable`` for ``measurable``.

    :param data: Flat metadata dictionary.
    :returns: A :class:`SmartCriteria` or ``None``.
    """
    raw: Any = data.get("smart")
    if not raw or not isinstance(raw, dict):
        return None
    return SmartCriteria(
        specific=raw.get("specific", ""),
        measurable=raw.get("measurable", raw.get("mesurable", "")),
        actionable=raw.get("actionable", ""),
        relevant=raw.get("relevant", ""),
        time_bound=raw.get("time_bound"),
    )


# ── Metadata parser ─────────────────────────────────────────────────────


def _parse_metadata(body: str) -> dict[str, Any]:
    """Parse YAML-list metadata from the text body under a heading.

    Lines are collected while they look like YAML (``- key: value`` or
    continuation indents).  Free-form text after a blank line stops
    collection.

    :param body: Raw text between two headings.
    :returns: A flat dictionary of parsed metadata fields.
    """
    yaml_lines: list[str] = []
    saw_blank: bool = False

    for line in body.split("\n"):
        stripped: str = line.strip()
        if not stripped:
            saw_blank = True
            continue
        if saw_blank:
            if stripped.startswith("- ") or (stripped[0] == " " and yaml_lines):
                yaml_lines.append("")
                saw_blank = False
            else:
                break
        if stripped.startswith("- ") or (
            yaml_lines and (line[0] == " " or stripped.startswith("- "))
        ):
            yaml_lines.append(line)
        else:
            break

    if not yaml_lines:
        return {}

    yaml_text: str = "\n".join(yaml_lines)
    try:
        parsed: Any = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return {}

    if isinstance(parsed, list):
        result: dict[str, Any] = {}
        for item in parsed:
            if isinstance(item, dict):
                result.update(item)
            elif isinstance(item, str) and ":" in item:
                key: str
                val: str
                key, _, val = item.partition(":")
                result[key.strip()] = val.strip()
        return result
    elif isinstance(parsed, dict):
        return parsed
    return {}


# ── Time-journal parser ─────────────────────────────────────────────────


def _parse_time_entries(
    text: str,
    default_node_id: str = "",
) -> list[TimeEntry]:
    """Parse a Markdown table of time-journal entries.

    Two table formats are accepted:

    * **Full** (4 columns): ``| Date | Tâche | Valeur | Notes |`` —
      used at the goal level where entries target different children.
    * **Short** (2–3 columns): ``| Date | Valeur | Notes |`` — used at
      the leaf level where the task id is implicit.

    The format is auto-detected from the header row.  When no header is
    found, the parser falls back to *default_node_id* and tries the
    short format first, then the full format.

    :param text: Raw text of the journal section.
    :param default_node_id: Node id to use when the table has no task
        column (leaf-level journal).
    :returns: A list of :class:`TimeEntry` objects.
    """
    entries: list[TimeEntry] = []
    short_format: Optional[bool] = None

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        lower: str = line.lower()

        # Detect format from header row
        if "date" in lower and ("valeur" in lower or "value" in lower):
            has_task_col: bool = "tâche" in lower or "tache" in lower or "task" in lower
            short_format = not has_task_col
            continue

        cols: list[str] = [c.strip() for c in line.split("|")[1:-1]]

        # Auto-detect format from column count when no header was found
        if short_format is None:
            if default_node_id and len(cols) in (2, 3):
                short_format = True
            else:
                short_format = False

        if short_format:
            # Short format: | Date | Valeur | Notes? |
            if len(cols) < 2:
                continue
            entry_date: Optional[date] = _parse_date(cols[0])
            if entry_date is None:
                continue
            quantity: Optional[float]
            quantity, _ = _extract_value_unit(cols[1])
            if quantity is None:
                continue
            entries.append(
                TimeEntry(
                    date=entry_date,
                    node_id=default_node_id,
                    quantity=quantity,
                    notes=cols[2] if len(cols) > 2 else "",
                )
            )
        else:
            # Full format: | Date | Tâche | Valeur | Notes? |
            if len(cols) < 3:
                continue
            entry_date = _parse_date(cols[0])
            if entry_date is None:
                continue
            quantity, _ = _extract_value_unit(cols[2])
            if quantity is None:
                continue
            node_id: str = cols[1] if cols[1] else default_node_id
            entries.append(
                TimeEntry(
                    date=entry_date,
                    node_id=node_id,
                    quantity=quantity,
                    notes=cols[3] if len(cols) > 3 else "",
                )
            )

    return entries


# ── Heading splitter ─────────────────────────────────────────────────────


@dataclass
class _Section:
    """An intermediate representation of a single Markdown heading section.

    :param level: Heading depth (2 for ``##``, 3 for ``###``, etc.).
    :param raw_heading: Original heading text after the ``#`` characters.
    :param node_id: Parsed identifier (empty when absent).
    :param title: Parsed title (may equal *raw_heading* when no id).
    :param body: Text between this heading and the next.
    :param is_journal: ``True`` when this heading is a time-journal section.
    """

    level: int
    raw_heading: str
    node_id: str
    title: str
    body: str
    is_journal: bool = False


def _split_into_sections(text: str) -> list[_Section]:
    """Split an entire document body into a flat list of :class:`_Section`.

    :param text: Document body (frontmatter already stripped).
    :returns: Ordered list of sections.
    """
    heading_re: re.Pattern[str] = re.compile(
        r"^(#{2,6})\s+(.+)$",
        re.MULTILINE,
    )
    matches: list[re.Match[str]] = list(heading_re.finditer(text))
    sections: list[_Section] = []

    for idx, heading_match in enumerate(matches):
        level: int = len(heading_match.group(1))
        raw: str = heading_match.group(2).strip()
        body_start: int = heading_match.end()
        body_end: int = (
            matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        )
        body: str = text[body_start:body_end].strip()

        if raw.lower() == JOURNAL_HEADING:
            sections.append(
                _Section(
                    level=level,
                    raw_heading=raw,
                    node_id="",
                    title="",
                    body=body,
                    is_journal=True,
                )
            )
            continue

        id_title_match: Optional[re.Match[str]] = re.match(
            r"^([\w-]+)\s*:\s*(.+)$",
            raw,
        )
        node_id: str
        title: str
        if id_title_match:
            node_id = id_title_match.group(1).strip()
            title = id_title_match.group(2).strip()
        else:
            node_id = ""
            title = raw

        sections.append(
            _Section(
                level=level,
                raw_heading=raw,
                node_id=node_id,
                title=title,
                body=body,
            )
        )

    return sections


# ── Node builder ─────────────────────────────────────────────────────────


def _build_node(section: _Section, meta: dict[str, Any]) -> Node:
    """Construct a :class:`Node` from a section and its parsed metadata.

    :param section: The heading section to convert.
    :param meta: Pre-parsed YAML metadata dictionary.
    :returns: A new :class:`Node` (without children).
    """
    tracking: TrackingConfig = _parse_tracking(meta)
    actual: float
    actual, tracking = _parse_actual(meta, tracking)

    raw_end: Any = meta.get("end")
    fixed_end: bool = False
    if raw_end is not None:
        raw_end_str: str = str(raw_end).strip()
        if raw_end_str.endswith("!"):
            fixed_end = True
            raw_end = raw_end_str[:-1].strip()
    end_date: Optional[date] = _parse_date(raw_end)

    return Node(
        node_id=section.node_id,
        title=section.title,
        node_type=str(meta.get("type", "bounded")),
        status=_clean_status(meta.get("status")),
        priority=_clean_priority(meta.get("priority")),
        created=_parse_date(meta.get("created")),
        tags=(meta.get("tags", []) if isinstance(meta.get("tags"), list) else []),
        smart=_parse_smart(meta),
        tracking=tracking,
        actual=actual,
        start=_parse_date(meta.get("start")),
        end=end_date,
        fixed_end=fixed_end,
        depends_on=_clean_depends(meta.get("depends_on")),
    )


# ── Tree builder ─────────────────────────────────────────────────────────


def _collect_ids(node: Node) -> set[str]:
    """Collect all node identifiers in a subtree.

    :param node: Root of the subtree.
    :returns: Set of all :pyattr:`Node.node_id` values.
    """
    ids: set[str] = {node.node_id}
    for child in node.children:
        ids |= _collect_ids(child)
    return ids


def _build_tree(
    sections: list[_Section],
    start_idx: int,
    parent_level: int,
    parent_node_id: str = "",
) -> tuple[list[Node], list[TimeEntry], int]:
    """Recursively build a tree of nodes from a flat section list.

    Processes sections starting at *start_idx* whose heading level is
    strictly deeper than *parent_level*.

    Journal entries are validated against known node identifiers:

    * Under a **leaf** (no sibling nodes before the journal), the
      short format is accepted and defaults to *parent_node_id*.
    * Under a **non-leaf**, entries must reference a node id that was
      defined earlier in the file.  Entries with unknown ids are
      silently dropped.

    :param sections: Complete flat list of document sections.
    :param start_idx: Index of the first section to consider.
    :param parent_level: Heading level of the parent node.
    :param parent_node_id: Node id of the parent, used as default for
        leaf-level journal entries that omit the task column.
    :returns: ``(children, time_entries, next_index)`` where *next_index*
        is the first section index that was **not** consumed.
    """
    children: list[Node] = []
    time_entries: list[TimeEntry] = []
    idx: int = start_idx
    known_ids: set[str] = set()

    while idx < len(sections):
        sec: _Section = sections[idx]

        if sec.level <= parent_level:
            break

        if sec.is_journal:
            is_leaf_journal: bool = len(known_ids) == 0
            default_id: str = parent_node_id if is_leaf_journal else ""
            raw_entries: list[TimeEntry] = _parse_time_entries(
                sec.body, default_node_id=default_id
            )
            valid_ids: set[str] = known_ids | (
                {parent_node_id} if parent_node_id else set()
            )
            time_entries.extend(e for e in raw_entries if e.node_id in valid_ids)
            idx += 1
            continue

        if not sec.node_id:
            idx += 1
            continue

        meta: dict[str, Any] = _parse_metadata(sec.body)
        node: Node = _build_node(sec, meta)
        known_ids.add(node.node_id)

        node_children: list[Node]
        child_entries: list[TimeEntry]
        node_children, child_entries, idx = _build_tree(
            sections,
            idx + 1,
            sec.level,
            parent_node_id=node.node_id,
        )
        node.children = node_children
        known_ids |= _collect_ids(node)
        time_entries.extend(child_entries)
        children.append(node)

    return children, time_entries, idx


# ── Priority propagation ────────────────────────────────────────────────


def _propagate_priority(
    node: Node,
    parent_priority: str = "medium",
) -> None:
    """Walk the tree and fill in ``None`` priorities from the parent.

    :param node: Root of the subtree to process.
    :param parent_priority: Priority to inherit when *node.priority* is
        ``None``.
    """
    if node.priority is None:
        node.priority = parent_priority
    for child in node.children:
        _propagate_priority(child, node.priority)


# ── Main entry point ────────────────────────────────────────────────────


def parse_goals_file(filepath: Path) -> list[Node]:
    """Parse a Markdown goals file into a list of top-level :class:`Node`.

    :param filepath: Path to the ``.md`` file.
    :returns: Ordered list of goal nodes with fully resolved children and
        inherited priorities.
    """
    text: str = filepath.read_text(encoding="utf-8")

    fm_match: Optional[re.Match[str]] = re.match(
        r"^---\s*\n.*?\n---\s*\n(.*)",
        text,
        re.DOTALL,
    )
    body: str = fm_match.group(1) if fm_match else text

    sections: list[_Section] = _split_into_sections(body)

    goals: list[Node] = []
    idx: int = 0

    while idx < len(sections):
        sec: _Section = sections[idx]

        if sec.level != 2 or not sec.node_id:
            idx += 1
            continue

        meta: dict[str, Any] = _parse_metadata(sec.body)
        goal: Node = _build_node(sec, meta)

        goal_children: list[Node]
        time_entries: list[TimeEntry]
        goal_children, time_entries, idx = _build_tree(
            sections, idx + 1, 2, parent_node_id=goal.node_id
        )
        goal.children = goal_children
        goal.time_entries = time_entries
        goal.source_file = str(filepath)

        _propagate_priority(goal)
        goals.append(goal)

    return goals
