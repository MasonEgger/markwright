# ABOUTME: Tests for the icons extension.
# Validates shortcode resolution, code skipping, option validation, and the in-process render.

from __future__ import annotations

from typing import TYPE_CHECKING

import markdown
import pytest

from markwright import ConfigError, ConfigWarning, OptionError, config_from_mapping
from markwright.icons import IconsExtension, expand_source

if TYPE_CHECKING:
    from pathlib import Path

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


class TestIconsOptions:
    """Tests for option validation."""

    @pytest.mark.parametrize("bad_packs", [["x"], {"x": 1}, {1: "dir"}, "dir"])
    def test_non_table_or_non_string_values_raise(self, bad_packs: object) -> None:
        with pytest.raises(OptionError, match="'packs' must be a table of pack name to directory"):
            expand_source(":a-b:", {"packs": bad_packs})

    def test_missing_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(OptionError, match="directory for 'octicons' not found"):
            expand_source(":a-b:", {"packs": {"octicons": str(tmp_path / "nope")}})

    def test_config_reports_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match=r"\[icons\] 'packs' directory for 'octicons' not found"):
            config_from_mapping({"icons": {"packs": {"octicons": str(tmp_path / "nope")}}}, "test")

    def test_config_stores_valid_packs(self, packs: dict[str, str]) -> None:
        config = config_from_mapping({"icons": {"packs": packs}}, "test")
        assert config.options["icons"] == {"packs": packs}
