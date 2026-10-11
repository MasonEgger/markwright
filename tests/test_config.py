# ABOUTME: Tests for the config module: pathlib discovery, tomllib parse, validation, resolved Config.
# Drives load_config directly with tmp_path trees and asserts ConfigError at each boundary.

from __future__ import annotations

import dataclasses
import logging
import tomllib
from pathlib import Path

import pytest

import markwright
from markwright.config import (
    Config,
    ConfigError,
    config_from_mapping,
    extension_configs,
    load_config,
    selected_extensions,
)
from markwright.registry import EXTENSION_NAMES

MAPPING_SOURCE = "bartleby.yml: markwright"

# Config files load_config accepts; config_from_mapping must resolve the same table identically.
VALID_TOML = [
    "",
    'enable = ["fence", "youtube"]\n',
    'disable = ["youtube", "twitter"]\nwarn = true\n',
    '[fence]\nallowed_environments = ["staging"]\n',
    '[youtube]\nload = "lazy"\n\n[twitter]\nload = "click"\n',
]

# Config files load_config rejects, each with a fragment of the expected message.
INVALID_TOML = [
    ('enable = ["fence"]\ndisable = ["youtube"]\n', "mutually exclusive"),
    ("enabled = true\n", "enabled"),
    ('enable = ["bogus"]\n', "bogus"),
    ('disable = ["nope"]\n', "nope"),
    ('enable = "fence"\n', "enable"),
    ("enable = [1, 2]\n", "enable"),
    ('warn = "yes"\n', "warn"),
    ("fence = 3\n", "fence"),
    ('[twitter]\nload = "lazy"\n', "twitter.load"),
    ('[youtube]\nload = "sometimes"\n', "youtube.load"),
    ('[slideshow]\nload = "click"\n', "slideshow"),
]


def _write(path: Path, text: str) -> Path:
    """Write ``text`` to ``path`` and return the path.

    :param path: Destination file path.
    :param text: File contents.
    :returns: The written path.
    """
    path.write_text(text, encoding="utf-8")
    return path


class TestDiscovery:
    """Tests for pathlib walk-up discovery of the config file."""

    def test_finds_markwright_toml_in_parent_dir(self, tmp_path: Path) -> None:
        config_path = _write(tmp_path / "markwright.toml", 'disable = ["youtube"]\n')
        child = tmp_path / "docs" / "nested"
        child.mkdir(parents=True)
        config = load_config(None, child)
        assert config.source_path == config_path
        assert config.disable == ("youtube",)

    def test_markwright_toml_wins_over_pyproject_in_same_dir(self, tmp_path: Path) -> None:
        standalone = _write(tmp_path / "markwright.toml", 'disable = ["youtube"]\n')
        _write(tmp_path / "pyproject.toml", '[tool.markwright]\ndisable = ["fence"]\n')
        config = load_config(None, tmp_path)
        assert config.source_path == standalone
        assert config.disable == ("youtube",)

    def test_finds_pyproject_tool_markwright_table(self, tmp_path: Path) -> None:
        pyproject = _write(tmp_path / "pyproject.toml", '[tool.markwright]\nenable = ["fence"]\n')
        config = load_config(None, tmp_path)
        assert config.source_path == pyproject
        assert config.enable == ("fence",)

    def test_pyproject_without_markwright_table_is_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path / "pyproject.toml", "[tool.ruff]\nline-length = 120\n")
        config = load_config(None, tmp_path)
        assert config.source_path is None
        assert config.enable is None
        assert config.disable == ()

    def test_pyproject_without_tool_table_is_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
        config = load_config(None, tmp_path)
        assert config.source_path is None

    def test_no_config_anywhere_yields_defaults(self, tmp_path: Path) -> None:
        config = load_config(None, tmp_path)
        assert config == Config()


class TestExplicitPath:
    """Tests for the --config PATH bypass of discovery."""

    def test_explicit_markwright_toml_loads(self, tmp_path: Path) -> None:
        elsewhere = _write(tmp_path / "custom.toml", 'enable = ["fence"]\n')
        unrelated_start = tmp_path / "somewhere" / "else"
        unrelated_start.mkdir(parents=True)
        config = load_config(elsewhere, unrelated_start)
        assert config.source_path == elsewhere
        assert config.enable == ("fence",)

    def test_missing_explicit_path_errors(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="not found"):
            load_config(tmp_path / "absent.toml", tmp_path)

    def test_explicit_pyproject_requires_markwright_table(self, tmp_path: Path) -> None:
        pyproject = _write(tmp_path / "pyproject.toml", "[tool.ruff]\nline-length = 120\n")
        with pytest.raises(ConfigError, match="tool.markwright"):
            load_config(pyproject, tmp_path)

    def test_explicit_pyproject_with_table_loads(self, tmp_path: Path) -> None:
        pyproject = _write(tmp_path / "pyproject.toml", "[tool.markwright]\nwarn = true\n")
        config = load_config(pyproject, tmp_path)
        assert config.source_path == pyproject
        assert config.warn is True


