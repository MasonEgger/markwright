# ABOUTME: Config discovery, TOML parsing, validation, and the resolved Config object.
# Owns the markwright.toml / [tool.markwright] tuning surface and the public API host tools build on.

from __future__ import annotations

import dataclasses
import tomllib
import warnings
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from markwright._diagnostics import ConfigWarning
from markwright.registry import EXTENSION_NAMES, LOAD_MODES

_TOP_LEVEL_KEYS: frozenset[str] = frozenset({"enable", "disable", "warn"})


class ConfigError(Exception):
    """Raised for any config discovery, parse, or validation failure.

    Carries a message meant for the user at the CLI boundary, never a traceback.
    """


@dataclass(frozen=True)
class Config:
    """Resolved markwright configuration.

    :ivar enable: Allowlist of extension names, or ``None`` when unset.
    :ivar disable: Denylist of extension names, empty when unset.
    :ivar options: Per-extension option tables keyed by extension name.
    :ivar warn: Default for the post stage's marker warnings.
    :ivar source_path: The file this config was loaded from, or ``None`` for built-in defaults
        and for a config built from a mapping.
    :ivar sources: Maps each key set in the table (``enable``, ``disable``, ``warn``, or an
        extension name) to the file path or source label it came from; keys not present use defaults.
    """

    enable: tuple[str, ...] | None = None
    disable: tuple[str, ...] = ()
    options: dict[str, dict[str, object]] = field(default_factory=dict)
    warn: bool = False
    source_path: Path | None = None
    sources: dict[str, str] = field(default_factory=dict)


def load_config(explicit_path: Path | None, start_dir: Path) -> Config:
    """Resolve the configuration from an explicit path or by walk-up discovery.

    :param explicit_path: A specific config file to load, bypassing discovery, or ``None``.
    :param start_dir: The directory to begin walk-up discovery from when no explicit path is given.
    :returns: The resolved :class:`Config`; built-in defaults when nothing is found.
    :raises ConfigError: If a file is missing, unparseable, or fails schema validation.
    """
    if explicit_path is not None:
        path, table = _load_explicit(explicit_path)
    else:
        discovered = _discover(start_dir)
        if discovered is None:
            return Config()
        path, table = discovered
    return dataclasses.replace(_build_config(table, str(path)), source_path=path)


def config_from_mapping(table: Mapping[str, object], source: str) -> Config:
    """Validate an already-parsed config table and resolve it into a :class:`Config`.

    For host tools that carry markwright config inside their own config file. The table
    gets the same validation as ``markwright.toml``; no file discovery happens here.

    :param table: The markwright table, same shape as ``markwright.toml``.
    :param source: A label for error messages and the source map, for example
        ``"bartleby.yml: markwright"``.
    :returns: The resolved config, with ``source_path`` left as ``None``.
    :raises ConfigError: On any unknown key, bad type, unknown extension name, or
        ``enable`` and ``disable`` both set.
    """
    return _build_config(table, source)


def selected_extensions(config: Config) -> list[str]:
    """Resolve the extension names a config turns on.

    A list names exactly what it holds: an empty ``enable`` selects nothing and an empty ``disable``
    removes nothing. An empty selection is allowed, since it switches markwright off inside a tool
    chain, but it emits a :class:`ConfigWarning` naming the cause so it never fails silently.

    :param config: The resolved config.
    :returns: Extension names after ``enable`` and ``disable``, in registry order.
    """
    names = [
        name
        for name in EXTENSION_NAMES
        if (config.enable is None or name in config.enable) and name not in config.disable
    ]

    # Report an empty selection with the key and source that caused it
    if not names:
        if config.enable is not None:
            cause = f"'enable' is empty in {config.sources.get('enable', 'config')}"
        else:
            cause = f"'disable' lists every extension in {config.sources.get('disable', 'config')}"
        warnings.warn(
            f"no markwright extensions selected ({cause}); markwright syntax passes through unprocessed",
            ConfigWarning,
            stacklevel=2,
        )
    return names


def extension_configs(config: Config, names: list[str]) -> dict[str, dict[str, object]]:
    """Assemble the ``extension_configs`` argument for ``markdown.Markdown``.

    :param config: The resolved config carrying per-extension option tables.
    :param names: The selected extension names.
    :returns: Option dicts keyed by ``markwright.<name>``, only for selected extensions
        with a non-empty option table.
    """
    return {f"markwright.{name}": config.options[name] for name in names if config.options.get(name)}


def _load_explicit(path: Path) -> tuple[Path, dict[str, object]]:
    """Load a config table from an explicitly named file.

    :param path: The file named by ``--config``.
    :returns: The path and its config table.
    :raises ConfigError: If the file is missing, or a ``pyproject.toml`` lacks a
        ``[tool.markwright]`` table.
    """
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    parsed = _read_toml(path)
    if path.name == "pyproject.toml":
        table = _pyproject_markwright_table(parsed)
        if table is None:
            raise ConfigError(f"no [tool.markwright] table in {path}")
        return path, table
    return path, parsed


def _discover(start_dir: Path) -> tuple[Path, dict[str, object]] | None:
    """Walk up from ``start_dir`` to the filesystem root looking for a config file.

    In each directory a ``markwright.toml`` wins over a ``pyproject.toml`` that carries a
    ``[tool.markwright]`` table. The first directory with either stops the search.

    :param start_dir: The directory to begin the walk from.
    :returns: The winning path and its config table, or ``None`` if none is found.
    :raises ConfigError: If a candidate file is present but unparseable.
    """
    for directory in [start_dir, *start_dir.parents]:
        standalone = directory / "markwright.toml"
        if standalone.is_file():
            return standalone, _read_toml(standalone)
        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            table = _pyproject_markwright_table(_read_toml(pyproject))
            if table is not None:
                return pyproject, table
    return None


