# ABOUTME: Tests for the icons extension.
# Validates shortcode resolution, code skipping, option validation, and the in-process render.

from __future__ import annotations

from pathlib import Path

import markdown
import pytest

from markwright import ConfigError, ConfigWarning, OptionError, config_from_mapping
from markwright.icons import IconsExtension, expand_source
from markwright.registry import run_pre

ROCKET = '<svg viewBox="0 0 16 16"><path d="M1 1"/></svg>'
ARROW_UP = '<svg viewBox="0 0 24 24"> <path d="m5 12 7-7"/> </svg>'


@pytest.fixture
def packs(tmp_path: Path) -> dict[str, str]:
    """Write two icon packs under a temp directory and return the packs table.

    :param tmp_path: Pytest's temporary directory.
    :returns: Pack prefix to directory path, as a config table holds it.
    """
    octicons_dir = tmp_path / "octicons"
    octicons_dir.mkdir()
    (octicons_dir / "rocket-16.svg").write_text(ROCKET + "\n", encoding="utf-8")

    nested_dir = tmp_path / "lucide" / "arrows"
    nested_dir.mkdir(parents=True)
    (nested_dir / "up.svg").write_text(
        '<?xml version="1.0"?>\n<!-- license -->\n<svg viewBox="0 0 24 24">\n  <path d="m5 12 7-7"/>\n</svg>\n',
        encoding="utf-8",
    )
    return {"octicons": str(octicons_dir), "lucide": str(tmp_path / "lucide")}


def render_icons(source: str, packs: dict[str, str] | None = None) -> str:
    """Render Markdown source with the icons extension loaded.

    :param source: Markdown source text.
    :param packs: The packs table, or ``None`` to leave the option omitted.
    :returns: Rendered HTML string.
    """
    extension_configs = {"markwright.icons": {"packs": packs}} if packs is not None else {}
    return markdown.Markdown(extensions=["markwright.icons"], extension_configs=extension_configs).convert(source)


class TestIconsExpandSource:
    """Tests for the pre-stage conversion."""

    def test_flat_icon_is_wrapped(self, packs: dict[str, str]) -> None:
        result = expand_source("Launch :octicons-rocket-16: now", {"packs": packs})
        assert result == f'Launch <span aria-hidden="true" class="mw-icon">{ROCKET}</span> now'

    def test_nested_path_joins_with_dash_and_svg_is_one_line(self, packs: dict[str, str]) -> None:
        result = expand_source(":lucide-arrows-up:", {"packs": packs})
        assert result == f'<span aria-hidden="true" class="mw-icon">{ARROW_UP}</span>'
        assert "<?xml" not in result
        assert "\n" not in result

    def test_unknown_pack_stays_literal(self, packs: dict[str, str]) -> None:
        source = "at :material-rocket: and 10:30-11:00: sharp"
        assert expand_source(source, {"packs": packs}) == source

    def test_unknown_name_stays_literal(self, packs: dict[str, str]) -> None:
        assert expand_source(":octicons-missing-16:", {"packs": packs}) == ":octicons-missing-16:"

    def test_inline_code_and_fenced_block_are_untouched(self, packs: dict[str, str]) -> None:
        source = "Use `:octicons-rocket-16:` here\n\n```text\n:octicons-rocket-16:\n```"
        assert expand_source(source, {"packs": packs}) == source

    def test_html_attribute_stays_literal_and_trailing_shortcode_is_wrapped(self, packs: dict[str, str]) -> None:
        source = '<span title=":octicons-rocket-16:">x</span> :octicons-rocket-16:'
        result = expand_source(source, {"packs": packs})
        icon = f'<span aria-hidden="true" class="mw-icon">{ROCKET}</span>'
        assert result == f'<span title=":octicons-rocket-16:">x</span> {icon}'

    def test_longest_prefix_wins(self, tmp_path: Path) -> None:
        short_dir = tmp_path / "short"
        short_dir.mkdir()
        (short_dir / "b-x.svg").write_text("<svg>short</svg>", encoding="utf-8")
        long_dir = tmp_path / "long"
        long_dir.mkdir()
        (long_dir / "x.svg").write_text("<svg>long</svg>", encoding="utf-8")
        result = expand_source(":a-b-x:", {"packs": {"a": str(short_dir), "a-b": str(long_dir)}})
        assert "<svg>long</svg>" in result

    def test_no_packs_passes_text_through_silently(self, recwarn: pytest.WarningsRecorder) -> None:
        source = ":octicons-rocket-16:"
        assert expand_source(source) == source
        assert expand_source(source, {"packs": None}) == source
        assert not recwarn.list

    def test_empty_packs_warns_and_passes_text_through(self) -> None:
        source = ":octicons-rocket-16:"
        with pytest.warns(ConfigWarning, match="'packs' is empty"):
            assert expand_source(source, {"packs": {}}) == source


