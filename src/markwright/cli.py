# ABOUTME: Command-line entry point for the mw markwright pipeline tool.
# Builds the argparse parser and dispatches list/pre/post/render; --version reports the package version.

from __future__ import annotations

import argparse
import os
import sys
import warnings
from importlib.metadata import version
from pathlib import Path
from typing import TextIO

import markdown

from markwright import config, registry
from markwright._diagnostics import ConfigWarning, Diagnostic, OptionError, RenderWarning
from markwright._embed_load import LOAD_EAGER
from markwright.config import Config, ConfigError


def build_parser() -> argparse.ArgumentParser:
    """Construct the ``mw`` argument parser with its subcommands.

    :returns: A parser exposing ``--version`` and the ``list`` subcommand.
    """
    parser = argparse.ArgumentParser(prog="mw", description="markwright Markdown pipeline CLI.")
    parser.add_argument("--version", action="version", version=f"mw {version('markwright')}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("list", help="List registered extensions and the stages each provides.")
    pre_parser = subparsers.add_parser("pre", help="Expand markwright source directives read from stdin.")
    _add_selection_flags(pre_parser)
    post_parser = subparsers.add_parser("post", help="Post-process rendered HTML read from stdin.")
    _add_selection_flags(post_parser)
    _add_warn_flags(post_parser)
    render_parser = subparsers.add_parser("render", help="Render Markdown from stdin to final HTML.")
    _add_selection_flags(render_parser)
    _add_warn_flags(render_parser)
    config_parser = subparsers.add_parser("config", help="Print the resolved configuration and each value's source.")
    _add_selection_flags(config_parser)
    return parser


def _add_warn_flags(subparser: argparse.ArgumentParser) -> None:
    """Add the shared ``--warn`` and ``--no-warn`` flags to a subparser.

    Both flags write ``warn``; ``None`` means neither was given, so the config default applies and the last flag wins.

    :param subparser: The ``post`` or ``render`` subparser.
    """
    subparser.add_argument(
        "--warn",
        action="store_const",
        const=True,
        dest="warn",
        default=None,
        help="Report skipped markers to stderr (overrides the config 'warn' key).",
    )
    subparser.add_argument(
        "--no-warn",
        action="store_const",
        const=False,
        dest="warn",
        help="Do not report skipped markers (overrides the config 'warn' key).",
    )


def _warn_enabled(args: argparse.Namespace, resolved_config: Config) -> bool:
    """Decide whether diagnostics are on: the last of ``--warn`` and ``--no-warn``, else the config key.

    :param args: Parsed arguments carrying ``warn`` (``None`` when no flag was given).
    :param resolved_config: The resolved config, whose ``warn`` is the default.
    :returns: ``True`` when diagnostics should be reported.
    """
    return resolved_config.warn if args.warn is None else args.warn


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


class _StreamError(Exception):
    """Raised when stdin cannot be read or stdout cannot be written; ``main`` reports it as ``mw: error:``."""


def _use_utf8_stdio() -> None:
    """Switch stdin and stdout to UTF-8 whatever the locale or ``PYTHONIOENCODING`` says.

    A stream without ``reconfigure`` (a test stand-in, for example) is left as it is.
    """
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def _read_stdin() -> str:
    """Read all of stdin.

    :returns: The decoded text.
    :raises _StreamError: If stdin is not UTF-8, is closed, or cannot be read.
    """
    # Python sets a stream to None when its descriptor is closed at startup
    if sys.stdin is None:
        raise _StreamError("cannot read stdin: stdin is closed")
    try:
        return sys.stdin.read()
    except (UnicodeDecodeError, OSError, ValueError) as read_error:
        raise _StreamError(f"cannot read stdin: {read_error}") from read_error


def _write_stdout(text: str) -> None:
    """Write text to stdout and flush it, so a broken pipe surfaces here.

    :param text: The text to write.
    :raises _StreamError: If stdout is closed, the pipe is broken, or the write fails.
    """
    if sys.stdout is None:
        raise _StreamError("cannot write stdout: stdout is closed")
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except (OSError, ValueError) as write_error:
        _discard_stdout()
        raise _StreamError(f"cannot write stdout: {write_error}") from write_error


def _discard_stdout() -> None:
    """Point stdout's descriptor at the null device, so the buffered bytes a failed flush left behind
    cannot fail again when the interpreter flushes at exit (the Python docs' note on SIGPIPE).

    A stream with no descriptor, or one already closed, is left as it is.
    """
    try:
        stdout_descriptor = sys.stdout.fileno()
    except (OSError, ValueError):
        return
    os.dup2(os.open(os.devnull, os.O_WRONLY), stdout_descriptor)


def _split_front_matter(text: str) -> tuple[str, str]:
    """Split a leading front matter block off a document.

    The block starts on the first line, which is exactly ``---`` (YAML) or ``+++`` (TOML), and ends at
    the next line that is exactly the same delimiter. An opener with no closer is not front matter.

    :param text: The whole document.
    :returns: The front matter through its closing line (empty when there is none) and the rest.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") not in ("---", "+++"):
        return "", text
    delimiter = lines[0].rstrip("\r\n")
    for line_number, line in enumerate(lines[1:], start=2):
        if line.rstrip("\r\n") == delimiter:
            return "".join(lines[:line_number]), "".join(lines[line_number:])
    return "", text


def _run_pre(args: argparse.Namespace) -> None:
    """Expand source directives from stdin and write the result to stdout.

    A leading YAML or TOML front matter block is written back untouched; only the rest is expanded.

    :param args: Parsed arguments carrying ``config`` and ``exclude``.
    :raises ConfigError: If the config is invalid.
    :raises OptionError: If an icon file cannot be read or is not UTF-8.
    :raises _StreamError: If stdin cannot be read or stdout cannot be written.
    """
    resolved_config, names = _resolve(args)
    front_matter, body = _split_front_matter(_read_stdin())
    _write_stdout(front_matter + registry.run_pre(body, names, resolved_config.options))


def _run_post(args: argparse.Namespace) -> None:
    """Post-process HTML from stdin and write the result to stdout.

    Diagnostics are on when ``--warn`` is the last of the two flags given, off when ``--no-warn``
    is, and otherwise follow the config ``warn`` key. They are plain stderr lines, not Python warnings.

    :param args: Parsed arguments carrying ``config``, ``exclude``, and ``warn`` (``None`` when no flag was given).
    :raises ConfigError: If the config is invalid.
    :raises _StreamError: If stdin cannot be read or stdout cannot be written.
    """
    resolved_config, names = _resolve(args)
    marker_diagnostics: list[Diagnostic] | None = [] if _warn_enabled(args, resolved_config) else None
    rendered_html = registry.run_post(_read_stdin(), names, marker_diagnostics, resolved_config.options)
    _write_stdout(rendered_html)
    if marker_diagnostics is not None:
        for diagnostic in marker_diagnostics:
            print(diagnostic.message, file=sys.stderr)


def _run_render(args: argparse.Namespace) -> None:
    """Render Markdown from stdin to final HTML using the in-process stack.

    Builds a ``markdown.Markdown`` instance configured with ``pymdownx.superfences``
    and ``pymdownx.highlight`` plus the selected ``markwright.*`` extensions, mirroring
    the site stack so fence and highlight render correctly.

    A reported :class:`RenderWarning` prints as one ``mw: warning:`` line when diagnostics are on
    (the same rule as ``post``) and is dropped when they are off. The filter is set inside the
    run, so ``PYTHONWARNINGS=error`` never turns a diagnostic into a failure.

    :param args: Parsed arguments carrying ``config``, ``exclude``, and ``warn``.
    :raises ConfigError: If the config is invalid.
    :raises _StreamError: If stdin cannot be read or stdout cannot be written.
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
    with warnings.catch_warnings():
        warnings.simplefilter("always" if _warn_enabled(args, resolved_config) else "ignore", RenderWarning)
        rendered_html = instance.convert(_read_stdin())
    _write_stdout(rendered_html)


def _run_config(args: argparse.Namespace) -> None:
    """Print the resolved configuration and the source of each value.

    Extension status follows selection precedence: a CLI ``--exclude`` wins, then the config's
    ``enable`` allowlist or ``disable`` denylist, then the all-on default.

    :param args: Parsed arguments carrying ``config`` and ``exclude``.
    :raises ConfigError: If the config is invalid.
    """
    resolved_config, _ = _resolve(args)
    config_source = str(resolved_config.source_path) if resolved_config.source_path is not None else "default"

    # Each extension's on/off state and the layer that decided it
    print("extensions:")
    for name in registry.EXTENSION_NAMES:
        if name in args.exclude:
            status, source = "off", "--exclude"
        elif resolved_config.enable is not None:
            status, source = ("on" if name in resolved_config.enable else "off"), config_source
        elif name in resolved_config.disable:
            status, source = "off", config_source
        else:
            status, source = "on", "default"
        print(f"  {name}: {status} ({source})")

    warn_source = resolved_config.sources.get("warn", "default")
    print(f"warn: {str(resolved_config.warn).lower()} ({warn_source})")

    # The load mode of every embed that takes one
    print("load:")
    load_embeds = [name for name in registry.EXTENSION_NAMES if "load" in registry.OPTION_NAMES[name]]
    for extension_name in load_embeds:
        extension_options = resolved_config.options.get(extension_name, {})
        load = extension_options.get("load", LOAD_EAGER)
        source = resolved_config.sources[extension_name] if "load" in extension_options else "default"
        print(f"  {extension_name}: {load} ({source})")

    # Every option table, with its source
    if not resolved_config.options:
        print("options: none")
        return
    print("options:")
    for extension_name, option_table in resolved_config.options.items():
        print(f"  {extension_name}: {option_table} ({resolved_config.sources.get(extension_name, 'default')})")


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
    if issubclass(category, ConfigWarning | RenderWarning):
        print(f"mw: warning: {message}", file=sys.stderr)
    else:
        sys.stderr.write(warnings.formatwarning(message, category, filename, lineno, line))


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and dispatch to the selected subcommand.

    The CLI is the boundary where exceptions become exit codes: a :class:`ConfigError`, an
    :class:`OptionError`, a :class:`ConfigWarning` escalated to an error (``python -W error``), or a
    stdin or stdout failure (input that is not UTF-8, a closed stream, a broken pipe) prints one
    ``mw: error:`` line and exits ``2``. stdin and stdout are UTF-8 whatever the locale says.

    :param argv: Argument vector, or ``None`` to read from ``sys.argv``.
    :returns: Process exit code (``0`` success, ``2`` usage error).
    """
    _use_utf8_stdio()
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
                    for name, stages in registry.describe():
                        print(f"{name}: {', '.join(stages)}")
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
        except (ConfigError, OptionError, ConfigWarning, _StreamError) as usage_error:
            print(f"mw: error: {usage_error}", file=sys.stderr)
            return 2
    return 0
