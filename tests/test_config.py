# ABOUTME: Tests for the config module: pathlib discovery, tomllib parse, validation, resolved Config.
# Drives load_config directly with tmp_path trees and asserts ConfigError at each boundary.

from __future__ import annotations

from pathlib import Path

import pytest

from markwright.config import Config, ConfigError, load_config


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