class TestIconsStageOrder:
    """In ``mw pre`` the icons stage runs after the directive stages, so a directive line is read before an icon."""

    @staticmethod
    def pipeline_pre(source: str, names: list[str], packs: dict[str, str]) -> str:
        """Run the selected pre stages with the icons table configured.

        :param source: Markdown source text.
        :param names: Selected extension names.
        :param packs: The packs table.
        :returns: The source after every selected pre stage.
        """
        return run_pre(source, names, {"icons": {"packs": packs}})

    def test_button_text_keeps_its_directive_and_gets_the_icon(self, packs: dict[str, str]) -> None:
        result = self.pipeline_pre("[button https://x.test :octicons-rocket-16: Go]", ["button", "icons"], packs)
        assert result.startswith('<a class="mw-button"')
        assert f'<span aria-hidden="true" class="mw-icon">{ROCKET}</span> Go</a>' in result

    def test_button_directive_equals_in_process_text(self, packs: dict[str, str]) -> None:
        source = "[button https://x.test :octicons-rocket-16: Go]"
        names = ["button", "icons"]
        in_process = markdown.Markdown(
            extensions=["markwright.button", "markwright.icons"],
            extension_configs={"markwright.icons": {"packs": packs}},
        ).convert(source)
        pipeline = markdown.Markdown().convert(self.pipeline_pre(source, names, packs))
        assert pipeline == in_process

    def test_tab_name_stays_literal_in_the_marker(self, packs: dict[str, str]) -> None:
        source = "[tab :octicons-rocket-16: One]\nbody\n[/tab]\n"
        result = self.pipeline_pre(source, ["tabs", "icons"], packs)
        assert "<svg" not in result
        assert ":octicons-rocket-16:" in result

    def test_embed_line_with_a_shortcode_matches_in_process(self, packs: dict[str, str]) -> None:
        source = "[youtube dQw4w9WgXcQ :octicons-rocket-16:]"
        in_process = markdown.Markdown(
            extensions=["markwright.youtube", "markwright.icons"],
            extension_configs={"markwright.icons": {"packs": packs}},
        ).convert(source)
        pipeline = markdown.Markdown().convert(self.pipeline_pre(source, ["youtube", "icons"], packs))
        assert pipeline == in_process

    def test_embed_line_without_a_shortcode_is_still_expanded(self, packs: dict[str, str]) -> None:
        result = self.pipeline_pre("[youtube dQw4w9WgXcQ]\n\n:octicons-rocket-16:", ["youtube", "icons"], packs)
        assert "<iframe" in result
        assert result.count("<svg") == 1

    def test_converted_mermaid_diagram_keeps_its_shortcode(self, packs: dict[str, str]) -> None:
        source = "```mermaid\ngraph LR\n  A[:octicons-rocket-16:] --> B\n```\n\nAfter :octicons-rocket-16:\n"
        result = self.pipeline_pre(source, ["mermaid", "icons"], packs)
        assert '<pre class="mermaid">graph LR\n  A[:octicons-rocket-16:] --&gt; B\n</pre>' in result
        assert result.count("<svg") == 1

    def test_mermaid_diagram_keeps_its_shortcode_in_a_list_item(self, packs: dict[str, str]) -> None:
        source = "- item\n\n    ```mermaid\n    graph LR\n      A[:octicons-rocket-16:]\n    ```\n"
        result = self.pipeline_pre(source, ["mermaid", "icons"], packs)
        assert "<svg" not in result
        assert "A[:octicons-rocket-16:]" in result

    @pytest.mark.parametrize(
        "source",
        [
            "```mermaid\ngraph LR\n\n    A[:octicons-rocket-16:]\n  B[:octicons-rocket-16:]\n```\n",
            "~~~mermaid\ngraph LR\n```\n  A[:octicons-rocket-16:]\n```\n  B[:octicons-rocket-16:]\n~~~\n",
        ],
        ids=["line-indented-like-code", "backtick-fence-in-the-text"],
    )
    def test_diagram_text_that_reads_as_code_keeps_its_shortcodes(self, packs: dict[str, str], source: str) -> None:
        result = self.pipeline_pre(source, ["mermaid", "icons"], packs)
        assert "<svg" not in result
        assert result.count(":octicons-rocket-16:") == 2

    def test_fence_line_in_a_diagram_changes_nothing_after_the_diagram(self, packs: dict[str, str]) -> None:
        source = (
            "~~~~mermaid\ngraph LR\n```\n~~~~\n\nAfter :octicons-rocket-16:\n\n```\ncode :octicons-rocket-16:\n```\n"
        )
        result = self.pipeline_pre(source, ["mermaid", "icons"], packs)
        assert f'After <span aria-hidden="true" class="mw-icon">{ROCKET}</span>' in result
        assert "```\ncode :octicons-rocket-16:\n```" in result

    def test_icons_stage_is_idempotent(self, packs: dict[str, str]) -> None:
        source = (
            "[button https://x.test :octicons-rocket-16: Go]\n\n```mermaid\ngraph LR\n```\n\n:octicons-rocket-16:\n"
        )
        names = ["button", "mermaid", "icons"]
        once = self.pipeline_pre(source, names, packs)
        assert self.pipeline_pre(once, names, packs) == once


