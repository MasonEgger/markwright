# ABOUTME: Command-line entry point for the mw markwright pipeline tool.
# Builds the argparse parser and dispatches list/pre/post/render; --version reports the package version.

from __future__ import annotations

import argparse
import sys
import warnings
from importlib.metadata import version
from pathlib import Path
from typing import TextIO

import markdown

from markwright import config, registry
from markwright._diagnostics import ConfigWarning
from markwright._embed_load import LOAD_EAGER
from markwright.config import Config, ConfigError


def _package_version() -> str:
    """Return the installed markwright distribution version.

    :returns: The version string for the ``markwright`` distribution.
    """
    return version("markwright")


def build_parser() -> argparse.ArgumentParser:
    """Construct the ``mw`` argument parser with its subcommands.

    :returns: A parser exposing ``--version`` and the ``list`` subcommand.
    """
    parser = argparse.ArgumentParser(prog="mw", description="markwright Markdown pipeline CLI.")
    parser.add_argument("--version", action="version", version=f"mw {_package_version()}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("list", help="List registered extensions and the stages each provides.")
    pre_parser = subparsers.add_parser("pre", help="Expand markwright source directives read from stdin.")
    _add_selection_flags(pre_parser)
    post_parser = subparsers.add_parser("post", help="Post-process rendered HTML read from stdin.")
    _add_selection_flags(post_parser)
    post_parser.add_argument("--warn", action="store_true", help="Report skipped markers to stderr.")
    render_parser = subparsers.add_parser("render", help="Render Markdown from stdin to final HTML.")
    _add_selection_flags(render_parser)
    config_parser = subparsers.add_parser("config", help="Print the resolved configuration and each value's source.")
    _add_selection_flags(config_parser)
    return parser


def _add_selection_flags(subparser: argparse.ArgumentParser) -> None:
    """Add the shared ``--config`` and ``--exclude`` selection flags to a subparser.

    :param subparser: The subcommand parser to extend.
    """
    subparser.add_argument("--config", default=None, help="Load configuration from PATH, bypassing discovery.")
    subparser.add_argument(
        "--exclude",
        action="append",
        default=[],
        choices=registry.EXTENSION_NAMES,
        metavar="NAME",
        help="Drop the named extension (repeatable).",
    )


def _run_list() -> None:
    """Print each registered extension and its available stages."""
    for name, stages in registry.describe():
        print(f"{name}: {', '.join(stages)}")


def _resolve(args: argparse.Namespace) -> tuple[Config, list[str]]:
    """Load config and resolve the active extension names.

    Selection resolves from config (``enable`` allowlist or ``disable`` denylist) through
    :func:`config.selected_extensions`, with the repeatable CLI ``--exclude`` applied on top
    (argparse has already rejected unknown names).

    :param args: Parsed arguments carrying ``config`` and ``exclude``.
    :returns: The resolved config and selected extension names.
    :raises ConfigError: If the config file is missing, malformed, or invalid.
    """
    explicit_path = Path(args.config) if args.config else None
    resolved_config = config.load_config(explicit_path, Path.cwd())
    config_selected = config.selected_extensions(resolved_config)
    names = [name for name in config_selected if name not in args.exclude]

    # An empty config selection already warned; only report the case --exclude caused
    if config_selected and not names:
        warnings.warn(
            "no markwright extensions selected (--exclude removed every one);"
            " markwright syntax passes through unprocessed",
            ConfigWarning,
            stacklevel=2,
        )
    return resolved_config, names


def _run_pre(args: argparse.Namespace) -> None:
    """Expand source directives from stdin and write the result to stdout.

    :param args: Parsed arguments carrying ``config`` and ``exclude``.
    :raises ConfigError: If the config is invalid.
    """
    resolved_config, names = _resolve(args)
    sys.stdout.write(registry.run_pre(sys.stdin.read(), names, resolved_config.options))


def _run_post(args: argparse.Namespace) -> None:
    """Post-process HTML from stdin and write the result to stdout.

    :param args: Parsed arguments carrying ``config``, ``exclude``, and ``warn``.
    :raises ConfigError: If the config is invalid.
    """
    resolved_config, names = _resolve(args)
    marker_warnings: list[str] | None = [] if args.warn else None
    rendered_html = registry.run_post(sys.stdin.read(), names, marker_warnings, resolved_config.options)
    sys.stdout.write(rendered_html)
    if marker_warnings is not None:
        for marker_warning in marker_warnings:
            print(marker_warning, file=sys.stderr)


def _run_render(args: argparse.Namespace) -> None:
    """Render Markdown from stdin to final HTML using the in-process stack.

    Builds a ``markdown.Markdown`` instance configured with ``pymdownx.superfences``
    and ``pymdownx.highlight`` plus the selected ``markwright.*`` extensions, mirroring
    the site stack so fence and highlight render correctly.

    :param args: Parsed arguments carrying ``config`` and ``exclude``.
    :raises ConfigError: If the config is invalid.
    """
    resolved_config, names = _resolve(args)
    instance = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight", *(f"markwright.{name}" for name in names)],
        # pygments_lang_class is a CLI rendering choice, not markwright config
        extension_configs={
            "pymdownx.highlight": {"pygments_lang_class": True},
            **config.extension_configs(resolved_config, names),
        },
    )
    sys.stdout.write(instance.convert(sys.stdin.read()))