class TestParsing:
    """Tests for TOML parse-error handling at the boundary."""

    def test_malformed_toml_raises_config_error(self, tmp_path: Path) -> None:
        bad = _write(tmp_path / "markwright.toml", "enable = [\n")
        with pytest.raises(ConfigError, match="parse"):
            load_config(None, tmp_path)
        assert bad.exists()


class TestValidation:
    """Tests for schema validation of the resolved config table."""

    def test_enable_and_disable_together_errors(self, tmp_path: Path) -> None:
        _write(tmp_path / "markwright.toml", 'enable = ["fence"]\ndisable = ["youtube"]\n')
        with pytest.raises(ConfigError, match="mutually exclusive"):
            load_config(None, tmp_path)

    def test_unknown_top_level_key_errors(self, tmp_path: Path) -> None:
        _write(tmp_path / "markwright.toml", "enabled = true\n")
        with pytest.raises(ConfigError, match="enabled"):
            load_config(None, tmp_path)

    def test_unknown_extension_in_enable_errors(self, tmp_path: Path) -> None:
        _write(tmp_path / "markwright.toml", 'enable = ["bogus"]\n')
        with pytest.raises(ConfigError, match="bogus"):
            load_config(None, tmp_path)

    def test_unknown_extension_in_disable_errors(self, tmp_path: Path) -> None:
        _write(tmp_path / "markwright.toml", 'disable = ["nope"]\n')
        with pytest.raises(ConfigError, match="nope"):
            load_config(None, tmp_path)

    def test_enable_must_be_a_list_errors(self, tmp_path: Path) -> None:
        _write(tmp_path / "markwright.toml", 'enable = "fence"\n')
        with pytest.raises(ConfigError, match="enable"):
            load_config(None, tmp_path)

    def test_enable_list_items_must_be_strings(self, tmp_path: Path) -> None:
        _write(tmp_path / "markwright.toml", "enable = [1, 2]\n")
        with pytest.raises(ConfigError, match="enable"):
            load_config(None, tmp_path)

    def test_warn_must_be_boolean_errors(self, tmp_path: Path) -> None:
        _write(tmp_path / "markwright.toml", 'warn = "yes"\n')
        with pytest.raises(ConfigError, match="warn"):
            load_config(None, tmp_path)

    def test_extension_key_must_be_a_table_errors(self, tmp_path: Path) -> None:
        _write(tmp_path / "markwright.toml", "fence = 3\n")
        with pytest.raises(ConfigError, match="fence"):
            load_config(None, tmp_path)


class TestResolvedConfig:
    """Tests that a valid file resolves to the expected Config with a source map."""

    def test_valid_file_resolves_all_fields(self, tmp_path: Path) -> None:
        config_path = _write(
            tmp_path / "markwright.toml",
            'enable = ["fence", "youtube"]\nwarn = true\n\n[fence]\nallowed_environments = ["staging"]\n',
        )
        config = load_config(None, tmp_path)
        assert config.enable == ("fence", "youtube")
        assert config.disable == ()
        assert config.warn is True
        assert config.options == {"fence": {"allowed_environments": ["staging"]}}
        assert config.source_path == config_path
        assert config.sources == {
            "enable": str(config_path),
            "warn": str(config_path),
            "fence": str(config_path),
        }

    def test_disable_only_leaves_enable_none(self, tmp_path: Path) -> None:
        _write(tmp_path / "markwright.toml", 'disable = ["youtube", "twitter"]\n')
        config = load_config(None, tmp_path)
        assert config.enable is None
        assert config.disable == ("youtube", "twitter")
        assert config.options == {}


