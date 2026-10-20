# ABOUTME: Tests for the shared HTML helpers in markwright._html: matching_end and add_classes.
# These helpers are shared infrastructure with their own contract, so the private module is tested directly.

from __future__ import annotations

from markwright._html import add_classes, matching_end, tokenize


class TestMatchingEnd:
    def test_finds_the_end_tag_of_a_simple_element(self) -> None:
        tokens = tokenize("<ul><li>x</li></ul>")

        assert matching_end(tokens, 0) == len(tokens) - 1

    def test_counts_nesting_to_find_the_outer_end_tag(self) -> None:
        tokens = tokenize("<div><div>x</div></div>")

        assert matching_end(tokens, 0) == 4
        assert matching_end(tokens, 1) == 3

    def test_ignores_other_tag_names_and_self_closing_tags(self) -> None:
        tokens = tokenize("<ul><li>a<br/></li></ul>")

        assert matching_end(tokens, 0) == len(tokens) - 1

    def test_ignores_a_self_closing_tag_of_the_same_name(self) -> None:
        tokens = tokenize("<div><div/>x</div>")

        assert matching_end(tokens, 0) == len(tokens) - 1

    def test_returns_none_when_the_element_is_never_closed(self) -> None:
        tokens = tokenize("<ul><li>x")

        assert matching_end(tokens, 0) is None


class TestAddClasses:
    def test_puts_new_classes_in_front_of_existing_ones(self) -> None:
        tag = tokenize('<ol class="steps">')[0]

        assert add_classes(tag, "new") == '<ol class="new steps">'

    def test_adds_a_class_attribute_when_the_tag_has_none(self) -> None:
        tag = tokenize("<ul>")[0]

        assert add_classes(tag, "new") == '<ul class="new">'

    def test_appends_added_attrs_after_existing_attributes(self) -> None:
        tag = tokenize('<ol class="steps" id="x">')[0]

        result = add_classes(tag, "mw-annotations", (("data-mw-version", "1"),))

        assert result == '<ol class="mw-annotations steps" id="x" data-mw-version="1">'

    def test_appends_added_attrs_when_the_tag_has_no_class(self) -> None:
        tag = tokenize('<ul id="x">')[0]

        result = add_classes(tag, "new", (("data-mw-version", "1"),))

        assert result == '<ul class="new" id="x" data-mw-version="1">'
