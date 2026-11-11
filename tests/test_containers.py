# ABOUTME: Tests for markwright._containers.scan_containers, the container pairing scanner.
# Exempt from the public-API-only rule: the scanner has a contract of its own, like _fences and _markers.

from __future__ import annotations

from markwright._containers import scan_containers


class TestPairs:
    def test_a_single_grid_pair_at_column_zero(self) -> None:
        scan = scan_containers("[grid]\n\ntext\n\n[/grid]")

        assert len(scan.pairs) == 1
        pair = scan.pairs[0]
        assert pair.kind == "grid"
        assert pair.tokens == ()
        assert pair.open_line == 0
        assert pair.close_line == 4
        assert pair.indent == ""
        assert scan.problems == ()
        assert scan.unclosed_grids == ()

    def test_grid_tokens_are_the_words_after_grid(self) -> None:
        scan = scan_containers("[grid cards 3]\n\ntext\n\n[/grid]")

        assert scan.pairs[0].tokens == ("cards", "3")

    def test_a_card_pair(self) -> None:
        scan = scan_containers("[card]\n\ntext\n\n[/card]")

        assert scan.pairs[0].kind == "card"
        assert scan.pairs[0].tokens == ()
        assert scan.problems == ()

    def test_a_tab_pair_keeps_the_whole_name_as_one_token(self) -> None:
        scan = scan_containers("[tab Node.js 20]\n\ntext\n\n[/tab]")

        assert scan.pairs[0].kind == "tab"
        assert scan.pairs[0].tokens == ("Node.js 20",)
        assert scan.problems == ()


class TestEmptyTabName:
    def test_a_tab_with_a_blank_name_is_a_problem(self) -> None:
        scan = scan_containers("[tab ]\n\n[/tab]")

        assert scan.pairs == ()
        empty_name_problems = [problem for problem in scan.problems if "empty" in problem.reason]
        assert len(empty_name_problems) == 1
        assert empty_name_problems[0].line == 0

    def test_a_tab_with_no_name_is_not_an_opener(self) -> None:
        scan = scan_containers("[tab]\n\n[/tab]")

        assert scan.pairs == ()
        assert any("empty" in problem.reason for problem in scan.problems)

    def test_a_tab_with_a_whitespace_only_name_is_a_problem(self) -> None:
        scan = scan_containers("[tab  ]\n\n[/tab]")

        assert scan.pairs == ()
        empty_name_problems = [problem for problem in scan.problems if "empty" in problem.reason]
        assert len(empty_name_problems) == 1
        assert empty_name_problems[0].line == 0


class TestNesting:
    def test_nested_same_kind_yields_two_pairs(self) -> None:
        scan = scan_containers("[grid]\n[grid]\n[/grid]\n[/grid]")

        assert len(scan.pairs) == 2
        assert scan.problems == ()
        outer, inner = scan.pairs
        assert outer.open_line == 0
        assert outer.close_line == 3
        assert inner.open_line == 1
        assert inner.close_line == 2

    def test_nested_mixed_kinds_yield_a_grid_and_a_card_pair(self) -> None:
        scan = scan_containers("[grid]\n[card]\n[/card]\n[/grid]")

        assert {pair.kind for pair in scan.pairs} == {"grid", "card"}
        assert scan.problems == ()


class TestIndentationAndMatching:
    def test_a_mismatched_indent_leaves_the_opener_unclosed_and_the_closer_stray(self) -> None:
        scan = scan_containers("[grid]\n    [/grid]")

        assert scan.pairs == ()
        assert scan.unclosed_grids == ()
        reasons = [problem.reason for problem in scan.problems]
        assert any("unclosed" in reason for reason in reasons)
        assert any("no matching" in reason for reason in reasons)

    def test_a_closer_skips_an_unmatched_opener_which_is_unclosed(self) -> None:
        scan = scan_containers("[grid]\n[card]\n[/grid]")

        assert [pair.kind for pair in scan.pairs] == ["grid"]
        card_problems = [problem for problem in scan.problems if "card" in problem.reason]
        assert len(card_problems) == 1
        assert card_problems[0].line == 1

    def test_a_stray_card_closer_is_a_problem(self) -> None:
        scan = scan_containers("[/card]")

        assert scan.pairs == ()
        assert len(scan.problems) == 1
        assert "no matching" in scan.problems[0].reason
        assert "card" in scan.problems[0].reason

    def test_an_unclosed_card_is_a_problem(self) -> None:
        scan = scan_containers("[card]\n\ntext")

        assert scan.pairs == ()
        assert len(scan.problems) == 1
        assert "unclosed" in scan.problems[0].reason
        assert scan.problems[0].line == 0

    def test_an_unclosed_tab_is_a_problem(self) -> None:
        scan = scan_containers("[tab One]\n\ntext")

        assert scan.pairs == ()
        assert len(scan.problems) == 1
        assert "unclosed" in scan.problems[0].reason