# Sources where a <pre> tag appears but no raw <pre> block starts, or the tags sit in code or a comment. The
# in-process render and mw pre agree on each: the shortcode between the tags is an icon in both.
PRE_LOOKALIKE_SOURCES = {
    "inline in a paragraph": "text <pre>:octicons-rocket-16:</pre> end\n",
    "other tag with the same prefix": "<pre-x>:octicons-rocket-16:</pre-x> and <pre>z</pre>\n",
    "between two code spans": "`<pre>` then :octicons-rocket-16: then `</pre>`\n",
    "between two comments": "<!-- <pre> -->\n\n:octicons-rocket-16:\n\n<!-- </pre> -->\n",
    "between two lines of one comment": "<!--\n<pre>\n-->\n\n:octicons-rocket-16:\n\n<!-- </pre> -->\n",
    "between two fences": "```\n<pre>\n```\n\n:octicons-rocket-16:\n\n```\n</pre>\n```\n",
}

# A shortcode after the closing tag of a diagram stays prose on its line. The Python-Markdown stub splits an
# inline SVG that follows a block, so these compare the number of icons, not the markup.
TEXT_AFTER_DIAGRAM_SOURCES = {
    "one-line diagram tag": '<pre class="mermaid">x</pre> :octicons-rocket-16:\n',
    "diagram closing tag": '<pre class="mermaid">\nx\n</pre> tail :octicons-rocket-16:\n',
    "two lines": '<pre class="mermaid">x</pre> :octicons-rocket-16:\n\nnext :octicons-rocket-16:\n',
}

