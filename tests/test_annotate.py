# ABOUTME: Tests for the annotate extension linking (N) markers in a block to the items of the list after it.
# Covers the source stage, prose and code linking, fail-soft marker skips, and the in-process render.

import markdown

from markwright.annotate import apply_html, expand_source

MARKER = '<!-- mw-annotate:{"version": 1} -->'
PROSE = "<p>Run (1) now (2).</p>"
NOTES = "<ol>\n<li>first</li>\n<li>second</li>\n</ol>"
ONE_NOTE = "<ol>\n<li>only</li>\n</ol>"
LINK_1 = '<a class="mw-annotation" href="#mw-annotation-1-1">1</a>'
LINK_2 = '<a class="mw-annotation" href="#mw-annotation-1-2">2</a>'
PROSE_ANNOTATED = (
    "\n"
    '<p class="mw-annotated">Run '
    + LINK_1
    + " now "
    + LINK_2
    + ".</p>\n"
    + '<ol class="mw-annotations" data-mw-version="1">\n'
    + '<li id="mw-annotation-1-1">first</li>\n'
    + '<li id="mw-annotation-1-2">second</li>\n'
    + "</ol>"
)
BASH_FENCE = "```bash\n./deploy.sh --prod # (1)!\n```"


def render_annotate(source: str) -> str:
    """Render source with superfences, highlight, annotate, and fence loaded."""
    md = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight", "markwright.annotate", "markwright.fence"],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
    )
    return md.convert(source)


class TestExpandSource:
    def test_line_becomes_marker_and_blank_line(self) -> None:
        assert expand_source("[annotate]\nText (1)\n\n1. note") == MARKER + "\n\nText (1)\n\n1. note"

    def test_indent_is_preserved(self) -> None:
        assert expand_source("- item\n\n    [annotate]\n    Text") == f"- item\n\n    {MARKER}\n\n    Text"

    def test_inline_mention_is_unchanged(self) -> None:
        source = "Use [annotate] in prose."
        assert expand_source(source) == source


class TestProse:
    def test_block_list_and_markers_are_annotated(self) -> None:
        assert apply_html(MARKER + "\n" + PROSE + "\n" + NOTES) == PROSE_ANNOTATED

    def test_number_without_an_item_stays_text(self) -> None:
        result = apply_html(MARKER + "\n<p>See (1) and (9).</p>\n" + ONE_NOTE)
        assert "See " + LINK_1 + " and (9)." in result

    def test_zero_stays_text(self) -> None:
        result = apply_html(MARKER + "\n<p>See (0).</p>\n" + ONE_NOTE)
        assert "See (0)." in result

    def test_attribute_and_later_paragraph_are_untouched(self) -> None:
        result = apply_html(MARKER + '\n<p title="(1)">a (1)</p>\n' + ONE_NOTE + "\n<p>later (1)</p>")
        assert '<p class="mw-annotated" title="(1)">a ' + LINK_1 + "</p>" in result
        assert result.endswith("<p>later (1)</p>")

    def test_script_and_style_text_is_untouched(self) -> None:
        block = "<div><script>f(1)</script><style>g(1)</style>h (1)</div>"
        result = apply_html(MARKER + "\n" + block + "\n" + ONE_NOTE)
        assert "<script>f(1)</script><style>g(1)</style>h " + LINK_1 in result

    def test_ids_count_per_page(self) -> None:
        page = f"{MARKER}\n{PROSE}\n{NOTES}\n{MARKER}\n<p>Again (1).</p>\n{ONE_NOTE}"
        result = apply_html(page)
        assert 'id="mw-annotation-2-1"' in result
        assert '<a class="mw-annotation" href="#mw-annotation-2-1">1</a>' in result

    def test_skipped_marker_does_not_use_a_number(self) -> None:
        page = f"{MARKER}\n<p>skipped</p>\n<p>none</p>\n{MARKER}\n<p>Real (1).</p>\n{ONE_NOTE}"
        result = apply_html(page)
        assert 'id="mw-annotation-1-1"' in result

    def test_nested_list_items_are_not_annotations(self) -> None:
        notes = "<ol>\n<li>a<ul>\n<li>inner</li>\n</ul></li>\n<li>b</li>\n</ol>"
        result = apply_html(MARKER + "\n<p>x (2)</p>\n" + notes)
        assert '<li id="mw-annotation-1-1">a<ul>\n<li>inner</li>\n</ul></li>' in result
        assert '<li id="mw-annotation-1-2">b</li>' in result

    def test_existing_classes_follow_the_added_ones(self) -> None:
        result = apply_html(MARKER + '\n<p class="lead">x</p>\n<ol class="steps">\n<li>a</li>\n</ol>')
        assert '<p class="mw-annotated lead">' in result
        assert '<ol class="mw-annotations steps" data-mw-version="1">' in result

    def test_existing_item_attributes_are_kept(self) -> None:
        result = apply_html(MARKER + '\n<p>x</p>\n<ol>\n<li class="k">a</li>\n</ol>')
        assert '<li id="mw-annotation-1-1" class="k">a</li>' in result

    def test_running_twice_is_stable(self) -> None:
        once = apply_html(MARKER + "\n" + PROSE + "\n" + NOTES)
        assert apply_html(once) == once

    def test_nested_same_tag_block_ends_at_its_own_close(self) -> None:
        result = apply_html(MARKER + "\n<div><div>(1)</div> (1)</div>\n" + ONE_NOTE)
        assert result.startswith('\n<div class="mw-annotated"><div>' + LINK_1 + "</div> " + LINK_1 + "</div>")

    def test_bare_pre_block_is_annotated(self) -> None:
        result = apply_html(MARKER + "\n<pre><code>x (1)</code></pre>\n" + ONE_NOTE)
        assert '<pre class="mw-annotated"><code>x ' + LINK_1 + "</code></pre>" in result

    def test_page_without_markers_is_unchanged(self) -> None:
        assert apply_html(PROSE) == PROSE

    def test_empty_page_is_unchanged(self) -> None:
        assert apply_html("") == ""


