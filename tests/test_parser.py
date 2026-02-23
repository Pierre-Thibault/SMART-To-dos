"""Tests for :mod:`app.parser`."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.parser import (
    Node,
    SmartCriteria,
    TimeEntry,
    TrackingConfig,
    _build_node,
    _clean_depends,
    _clean_priority,
    _clean_status,
    _extract_value_unit,
    _parse_actual,
    _parse_date,
    _parse_metadata,
    _parse_smart,
    _parse_time_entries,
    _parse_tracking,
    _propagate_priority,
    _Section,
    _split_into_sections,
    parse_goals_file,
)

# ── _extract_value_unit ──────────────────────────────────────────────────


class TestExtractValueUnit:
    def test_none(self) -> None:
        assert _extract_value_unit(None) == (None, "")

    def test_empty_string(self) -> None:
        assert _extract_value_unit("") == (None, "")

    def test_integer_with_unit(self) -> None:
        assert _extract_value_unit("84 pages") == (84.0, "pages")

    def test_float_with_unit(self) -> None:
        assert _extract_value_unit("21.5 minutes") == (21.5, "minutes")

    def test_percentage(self) -> None:
        assert _extract_value_unit("55%") == (55.0, "%")

    def test_number_only(self) -> None:
        assert _extract_value_unit("42") == (42.0, "")

    def test_non_numeric(self) -> None:
        assert _extract_value_unit("hello") == (None, "")

    def test_numeric_value_passed_as_int(self) -> None:
        assert _extract_value_unit(84) == (84.0, "")


# ── _parse_date ──────────────────────────────────────────────────────────


class TestParseDate:
    def test_none(self) -> None:
        assert _parse_date(None) is None

    def test_valid_string(self) -> None:
        assert _parse_date("2026-02-15") == date(2026, 2, 15)

    def test_date_passthrough(self) -> None:
        d: date = date(2026, 1, 1)
        assert _parse_date(d) is d

    def test_invalid_string(self) -> None:
        assert _parse_date("not-a-date") is None

    def test_date_from_yaml_int(self) -> None:
        # YAML sometimes parses bare dates as date objects
        assert _parse_date(date(2026, 3, 1)) == date(2026, 3, 1)


# ── _clean_depends ───────────────────────────────────────────────────────


class TestCleanDepends:
    def test_none(self) -> None:
        assert _clean_depends(None) == []

    def test_null_string(self) -> None:
        assert _clean_depends("null") == []

    def test_empty_string(self) -> None:
        assert _clean_depends("") == []

    def test_single_value(self) -> None:
        assert _clean_depends("task-01") == ["task-01"]

    def test_list_value(self) -> None:
        assert _clean_depends(["a", "b"]) == ["a", "b"]

    def test_list_with_nulls(self) -> None:
        assert _clean_depends(["a", None, "null"]) == ["a"]


# ── _clean_priority ──────────────────────────────────────────────────────


class TestCleanPriority:
    def test_none(self) -> None:
        assert _clean_priority(None) is None

    def test_valid(self) -> None:
        assert _clean_priority("high") == "high"

    def test_invalid(self) -> None:
        assert _clean_priority("urgent") is None

    def test_all_valid_values(self) -> None:
        for p in ("optional", "low", "medium", "high", "capital"):
            assert _clean_priority(p) == p


# ── _clean_status ────────────────────────────────────────────────────────


class TestCleanStatus:
    def test_none(self) -> None:
        assert _clean_status(None) == "not_started"

    def test_valid(self) -> None:
        assert _clean_status("done") == "done"

    def test_invalid(self) -> None:
        assert _clean_status("unknown") == "not_started"

    def test_all_valid_values(self) -> None:
        for s in ("not_started", "in_progress", "done", "paused", "cancelled"):
            assert _clean_status(s) == s


# ── _parse_tracking ──────────────────────────────────────────────────────


class TestParseTracking:
    def test_empty(self) -> None:
        tc: TrackingConfig = _parse_tracking({})
        assert tc.mode == "cumulative"
        assert tc.target is None

    def test_nested_dict(self) -> None:
        data = {"tracking": {"target": "84 pages", "mode": "cumulative"}}
        tc: TrackingConfig = _parse_tracking(data)
        assert tc.target == 84.0
        assert tc.unit == "pages"

    def test_list_format(self) -> None:
        data = {"tracking": [{"target": "60 jours"}]}
        tc: TrackingConfig = _parse_tracking(data)
        assert tc.target == 60.0
        assert tc.unit == "jours"

    def test_root_level_fallback(self) -> None:
        data = {"tracking": None, "target": "100%"}
        tc: TrackingConfig = _parse_tracking(data)
        assert tc.target == 100.0
        assert tc.unit == "%"

    def test_invalid_raw_type(self) -> None:
        tc: TrackingConfig = _parse_tracking({"tracking": "garbage"})
        assert tc.target is None


# ── _parse_actual ────────────────────────────────────────────────────────


class TestParseActual:
    def test_absent(self) -> None:
        tc = TrackingConfig()
        val, tc2 = _parse_actual({}, tc)
        assert val == 0.0
        assert tc2 is tc

    def test_with_unit_inherits(self) -> None:
        tc = TrackingConfig(target=100.0)
        val, tc2 = _parse_actual({"actual": "55 pages"}, tc)
        assert val == 55.0
        assert tc2.unit == "pages"

    def test_invalid(self) -> None:
        tc = TrackingConfig()
        val, tc2 = _parse_actual({"actual": "abc"}, tc)
        assert val == 0.0


# ── _parse_smart ─────────────────────────────────────────────────────────


class TestParseSmart:
    def test_absent(self) -> None:
        assert _parse_smart({}) is None

    def test_valid(self) -> None:
        data = {
            "smart": {
                "specific": "Learn X",
                "measurable": "Complete course",
                "actionable": "Daily practice",
                "relevant": "Career",
                "time_bound": "2026-06-01",
            }
        }
        sc = _parse_smart(data)
        assert sc is not None
        assert sc.specific == "Learn X"
        assert sc.time_bound == "2026-06-01"

    def test_mesurable_typo(self) -> None:
        data = {"smart": {"mesurable": "Finish it"}}
        sc = _parse_smart(data)
        assert sc is not None
        assert sc.measurable == "Finish it"

    def test_non_dict(self) -> None:
        assert _parse_smart({"smart": "not a dict"}) is None


# ── _parse_metadata ──────────────────────────────────────────────────────


class TestParseMetadata:
    def test_empty_body(self) -> None:
        assert _parse_metadata("") == {}

    def test_yaml_list(self) -> None:
        body = "- status: done\n- priority: high\n"
        meta = _parse_metadata(body)
        assert meta["status"] == "done"
        assert meta["priority"] == "high"

    def test_free_text_stops_parsing(self) -> None:
        body = "- status: done\n\nSome free text here."
        meta = _parse_metadata(body)
        assert meta["status"] == "done"

    def test_yaml_continuation_after_blank(self) -> None:
        body = "- tracking:\n    target: 84 pages\n\n- status: done\n"
        meta = _parse_metadata(body)
        assert "tracking" in meta

    def test_non_yaml_body(self) -> None:
        body = "Just plain text, no YAML here."
        assert _parse_metadata(body) == {}


# ── _parse_time_entries ──────────────────────────────────────────────────


class TestParseTimeEntries:
    def test_valid_table(self) -> None:
        text = (
            "| Date       | Tâche     | Valeur     | Notes |\n"
            "|------------|-----------|------------|-------|\n"
            "| 2026-02-15 | task-01   | 70 minutes |       |\n"
            "| 2026-02-16 | task-02   | 17 pages   | Ch. 1 |\n"
        )
        entries = _parse_time_entries(text)
        assert len(entries) == 2
        assert entries[0].node_id == "task-01"
        assert entries[0].quantity == 70.0
        assert entries[1].notes == "Ch. 1"

    def test_header_row_skipped(self) -> None:
        text = (
            "| Date | Tâche | Valeur | Notes |\n"
            "|------|-------|--------|-------|\n"
            "| 2026-01-01 | x | 10 pages | |\n"
        )
        entries = _parse_time_entries(text)
        assert len(entries) == 1

    def test_invalid_date_skipped(self) -> None:
        text = "| bad-date | x | 10 pages | |\n"
        entries = _parse_time_entries(text)
        assert len(entries) == 0

    def test_invalid_quantity_skipped(self) -> None:
        text = "| 2026-01-01 | x | abc | |\n"
        entries = _parse_time_entries(text)
        assert len(entries) == 0

    def test_too_few_columns_skipped(self) -> None:
        text = "| 2026-01-01 | x |\n"
        entries = _parse_time_entries(text)
        assert len(entries) == 0

    # ── Short format (leaf-level journal) ────────────────────────────

    def test_short_format_with_header(self) -> None:
        """Leaf journal: | Date | Valeur | Notes | (no Tâche column)."""
        text = (
            "| Date       | Valeur     | Notes |\n"
            "|------------|------------|-------|\n"
            "| 2026-02-15 | 20 pages   |       |\n"
            "| 2026-02-16 | 15 pages   | Ch. 2 |\n"
        )
        entries = _parse_time_entries(text, default_node_id="leaf-01")
        assert len(entries) == 2
        assert entries[0].node_id == "leaf-01"
        assert entries[0].quantity == 20.0
        assert entries[1].notes == "Ch. 2"

    def test_short_format_two_columns(self) -> None:
        """Minimal leaf journal: | Date | Valeur |."""
        text = (
            "| Date       | Valeur     |\n"
            "|------------|------------|\n"
            "| 2026-01-10 | 30 minutes |\n"
        )
        entries = _parse_time_entries(text, default_node_id="run")
        assert len(entries) == 1
        assert entries[0].node_id == "run"
        assert entries[0].quantity == 30.0
        assert entries[0].notes == ""

    def test_short_format_no_header(self) -> None:
        """Auto-detect short format from column count + default_node_id."""
        text = "| 2026-03-01 | 5 km | Morning run |\n"
        entries = _parse_time_entries(text, default_node_id="jog")
        assert len(entries) == 1
        assert entries[0].node_id == "jog"
        assert entries[0].quantity == 5.0

    def test_short_format_invalid_date_skipped(self) -> None:
        text = (
            "| Date       | Valeur |\n"
            "|------------|--------|\n"
            "| not-a-date | 10     |\n"
        )
        entries = _parse_time_entries(text, default_node_id="x")
        assert len(entries) == 0

    def test_short_format_invalid_quantity_skipped(self) -> None:
        text = (
            "| Date       | Valeur |\n"
            "|------------|--------|\n"
            "| 2026-01-01 | abc    |\n"
        )
        entries = _parse_time_entries(text, default_node_id="x")
        assert len(entries) == 0

    def test_short_format_too_few_columns(self) -> None:
        text = (
            "| Date       | Valeur |\n" "|------------|--------|\n" "| 2026-01-01 |\n"
        )
        entries = _parse_time_entries(text, default_node_id="x")
        assert len(entries) == 0

    def test_full_format_with_empty_task_uses_default(self) -> None:
        """Full format with empty task column → falls back to default."""
        text = (
            "| Date       | Tâche | Valeur   | Notes |\n"
            "|------------|-------|----------|-------|\n"
            "| 2026-01-01 |       | 10 pages |       |\n"
        )
        entries = _parse_time_entries(text, default_node_id="fallback")
        assert len(entries) == 1
        assert entries[0].node_id == "fallback"

    def test_english_header_detected(self) -> None:
        """Header with 'Task' and 'Value' (English) is detected as full."""
        text = (
            "| Date       | Task   | Value    | Notes |\n"
            "|------------|--------|----------|-------|\n"
            "| 2026-01-01 | abc    | 5 pages  |       |\n"
        )
        entries = _parse_time_entries(text)
        assert len(entries) == 1
        assert entries[0].node_id == "abc"

    def test_english_short_header_detected(self) -> None:
        """Header with 'Value' but no 'Task' → short format."""
        text = (
            "| Date       | Value  | Notes |\n"
            "|------------|--------|-------|\n"
            "| 2026-01-01 | 5 km   |       |\n"
        )
        entries = _parse_time_entries(text, default_node_id="run")
        assert len(entries) == 1
        assert entries[0].node_id == "run"

    def test_no_default_no_header_uses_full(self) -> None:
        """Without default_node_id and no header, 3+ cols → full format."""
        text = "| 2026-01-01 | task-x | 10 pages | |\n"
        entries = _parse_time_entries(text)
        assert len(entries) == 1
        assert entries[0].node_id == "task-x"


# ── _split_into_sections ─────────────────────────────────────────────────


class TestSplitIntoSections:
    def test_basic(self) -> None:
        text = "## foo : Foo Title\n\n- status: done\n\n## bar : Bar Title\n"
        sections = _split_into_sections(text)
        assert len(sections) == 2
        assert sections[0].node_id == "foo"
        assert sections[1].title == "Bar Title"

    def test_journal_heading(self) -> None:
        text = "## g : Goal\n\n### Journal de temps\n\n| ... |"
        sections = _split_into_sections(text)
        assert sections[1].is_journal is True

    def test_heading_without_id(self) -> None:
        text = "## Just a title\n\nText."
        sections = _split_into_sections(text)
        assert sections[0].node_id == ""
        assert sections[0].title == "Just a title"

    def test_nested_levels(self) -> None:
        text = "## a : A\n\n### b : B\n\n#### c : C\n"
        sections = _split_into_sections(text)
        assert [s.level for s in sections] == [2, 3, 4]


# ── Node.find_node ───────────────────────────────────────────────────────


class TestNodeFindNode:
    def test_find_self(self, leaf_node: Node) -> None:
        assert leaf_node.find_node("task-01") is leaf_node

    def test_find_child(self, parent_node: Node) -> None:
        found = parent_node.find_node("sub-02")
        assert found is not None
        assert found.node_id == "sub-02"

    def test_not_found(self, leaf_node: Node) -> None:
        assert leaf_node.find_node("nope") is None


# ── _propagate_priority ──────────────────────────────────────────────────


class TestPropagatePriority:
    def test_inherits_from_parent(self) -> None:
        parent = Node(
            node_id="p",
            title="Parent",
            priority="high",
            children=[
                Node(node_id="c1", title="Child1"),
                Node(node_id="c2", title="Child2", priority="low"),
            ],
        )
        _propagate_priority(parent)
        assert parent.children[0].priority == "high"
        assert parent.children[1].priority == "low"  # kept explicit

    def test_defaults_to_medium(self) -> None:
        node = Node(node_id="x", title="X")
        _propagate_priority(node)
        assert node.priority == "medium"

    def test_deep_inheritance(self) -> None:
        root = Node(
            node_id="r",
            title="Root",
            priority="capital",
            children=[
                Node(
                    node_id="a",
                    title="A",
                    children=[Node(node_id="b", title="B")],
                )
            ],
        )
        _propagate_priority(root)
        assert root.children[0].priority == "capital"
        assert root.children[0].children[0].priority == "capital"


# ── _build_node ──────────────────────────────────────────────────────────


class TestBuildNode:
    def test_basic(self) -> None:
        sec = _Section(
            level=2, raw_heading="t : Title", node_id="t", title="Title", body=""
        )
        node = _build_node(sec, {"status": "in_progress", "priority": "high"})
        assert node.node_id == "t"
        assert node.status == "in_progress"
        assert node.priority == "high"

    def test_fixed_end(self) -> None:
        sec = _Section(level=3, raw_heading="x : X", node_id="x", title="X", body="")
        node = _build_node(sec, {"start": "2026-01-01", "end": "2026-04-01!"})
        assert node.fixed_end is True
        assert node.end == date(2026, 4, 1)

    def test_tags(self) -> None:
        sec = _Section(level=2, raw_heading="x : X", node_id="x", title="X", body="")
        node = _build_node(sec, {"tags": ["pro", "learning"]})
        assert node.tags == ["pro", "learning"]

    def test_tags_non_list(self) -> None:
        sec = _Section(level=2, raw_heading="x : X", node_id="x", title="X", body="")
        node = _build_node(sec, {"tags": "not-a-list"})
        assert node.tags == []


# ── parse_goals_file (integration) ───────────────────────────────────────


class TestParseGoalsFile:
    def test_basic_file(self, tmp_md) -> None:
        p = tmp_md("""
        ---
        title: Test
        ---
        ## a : Alpha

        - status: in_progress
        - priority: high

        ### a1 : Sub Alpha

        - tracking:
            target: 100 pages
        """)
        goals = parse_goals_file(p)
        assert len(goals) == 1
        assert goals[0].node_id == "a"
        assert goals[0].priority == "high"
        assert len(goals[0].children) == 1
        assert goals[0].children[0].priority == "high"  # inherited

    def test_journal_parsed(self, tmp_md) -> None:
        p = tmp_md("""
        ## g : Goal

        - status: in_progress

        ### t : Task

        - tracking:
            target: 50 pages

        ### Journal de temps

        | Date       | Tâche | Valeur   | Notes |
        |------------|-------|----------|-------|
        | 2026-01-10 | t     | 20 pages |       |
        """)
        goals = parse_goals_file(p)
        assert len(goals[0].time_entries) == 1
        assert goals[0].time_entries[0].quantity == 20.0

    def test_no_frontmatter(self, tmp_md) -> None:
        p = tmp_md("## x : Hello\n\n- status: done\n")
        goals = parse_goals_file(p)
        assert len(goals) == 1
        assert goals[0].status == "done"

    def test_open_type(self, tmp_md) -> None:
        p = tmp_md("## o : Open goal\n\n- type: open\n")
        goals = parse_goals_file(p)
        assert goals[0].node_type == "open"

    def test_heading_without_id_skipped(self, tmp_md) -> None:
        p = tmp_md("""
        ## a : Real goal

        - status: done

        ## Just a Title

        Some text.

        ## b : Another goal
        """)
        goals = parse_goals_file(p)
        assert [g.node_id for g in goals] == ["a", "b"]

    def test_deep_nesting(self, tmp_md) -> None:
        p = tmp_md("""
        ## root : Root

        ### child : Child

        #### grandchild : Grandchild

        - tracking:
            target: 10 pages
        """)
        goals = parse_goals_file(p)
        assert len(goals) == 1
        assert len(goals[0].children) == 1
        assert len(goals[0].children[0].children) == 1
        gc = goals[0].children[0].children[0]
        assert gc.node_id == "grandchild"

    def test_multiple_goals(self, tmp_md) -> None:
        p = tmp_md("""
        ## a : First

        - priority: high

        ## b : Second

        - priority: low
        """)
        goals = parse_goals_file(p)
        assert len(goals) == 2
        assert goals[0].priority == "high"
        assert goals[1].priority == "low"

    def test_leaf_level_journal_short_format(self, tmp_md) -> None:
        """Journal directly under a leaf node with short format."""
        p = tmp_md("""
        ## g : Goal

        ### t : Task

        - tracking:
            target: 100 pages

        #### Journal de temps

        | Date       | Valeur   | Notes |
        |------------|----------|-------|
        | 2026-01-10 | 20 pages |       |
        | 2026-01-15 | 30 pages | Ch. 2 |
        """)
        goals = parse_goals_file(p)
        entries = goals[0].time_entries
        assert len(entries) == 2
        assert entries[0].node_id == "t"
        assert entries[0].quantity == 20.0
        assert entries[1].node_id == "t"
        assert entries[1].notes == "Ch. 2"

    def test_leaf_level_journal_two_columns(self, tmp_md) -> None:
        """Minimal leaf journal: | Date | Valeur |."""
        p = tmp_md("""
        ## g : Goal

        ### run : Running

        - tracking:
            mode: performance
            target: 60 minutes

        #### Journal de temps

        | Date       | Valeur     |
        |------------|------------|
        | 2026-01-10 | 12 minutes |
        | 2026-01-13 | 15 minutes |
        """)
        goals = parse_goals_file(p)
        entries = goals[0].time_entries
        assert len(entries) == 2
        assert all(e.node_id == "run" for e in entries)
        assert entries[0].quantity == 12.0

    def test_goal_level_journal_still_works(self, tmp_md) -> None:
        """Goal-level journal with full format alongside leaf journals."""
        p = tmp_md("""
        ## g : Goal

        ### a : Task A

        - tracking:
            target: 50 pages

        #### Journal de temps

        | Date       | Valeur   |
        |------------|----------|
        | 2026-01-10 | 10 pages |

        ### b : Task B

        - tracking:
            target: 80 pages

        ### Journal de temps

        | Date       | Tâche | Valeur   | Notes |
        |------------|-------|----------|-------|
        | 2026-01-12 | b     | 20 pages |       |
        """)
        goals = parse_goals_file(p)
        entries = goals[0].time_entries
        assert len(entries) == 2
        a_entries = [e for e in entries if e.node_id == "a"]
        b_entries = [e for e in entries if e.node_id == "b"]
        assert len(a_entries) == 1
        assert len(b_entries) == 1

    def test_leaf_journal_no_header(self, tmp_md) -> None:
        """Leaf journal without header row auto-detects short format."""
        p = tmp_md("""
        ## g : Goal

        ### t : Task

        - tracking:
            target: 50 pages

        #### Journal de temps

        | 2026-02-01 | 25 pages | Half done |
        """)
        goals = parse_goals_file(p)
        entries = goals[0].time_entries
        assert len(entries) == 1
        assert entries[0].node_id == "t"
        assert entries[0].quantity == 25.0
        assert entries[0].notes == "Half done"

    def test_journal_at_intermediate_level(self, tmp_md) -> None:
        """Journal under a non-leaf node with full format."""
        p = tmp_md("""
        ## g : Goal

        ### parent : Parent

        #### child-a : Child A

        - tracking:
            target: 50 pages

        #### child-b : Child B

        - tracking:
            target: 30 pages

        #### Journal de temps

        | Date       | Tâche   | Valeur   | Notes |
        |------------|---------|----------|-------|
        | 2026-01-10 | child-a | 10 pages |       |
        | 2026-01-15 | child-b | 5 pages  |       |
        """)
        goals = parse_goals_file(p)
        entries = goals[0].time_entries
        assert len(entries) == 2
        assert entries[0].node_id == "child-a"
        assert entries[1].node_id == "child-b"

    def test_journal_references_deep_descendant(self, tmp_md) -> None:
        """Journal at ### level can reference a ##### grandchild."""
        p = tmp_md("""
        ## g : Goal

        ### parent : Parent

        #### child : Child

        ##### gc : Grandchild

        - tracking:
            target: 100 pages

        ### Journal de temps

        | Date       | Tâche | Valeur   | Notes |
        |------------|-------|----------|-------|
        | 2026-01-10 | gc    | 20 pages |       |
        """)
        goals = parse_goals_file(p)
        entries = goals[0].time_entries
        assert len(entries) == 1
        assert entries[0].node_id == "gc"

    def test_journal_unknown_id_dropped(self, tmp_md) -> None:
        """Entries referencing unknown ids are silently dropped."""
        p = tmp_md("""
        ## g : Goal

        ### a : Task A

        - tracking:
            target: 50 pages

        ### Journal de temps

        | Date       | Tâche   | Valeur   | Notes |
        |------------|---------|----------|-------|
        | 2026-01-10 | a       | 10 pages |       |
        | 2026-01-11 | unknown | 5 pages  |       |
        """)
        goals = parse_goals_file(p)
        entries = goals[0].time_entries
        assert len(entries) == 1
        assert entries[0].node_id == "a"

    def test_journal_id_must_be_defined_before(self, tmp_md) -> None:
        """Journal before its target node → entry is dropped."""
        p = tmp_md("""
        ## g : Goal

        ### Journal de temps

        | Date       | Tâche | Valeur   | Notes |
        |------------|-------|----------|-------|
        | 2026-01-10 | later | 10 pages |       |

        ### later : Later Task

        - tracking:
            target: 50 pages
        """)
        goals = parse_goals_file(p)
        entries = goals[0].time_entries
        assert len(entries) == 0

    def test_journal_non_leaf_short_format_ignored(self, tmp_md) -> None:
        """Short format under a non-leaf yields no default_node_id."""
        p = tmp_md("""
        ## g : Goal

        ### a : Task A

        - tracking:
            target: 50 pages

        ### b : Task B

        - tracking:
            target: 30 pages

        ### Journal de temps

        | Date       | Valeur   | Notes |
        |------------|----------|-------|
        | 2026-01-10 | 10 pages |       |
        """)
        goals = parse_goals_file(p)
        # Short format without default → entries have empty node_id
        # which is not in known_ids → dropped
        entries = goals[0].time_entries
        assert len(entries) == 0

    def test_journal_parent_id_valid_for_leaf_goal(self, tmp_md) -> None:
        """Goal without children can have a leaf-level journal."""
        p = tmp_md("""
        ## run : Running

        - tracking:
            mode: performance
            target: 60 minutes

        ### Journal de temps

        | Date       | Valeur     |
        |------------|------------|
        | 2026-01-10 | 12 minutes |
        """)
        goals = parse_goals_file(p)
        entries = goals[0].time_entries
        assert len(entries) == 1
        assert entries[0].node_id == "run"

    def test_multiple_journals_at_different_levels(self, tmp_md) -> None:
        """Journals at leaf and parent levels in the same goal."""
        p = tmp_md("""
        ## g : Goal

        ### a : Task A

        - tracking:
            target: 100 pages

        #### Journal de temps

        | Date       | Valeur   |
        |------------|----------|
        | 2026-01-05 | 10 pages |

        ### b : Task B

        - tracking:
            target: 80 pages

        #### Journal de temps

        | Date       | Valeur   |
        |------------|----------|
        | 2026-01-06 | 20 pages |

        ### Journal de temps

        | Date       | Tâche | Valeur   | Notes |
        |------------|-------|----------|-------|
        | 2026-01-10 | a     | 15 pages |       |
        | 2026-01-11 | b     | 25 pages |       |
        """)
        goals = parse_goals_file(p)
        entries = goals[0].time_entries
        a_entries = [e for e in entries if e.node_id == "a"]
        b_entries = [e for e in entries if e.node_id == "b"]
        assert len(a_entries) == 2  # leaf + goal-level
        assert len(b_entries) == 2  # leaf + goal-level