# Raw <pre> blocks the author wrote, and mermaid-like tags that are not the diagram's exact tag. The icons stage
# does not read the block structure, so it rewrites every shortcode outside code (a Roadmap Deferred entry in spec.md).
UNSKIPPED_BLOCK_SOURCES = {
    "closed block": "<pre>\n:octicons-rocket-16:\n</pre>\n",
    "unclosed block with a fence after it": (
        "<pre>\n:octicons-rocket-16:\n\n```\ncode\n```\n\nmore :octicons-rocket-16:\n"
    ),
    "text after the closing tag": "<pre>\n:octicons-rocket-16:\n</pre> tail :octicons-rocket-16:\n",
    "upper case mermaid tag": '<PRE CLASS="MERMAID">\n:octicons-rocket-16:\n</PRE>\n',
    "mermaid tag with another attribute": '<pre class="mermaid" id="x">\n:octicons-rocket-16:\n</pre>\n',
}


class TestIconsPreTags:
    """Only the diagram the mermaid stage emitted is skipped; any other <pre> text is read as before."""

    @pytest.mark.parametrize("source", PRE_LOOKALIKE_SOURCES.values(), ids=PRE_LOOKALIKE_SOURCES.keys())
    def test_pipeline_matches_the_in_process_render(self, packs: dict[str, str], source: str) -> None:
        extensions = ["pymdownx.superfences", "admonition"]
        in_process = markdown.Markdown(
            extensions=[*extensions, "markwright.icons"],
            extension_configs={"markwright.icons": {"packs": packs}},
        ).convert(source)
        pre_output = run_pre(source, ["icons"], {"icons": {"packs": packs}})
        pipeline = markdown.Markdown(extensions=extensions).convert(pre_output)

        assert pipeline == in_process

    @pytest.mark.parametrize("source", TEXT_AFTER_DIAGRAM_SOURCES.values(), ids=TEXT_AFTER_DIAGRAM_SOURCES.keys())
    def test_text_after_a_diagram_tag_keeps_its_icon(self, packs: dict[str, str], source: str) -> None:
        extensions = ["pymdownx.superfences"]
        in_process = markdown.Markdown(
            extensions=[*extensions, "markwright.icons"],
            extension_configs={"markwright.icons": {"packs": packs}},
        ).convert(source)
        pre_output = run_pre(source, ["icons"], {"icons": {"packs": packs}})
        pipeline = markdown.Markdown(extensions=extensions).convert(pre_output)

        assert pipeline.count("<svg") == in_process.count("<svg")

    @pytest.mark.parametrize("source", UNSKIPPED_BLOCK_SOURCES.values(), ids=UNSKIPPED_BLOCK_SOURCES.keys())
    def test_every_shortcode_outside_code_is_rewritten(self, packs: dict[str, str], source: str) -> None:
        icon = f'<span aria-hidden="true" class="mw-icon">{ROCKET}</span>'

        result = run_pre(source, ["icons"], {"icons": {"packs": packs}})

        assert result == source.replace(":octicons-rocket-16:", icon)