class TestCode:
    def test_pygments_comment_span_is_replaced_whole(self) -> None:
        code = '<pre><code>run<span class="w"> </span><span class="c1"># (1)!</span>\n</code></pre>'
        result = apply_html(MARKER + "\n" + code + "\n" + ONE_NOTE)
        assert 'run<span class="w"> </span>' + LINK_1 + "\n</code>" in result
        assert "# (1)!" not in result

    def test_chroma_comment_span_keeps_the_line_break(self) -> None:
        code = (
            '<pre class="chroma"><code><span class="line"><span class="cl">x '
            '<span class="c1"># (1)!</span>\n</span></span></code></pre>'
        )
        result = apply_html(MARKER + "\n" + code + "\n" + ONE_NOTE)
        assert '<span class="cl">x ' + LINK_1 + "\n</span></span>" in result

    def test_trailing_newline_inside_the_span_is_kept(self) -> None:
        code = '<pre><code>x <span class="c1"># (1)!\n</span>y</code></pre>'
        result = apply_html(MARKER + "\n" + code + "\n" + ONE_NOTE)
        assert "x " + LINK_1 + "\ny</code>" in result

    def test_two_markers_in_one_comment_collapse_to_the_first_link(self) -> None:
        code = '<pre><code>x <span class="c1"># (1)! (2)</span></code></pre>'
        result = apply_html(MARKER + "\n" + code + "\n" + NOTES)
        assert "x " + LINK_1 + "</code>" in result

    def test_marker_without_a_comment_span_replaces_only_the_marker(self) -> None:
        result = apply_html(MARKER + "\n<pre><code>plain # (1)!</code></pre>\n" + ONE_NOTE)
        assert "plain # " + LINK_1 + "</code>" in result

    def test_marker_in_a_non_comment_span_replaces_only_the_marker(self) -> None:
        result = apply_html(MARKER + '\n<pre><code><span class="s">"(1)!"</span></code></pre>\n' + ONE_NOTE)
        assert '<span class="s">"' + LINK_1 + '"</span>' in result

    def test_marker_without_a_bang_keeps_the_comment_span(self) -> None:
        code = '<pre><code>x <span class="c1"># (1)</span></code></pre>'
        result = apply_html(MARKER + "\n" + code + "\n" + ONE_NOTE)
        assert '<span class="c1"># ' + LINK_1 + "</span>" in result

    def test_comment_span_with_other_text_replaces_only_the_marker(self) -> None:
        code = '<pre><code><span class="c1"># note <b>x</b> (1)!</span></code></pre>'
        result = apply_html(MARKER + "\n" + code + "\n" + ONE_NOTE)
        assert '<span class="c1"># note <b>x</b> ' + LINK_1 + "</span>" in result