class TestCodeSkipping:
    def test_a_directive_inside_a_fenced_block_is_left_literal(self) -> None:
        source = "```\n[grid]\n[/grid]\n```"

        scan = scan_containers(source)

        assert scan.pairs == ()
        assert scan.problems == ()
        assert scan.unclosed_grids == ()

    def test_a_directive_inside_an_indented_code_block_is_left_literal(self) -> None:
        source = "para\n\n    [grid]\n    [/grid]\n"

        scan = scan_containers(source)

        assert scan.pairs == ()
        assert scan.problems == ()
        assert scan.unclosed_grids == ()


class TestUnclosedGrids:
    def test_an_unclosed_grid_is_reported_as_a_shortcut_not_a_problem(self) -> None:
        scan = scan_containers("[grid cards]\n\n- one\n- two")

        assert scan.pairs == ()
        assert scan.problems == ()
        assert len(scan.unclosed_grids) == 1
        shortcut = scan.unclosed_grids[0]
        assert shortcut.line == 0
        assert shortcut.indent == ""
        assert shortcut.tokens == ("cards",)

    def test_a_stray_grid_closer_does_not_demote_a_separate_shortcut(self) -> None:
        source = "[grid cards]\n\n- one\n\n[grid]\n    [/grid]"

        scan = scan_containers(source)

        assert scan.pairs == ()
        assert [grid.line for grid in scan.unclosed_grids] == [0]
        assert scan.unclosed_grids[0].tokens == ("cards",)
        reasons = [problem.reason for problem in scan.problems]
        assert any("unclosed [grid]" in reason for reason in reasons)
        assert any("no matching [grid]" in reason for reason in reasons)

    def test_a_stray_grid_closer_demotes_the_nearest_grid_under_an_open_card(self) -> None:
        source = "[grid]\n[card]\n    [/grid]"

        scan = scan_containers(source)

        assert scan.pairs == ()
        assert scan.unclosed_grids == ()
        reasons = [problem.reason for problem in scan.problems]
        assert any("unclosed [grid]" in reason for reason in reasons)
        assert any("unclosed [card]" in reason for reason in reasons)
        assert any("no matching [grid]" in reason for reason in reasons)

    def test_a_stray_grid_closer_before_a_shortcut_leaves_the_shortcut_alone(self) -> None:
        source = "[/grid]\n\n[grid cards]\n\n- one"

        scan = scan_containers(source)

        assert [grid.line for grid in scan.unclosed_grids] == [2]
        stray_problems = [problem for problem in scan.problems if "no matching [grid]" in problem.reason]
        assert len(stray_problems) == 1
        assert stray_problems[0].line == 0


class TestEnclosedByGrid:
    def test_a_card_directly_inside_a_block_grid_is_enclosed(self) -> None:
        scan = scan_containers("[grid]\n[card]\n\ntext\n\n[/card]\n[/grid]")

        card = next(pair for pair in scan.pairs if pair.kind == "card")
        assert card.enclosed_by_grid is True

    def test_a_card_at_top_level_is_not_enclosed(self) -> None:
        scan = scan_containers("[card]\n\ntext\n\n[/card]")

        assert scan.pairs[0].enclosed_by_grid is False

    def test_a_card_inside_a_tab_is_not_enclosed_by_grid(self) -> None:
        scan = scan_containers("[grid]\n[tab One]\n[card]\n\ntext\n\n[/card]\n[/tab]\n[/grid]")

        card = next(pair for pair in scan.pairs if pair.kind == "card")
        assert card.enclosed_by_grid is False


class TestEdgeCases:
    def test_a_tab_name_containing_a_bracket_does_not_match_the_opener(self) -> None:
        scan = scan_containers("[tab a]b]\n\n[/tab]")

        assert scan.pairs == ()
        empty_name_problems = [problem for problem in scan.problems if "empty" in problem.reason]
        assert empty_name_problems == []
        assert all(problem.text != "[tab a]b]" for problem in scan.problems)

    def test_nesting_inside_a_list_item_pairs_at_the_two_space_indent(self) -> None:
        source = "- item\n\n  [grid]\n\n  content\n\n  [/grid]"

        scan = scan_containers(source)

        assert len(scan.pairs) == 1
        assert scan.pairs[0].kind == "grid"
        assert scan.pairs[0].indent == "  "
        assert scan.problems == ()