def _read_toml(path: Path) -> dict[str, object]:
    """Parse a TOML file, converting parse failures into a clear boundary error.

    :param path: The TOML file to read.
    :returns: The parsed top-level table.
    :raises ConfigError: If the file is not valid TOML.
    """
    try:
        with path.open("rb") as handle:
            parsed: dict[str, object] = tomllib.load(handle)
    except tomllib.TOMLDecodeError as decode_error:
        raise ConfigError(f"could not parse {path}: {decode_error}") from decode_error
    return parsed


def _pyproject_markwright_table(parsed: Mapping[str, object]) -> dict[str, object] | None:
    """Extract the ``[tool.markwright]`` table from a parsed ``pyproject.toml``.

    :param parsed: The parsed ``pyproject.toml`` top-level table.
    :returns: The markwright config table, or ``None`` if the ``[tool.markwright]`` path is absent.
    """
    tool_section = parsed.get("tool")
    if not isinstance(tool_section, dict):
        return None
    markwright_section = tool_section.get("markwright")
    if not isinstance(markwright_section, dict):
        return None
    return markwright_section


def _build_config(table: Mapping[str, object], source: str) -> Config:
    """Validate a raw config table and resolve it into a :class:`Config`.

    :param table: The parsed config table (from a file, a ``[tool.markwright]`` table, or a host tool).
    :param source: The source path or label, used to prefix errors and recorded for the source map.
    :returns: The resolved config, with ``source_path`` unset.
    :raises ConfigError: If any key, type, or extension name is invalid.
    """
    _reject_unknown_keys(table, source)
    enable = _selection_list(table, "enable", source)
    disable = _selection_list(table, "disable", source)
    if enable is not None and disable is not None:
        raise ConfigError(f"{source}: 'enable' and 'disable' are mutually exclusive")
    return Config(
        enable=enable,
        disable=disable if disable is not None else (),
        options=_extension_options(table, source),
        warn=_warn_value(table, source),
        sources={key: source for key in table},
    )


def _reject_unknown_keys(table: Mapping[str, object], source: str) -> None:
    """Reject any top-level key that is neither a recognized setting nor an extension name.

    :param table: The config table.
    :param source: The source path or label, for the error message.
    :raises ConfigError: On the first unrecognized key.
    """
    for key in table:
        if key not in _TOP_LEVEL_KEYS and key not in EXTENSION_NAMES:
            raise ConfigError(f"{source}: unknown configuration key: {key!r}")


def _selection_list(table: Mapping[str, object], key: str, source: str) -> tuple[str, ...] | None:
    """Read and validate an ``enable`` or ``disable`` list of extension names.

    :param table: The config table.
    :param key: Either ``"enable"`` or ``"disable"``.
    :param source: The source path or label, for error messages.
    :returns: The names as a tuple, or ``None`` if the key is absent.
    :raises ConfigError: If the value is not a list of known extension names.
    """
    if key not in table:
        return None
    value = table[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{source}: '{key}' must be a list of extension names")
    for name in value:
        if name not in EXTENSION_NAMES:
            raise ConfigError(f"{source}: unknown extension in '{key}': {name!r}")
    return tuple(value)


def _warn_value(table: Mapping[str, object], source: str) -> bool:
    """Read and validate the boolean ``warn`` default.

    :param table: The config table.
    :param source: The source path or label, for the error message.
    :returns: The ``warn`` value, defaulting to ``False`` when absent.
    :raises ConfigError: If ``warn`` is present but not a boolean.
    """
    if "warn" not in table:
        return False
    value = table["warn"]
    if not isinstance(value, bool):
        raise ConfigError(f"{source}: 'warn' must be a boolean")
    return value


def _extension_options(table: Mapping[str, object], source: str) -> dict[str, dict[str, object]]:
    """Collect the per-extension option tables from the config.

    :param table: The config table.
    :param source: The source path or label, for error messages.
    :returns: Option dicts keyed by extension name, in registry order.
    :raises ConfigError: If an extension key is present but not a table, or its ``load``
        option is unsupported for that extension.
    """
    options: dict[str, dict[str, object]] = {}
    for name in EXTENSION_NAMES:
        if name not in table:
            continue
        extension_table = table[name]
        if not isinstance(extension_table, dict):
            raise ConfigError(f"{source}: '{name}' must be a table of options")
        # Validate only the options markwright defines; other keys pass through to the extension
        environments = extension_table.get("allowed_environments", [])
        if name == "fence" and not (
            isinstance(environments, list) and all(isinstance(env, str) for env in environments)
        ):
            raise ConfigError(f"{source}: 'fence.allowed_environments' must be a list of environment names")
        if "load" in extension_table:
            allowed_loads = LOAD_MODES.get(name)
            if allowed_loads is None:
                raise ConfigError(f"{source}: '{name}' does not take a 'load' option")
            if extension_table["load"] not in allowed_loads:
                load_value = extension_table["load"]
                raise ConfigError(
                    f"{source}: '{name}.load' must be one of {', '.join(allowed_loads)}; got {load_value!r}"
                )
        options[name] = extension_table
    return options