class TestSkippedMarkers:
    def test_no_following_block_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html(MARKER + "\ntext only", skip_reasons)
        assert result == "\ntext only"
        assert skip_reasons == ["Skipping mw-annotate marker with no following block"]

    def test_unclosed_block_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html(MARKER + "\n<div>(1)", skip_reasons)
        assert result == "\n<div>(1)"
        assert skip_reasons == ["Skipping mw-annotate marker with no following block"]

    def test_block_then_non_list_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html(MARKER + "\n<p>a (1)</p>\n<p>b</p>", skip_reasons)
        assert result == "\n<p>a (1)</p>\n<p>b</p>"
        assert skip_reasons == ["Skipping mw-annotate marker with no annotation list after the block"]

    def test_block_then_end_of_page_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        apply_html(MARKER + "\n<p>a</p>\n", skip_reasons)
        assert skip_reasons == ["Skipping mw-annotate marker with no annotation list after the block"]

    def test_unordered_list_is_not_an_annotation_list(self) -> None:
        skip_reasons: list[str] = []
        apply_html(MARKER + "\n<p>a</p>\n<ul>\n<li>x</li>\n</ul>", skip_reasons)
        assert skip_reasons == ["Skipping mw-annotate marker with no annotation list after the block"]

    def test_unclosed_list_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        apply_html(MARKER + "\n<p>a</p>\n<ol>\n<li>x</li>", skip_reasons)
        assert skip_reasons == ["Skipping mw-annotate marker with no annotation list after the block"]

    def test_malformed_marker_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html("<!-- mw-annotate:{nope -->\n" + PROSE + "\n" + NOTES, skip_reasons)
        assert result == "\n" + PROSE + "\n" + NOTES
        assert skip_reasons == ["Skipping malformed mw-annotate marker: '{nope'"]

    def test_unsupported_version_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        apply_html('<!-- mw-annotate:{"version": 2} -->\n' + PROSE + "\n" + NOTES, skip_reasons)
        assert skip_reasons == ["Skipping mw-annotate marker with unsupported version 2"]

    def test_skip_reasons_are_optional(self) -> None:
        assert apply_html(MARKER + "\ntext") == "\ntext"


class TestInProcess:
    def test_paragraph_is_annotated(self) -> None:
        result = render_annotate("[annotate]\n\nRun (1) now (2).\n\n1. first\n2. second")
        assert result == PROSE_ANNOTATED.removeprefix("\n")

    def test_labeled_fence_is_annotated_and_labeled(self) -> None:
        source = "[annotate]\n\n```bash\n[label deploy.sh]\n./deploy.sh --prod # (1)!\n```\n\n1. Deploys."
        result = render_annotate(source)
        assert '<div class="mw-annotated language-bash highlight">' in result
        assert '--prod<span class="w"> </span>' + LINK_1 + "\n</code>" in result
        assert "deploy.sh</div>" in result
        assert 'id="mw-annotation-1-1"' in result
        assert "mw-fence" not in result

    def test_pygments_comment_keeps_the_line_break(self) -> None:
        result = render_annotate("[annotate]\n\n" + BASH_FENCE + "\n\n1. Deploys.")
        assert '--prod<span class="w"> </span>' + LINK_1 + "\n</code>" in result

    def test_marker_without_a_list_is_consumed(self) -> None:
        assert render_annotate("[annotate]\n\ntext") == "<p>text</p>"