class TestConfigFromMapping:
    """Tests that an already-parsed table validates exactly as a config file does."""

    def test_empty_mapping_is_the_default_config(self) -> None:
        config = config_from_mapping({}, MAPPING_SOURCE)
        assert config == Config()

    @pytest.mark.parametrize("toml_text", VALID_TOML)
    def test_matches_load_config_for_valid_tables(self, tmp_path: Path, toml_text: str) -> None:
        config_path = _write(tmp_path / "markwright.toml", toml_text)
        from_file = load_config(config_path, tmp_path)
        from_mapping = config_from_mapping(tomllib.loads(toml_text), MAPPING_SOURCE)
        assert from_mapping == dataclasses.replace(
            from_file,
            source_path=None,
            sources={key: MAPPING_SOURCE for key in from_file.sources},
        )

    @pytest.mark.parametrize(("toml_text", "message_fragment"), INVALID_TOML)
    def test_rejects_what_load_config_rejects(self, tmp_path: Path, toml_text: str, message_fragment: str) -> None:
        _write(tmp_path / "markwright.toml", toml_text)
        with pytest.raises(ConfigError, match=message_fragment):
            load_config(None, tmp_path)
        with pytest.raises(ConfigError, match=message_fragment) as mapping_error:
            config_from_mapping(tomllib.loads(toml_text), MAPPING_SOURCE)
        assert str(mapping_error.value).startswith(f"{MAPPING_SOURCE}: ")

    def test_source_map_uses_the_label(self) -> None:
        config = config_from_mapping({"warn": True, "fence": {}}, MAPPING_SOURCE)
        assert config.source_path is None
        assert config.sources == {"warn": MAPPING_SOURCE, "fence": MAPPING_SOURCE}


class TestSelectedExtensions:
    """Tests that enable and disable resolve to extension names in registry order."""

    def test_default_selects_every_extension(self) -> None:
        assert selected_extensions(Config()) == list(EXTENSION_NAMES)

    def test_enable_selects_only_those_in_registry_order(self) -> None:
        config = Config(enable=("highlight", "youtube"))
        assert selected_extensions(config) == ["youtube", "highlight"]

    def test_disable_removes_names(self) -> None:
        config = Config(disable=("youtube", "fence"))
        assert selected_extensions(config) == [name for name in EXTENSION_NAMES if name not in ("youtube", "fence")]

    def test_empty_enable_selects_nothing(self, tmp_path: Path) -> None:
        config_path = _write(tmp_path / "markwright.toml", "enable = []\n")
        assert selected_extensions(load_config(config_path, tmp_path)) == []
        assert selected_extensions(config_from_mapping({"enable": []}, MAPPING_SOURCE)) == []

    def test_disabling_everything_selects_nothing(self) -> None:
        config = Config(disable=EXTENSION_NAMES)
        assert selected_extensions(config) == []


class TestEmptySelectionWarning:
    """An empty selection is allowed (it switches markwright off in a tool chain) but never silent."""

    def test_empty_enable_warns_with_source(self, caplog: pytest.LogCaptureFixture) -> None:
        config = config_from_mapping({"enable": []}, MAPPING_SOURCE)
        with caplog.at_level(logging.WARNING, logger="markwright"):
            selected_extensions(config)
        assert [record.levelno for record in caplog.records] == [logging.WARNING]
        assert "no markwright extensions selected" in caplog.text
        assert f"'enable' is empty in {MAPPING_SOURCE}" in caplog.text

    def test_disable_listing_everything_warns_with_source(self, caplog: pytest.LogCaptureFixture) -> None:
        config = config_from_mapping({"disable": list(EXTENSION_NAMES)}, MAPPING_SOURCE)
        with caplog.at_level(logging.WARNING, logger="markwright"):
            selected_extensions(config)
        assert f"'disable' lists every extension in {MAPPING_SOURCE}" in caplog.text

    def test_non_empty_selection_does_not_warn(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING, logger="markwright"):
            selected_extensions(config_from_mapping({"enable": ["fence"]}, MAPPING_SOURCE))
            selected_extensions(Config())
        assert caplog.records == []


class TestExtensionConfigs:
    """Tests that per-extension option tables become markdown.Markdown extension_configs."""

    def test_only_selected_extensions_with_options_appear(self) -> None:
        config = Config(options={"fence": {"allowed_environments": ["staging"]}, "youtube": {}, "twitter": {"x": 1}})
        assert extension_configs(config, ["fence", "youtube", "highlight"]) == {
            "markwright.fence": {"allowed_environments": ["staging"]},
        }

    def test_no_options_yields_empty_mapping(self) -> None:
        assert extension_configs(Config(), list(EXTENSION_NAMES)) == {}


class TestPackageExports:
    """Tests that host tools can import the config API from the package root."""

    def test_package_reexports_the_config_api(self) -> None:
        assert markwright.__all__ == [
            "Config",
            "ConfigError",
            "config_from_mapping",
            "extension_configs",
            "selected_extensions",
        ]
        assert markwright.config_from_mapping is config_from_mapping
        assert markwright.Config is Config