class TestIconsInProcess:
    """Tests for the Python-Markdown extension."""

    def test_icon_renders_inside_a_paragraph(self, packs: dict[str, str]) -> None:
        result = render_icons("Launch :octicons-rocket-16: now", packs)
        assert result == f'<p>Launch <span aria-hidden="true" class="mw-icon">{ROCKET}</span> now</p>'

    def test_inline_code_is_untouched(self, packs: dict[str, str]) -> None:
        result = render_icons("Use `:octicons-rocket-16:` here", packs)
        assert "mw-icon" not in result
        assert ":octicons-rocket-16:" in result

    def test_unknown_name_stays_literal(self, packs: dict[str, str]) -> None:
        assert render_icons(":octicons-missing-16:", packs) == "<p>:octicons-missing-16:</p>"

    def test_no_packs_passes_text_through(self) -> None:
        assert render_icons(":octicons-rocket-16:") == "<p>:octicons-rocket-16:</p>"

    def test_invalid_packs_raise_at_construction(self) -> None:
        with pytest.raises(OptionError, match="'packs' must be a table"):
            markdown.Markdown(extensions=["markwright.icons"], extension_configs={"markwright.icons": {"packs": 1}})

    def test_set_config_after_construction_applies(self, packs: dict[str, str]) -> None:
        extension = IconsExtension()
        extension.setConfig("packs", packs)
        result = markdown.Markdown(extensions=[extension]).convert(":octicons-rocket-16:")
        assert "mw-icon" in result

    def test_image_alt_text_keeps_the_shortcode_literal(self, packs: dict[str, str]) -> None:
        result = render_icons("![Star :octicons-rocket-16:](a.png)", packs)
        assert 'alt="Star :octicons-rocket-16:"' in result
        assert "<svg" not in result

    def test_link_title_keeps_the_shortcode_literal(self, packs: dict[str, str]) -> None:
        result = render_icons('[go](/a ":octicons-rocket-16: tip")', packs)
        assert 'title=":octicons-rocket-16: tip"' in result

    def test_autolink_keeps_the_shortcode_literal(self, packs: dict[str, str]) -> None:
        result = render_icons("<https://x.test/:octicons-rocket-16:>", packs)
        assert 'href="https://x.test/:octicons-rocket-16:"' in result
        assert "<svg" not in result

    def test_inline_html_attribute_keeps_the_shortcode_literal(self, packs: dict[str, str]) -> None:
        result = render_icons('<span title=":octicons-rocket-16:">y</span>', packs)
        assert 'title=":octicons-rocket-16:"' in result

    def test_link_text_still_renders_the_icon(self, packs: dict[str, str]) -> None:
        result = render_icons("[go :octicons-rocket-16:](/a)", packs)
        assert f'<a href="/a">go <span aria-hidden="true" class="mw-icon">{ROCKET}</span></a>' in result

    def test_emphasis_still_renders_the_icon(self, packs: dict[str, str]) -> None:
        result = render_icons("*em :octicons-rocket-16:*", packs)
        assert f'<em>em <span aria-hidden="true" class="mw-icon">{ROCKET}</span></em>' in result


class TestIconsOptions:
    """Tests for option validation."""

    @pytest.mark.parametrize("bad_packs", [["x"], {"x": 1}, {1: "dir"}, "dir"])
    def test_non_table_or_non_string_values_raise(self, bad_packs: object) -> None:
        with pytest.raises(OptionError, match="'packs' must be a table of pack name to directory"):
            expand_source(":a-b:", {"packs": bad_packs})

    def test_missing_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(OptionError, match="directory for 'octicons' not found"):
            expand_source(":a-b:", {"packs": {"octicons": str(tmp_path / "nope")}})

    def test_non_utf8_svg_raises_naming_the_file(self, packs: dict[str, str]) -> None:
        bad_file = Path(packs["octicons"]) / "broken-16.svg"
        bad_file.write_bytes(b"<svg>\xff\xfe</svg>")
        with pytest.raises(OptionError, match=r"broken-16\.svg"):
            expand_source(":octicons-broken-16:", {"packs": packs})

    def test_unreadable_svg_raises_naming_the_file(self, packs: dict[str, str]) -> None:
        # A directory named like an SVG makes the read fail with an OSError whatever the user or filesystem
        (Path(packs["octicons"]) / "locked-16.svg").mkdir()
        with pytest.raises(OptionError, match=r"locked-16\.svg"):
            expand_source(":octicons-locked-16:", {"packs": packs})

    def test_readable_svg_still_inlines_beside_a_broken_one(self, packs: dict[str, str]) -> None:
        (Path(packs["octicons"]) / "broken-16.svg").write_bytes(b"\xff\xfe")
        assert "<svg" in expand_source(":octicons-rocket-16:", {"packs": packs})

    def test_config_reports_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match=r"\[icons\] 'packs' directory for 'octicons' not found"):
            config_from_mapping({"icons": {"packs": {"octicons": str(tmp_path / "nope")}}}, "test")

    def test_config_stores_valid_packs(self, packs: dict[str, str]) -> None:
        config = config_from_mapping({"icons": {"packs": packs}}, "test")
        assert config.options["icons"] == {"packs": packs}