def _extension_status(name: str, resolved_config: Config, excluded: list[str]) -> tuple[str, str]:
    """Report whether an extension is on or off and where that decision came from.

    Precedence matches selection: a CLI ``--exclude`` wins, then a config ``enable`` allowlist
    or ``disable`` denylist, then the all-on default.

    :param name: The extension name.
    :param resolved_config: The resolved config.
    :param excluded: Names passed to ``--exclude``.
    :returns: An ``(status, source)`` pair, ``status`` being ``"on"`` or ``"off"``.
    """
    config_source = str(resolved_config.source_path) if resolved_config.source_path is not None else "default"
    if name in excluded:
        return "off", "--exclude"
    if resolved_config.enable is not None:
        return ("on" if name in resolved_config.enable else "off"), config_source
    if name in resolved_config.disable:
        return "off", config_source
    return "on", "default"


def _format_config(resolved_config: Config, excluded: list[str]) -> list[str]:
    """Format the resolved configuration and value sources as printable lines.

    :param resolved_config: The resolved config.
    :param excluded: Names passed to ``--exclude``.
    :returns: Output lines for ``mw config``, one per rendered value.
    """
    lines = ["extensions:"]
    for name in registry.EXTENSION_NAMES:
        status, source = _extension_status(name, resolved_config, excluded)
        lines.append(f"  {name}: {status} ({source})")
    warn_source = resolved_config.sources.get("warn", "default")
    lines.append(f"warn: {str(resolved_config.warn).lower()} ({warn_source})")
    lines.append("load:")
    for extension_name in (name for name in registry.EXTENSION_NAMES if "load" in registry.OPTION_NAMES[name]):
        extension_options = resolved_config.options.get(extension_name, {})
        load = extension_options.get("load", LOAD_EAGER)
        source = resolved_config.sources[extension_name] if "load" in extension_options else "default"
        lines.append(f"  {extension_name}: {load} ({source})")
    if resolved_config.options:
        lines.append("options:")
        for extension_name, option_table in resolved_config.options.items():
            source = resolved_config.sources.get(extension_name, "default")
            lines.append(f"  {extension_name}: {option_table} ({source})")
    else:
        lines.append("options: none")
    return lines


def _run_config(args: argparse.Namespace) -> None:
    """Print the resolved configuration and the source of each value.

    :param args: Parsed arguments carrying ``config`` and ``exclude``.
    :raises ConfigError: If the config is invalid.
    """
    resolved_config, _ = _resolve(args)
    for line in _format_config(resolved_config, args.exclude):
        print(line)


def _show_warning(
    message: Warning | str,
    category: type[Warning],
    filename: str,
    lineno: int,
    file: TextIO | None = None,
    line: str | None = None,
) -> None:
    """Print a warning to stderr, as a one-line ``mw: warning:`` diagnostic when it is markwright's own.

    Replaces :func:`warnings.showwarning` for the duration of a CLI run, so a
    :class:`ConfigWarning` reads as tool output rather than a Python source location,
    while warnings from other libraries keep Python's standard format.

    :param message: The warning instance or text.
    :param category: The warning class.
    :param filename: The file that issued the warning.
    :param lineno: The line that issued the warning.
    :param file: The stream the default handler would write to; unused, stderr is always used.
    :param line: The source line, or ``None`` to read it from ``filename``.
    """
    if issubclass(category, ConfigWarning):
        print(f"mw: warning: {message}", file=sys.stderr)
    else:
        sys.stderr.write(warnings.formatwarning(message, category, filename, lineno, line))


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and dispatch to the selected subcommand.

    The CLI is the boundary where exceptions become exit codes: a :class:`ConfigError`, or a
    :class:`ConfigWarning` escalated to an error (``python -W error``), prints one
    ``mw: error:`` line and exits ``2``.

    :param argv: Argument vector, or ``None`` to read from ``sys.argv``.
    :returns: Process exit code (``0`` success, ``2`` usage error).
    """
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_error:
        return exit_error.code if isinstance(exit_error.code, int) else 2

    # Show warnings as mw diagnostics on stderr; catch_warnings restores the handler afterward
    with warnings.catch_warnings():
        warnings.showwarning = _show_warning
        try:
            match args.command:
                case "list":
                    _run_list()
                case "pre":
                    _run_pre(args)
                case "post":
                    _run_post(args)
                case "render":
                    _run_render(args)
                case "config":
                    _run_config(args)
                case _:
                    parser.print_usage()
                    return 2
        except (ConfigError, ConfigWarning) as usage_error:
            print(f"mw: error: {usage_error}", file=sys.stderr)
            return 2
    return 0
