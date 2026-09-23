# ABOUTME: Command-line entry point for the mw markwright pipeline tool.
# Builds the argparse parser and dispatches list/pre/post/render; --version reports the package version.

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

import markdown

from markwright import config, registry
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
    subparser.add_argument("--exclude", action="append", default=[], help="Drop the named extension (repeatable).")


def _run_list() -> int:
    """Print each registered extension and its available stages.

    :returns: Always ``0``.
    """
    for name, stages in registry.describe():
        print(f"{name}: {', '.join(stages)}")
    return 0


def _resolve(args: argparse.Namespace) -> tuple[Config, list[str]] | None:
    """Load config and resolve the active extension names, reporting failures to stderr.

    Selection resolves from config (``enable`` allowlist or ``disable`` denylist) with the
    repeatable CLI ``--exclude`` applied on top. A config error or an unknown extension name
    is reported to stderr and yields ``None`` so the caller returns exit code ``2``.

    :param args: Parsed arguments carrying ``config`` and ``exclude``.
    :returns: The resolved config and selected extension names, or ``None`` on failure.
    """
    explicit_path = Path(args.config) if args.config else None
    try:
        resolved_config = config.load_config(explicit_path, Path.cwd())
    except ConfigError as config_error:
        print(config_error, file=sys.stderr)
        return None
    use = list(resolved_config.enable) if resolved_config.enable is not None else []
    exclude = [*resolved_config.disable, *args.exclude]
    try:
        names = registry.select_extensions(use, exclude)
    except ValueError as selection_error:
        print(selection_error, file=sys.stderr)
        return None
    return resolved_config, names


def _extension_configs(resolved_config: Config, names: list[str]) -> dict[str, dict[str, object]]:
    """Assemble ``markdown.Markdown`` extension configs from the resolved config.

    Each selected ``markwright.*`` extension with a per-extension option table contributes
    it, alongside the fixed ``pymdownx.highlight`` entry that keeps language classes on.

    :param resolved_config: The resolved config carrying per-extension option dicts.
    :param names: The selected extension names.
    :returns: A mapping of extension name to its option dict.
    """
    configs: dict[str, dict[str, object]] = {"pymdownx.highlight": {"pygments_lang_class": True}}
    for name in names:
        options = resolved_config.options.get(name)
        if options:
            configs[f"markwright.{name}"] = options
    return configs


def _run_pre(args: argparse.Namespace) -> int:
    """Expand source directives from stdin and write the result to stdout.

    :param args: Parsed arguments carrying ``config`` and ``exclude``.
    :returns: ``0`` on success, ``2`` if config fails to load or a name is unknown.
    """
    resolved = _resolve(args)
    if resolved is None:
        return 2
    resolved_config, names = resolved
    sys.stdout.write(registry.run_pre(sys.stdin.read(), names, resolved_config.options))
    return 0


def _run_post(args: argparse.Namespace) -> int:
    """Post-process HTML from stdin and write the result to stdout.

    :param args: Parsed arguments carrying ``config``, ``exclude``, and ``warn``.
    :returns: ``0`` on success, ``2`` if config fails to load or a name is unknown.
    """
    resolved = _resolve(args)
    if resolved is None:
        return 2
    _, names = resolved
    warnings: list[str] | None = [] if args.warn else None
    rendered_html = registry.run_post(sys.stdin.read(), names, warnings)
    sys.stdout.write(rendered_html)
    if warnings is not None:
        for warning in warnings:
            print(warning, file=sys.stderr)
    return 0


def _run_render(args: argparse.Namespace) -> int:
    """Render Markdown from stdin to final HTML using the in-process stack.

    Builds a ``markdown.Markdown`` instance configured with ``pymdownx.superfences``
    and ``pymdownx.highlight`` plus the selected ``markwright.*`` extensions, mirroring
    the site stack so fence and highlight render correctly.

    :param args: Parsed arguments carrying ``config`` and ``exclude``.
    :returns: ``0`` on success, ``2`` if config fails to load or a name is unknown.
    """
    resolved = _resolve(args)
    if resolved is None:
        return 2
    resolved_config, names = resolved
    instance = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight", *(f"markwright.{name}" for name in names)],
        extension_configs=_extension_configs(resolved_config, names),
    )
    sys.stdout.write(instance.convert(sys.stdin.read()))
    return 0


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
    if resolved_config.options:
        lines.append("options:")
        for extension_name, option_table in resolved_config.options.items():
            source = resolved_config.sources.get(extension_name, "default")
            lines.append(f"  {extension_name}: {option_table} ({source})")
    else:
        lines.append("options: none")
    return lines


def _run_config(args: argparse.Namespace) -> int:
    """Print the resolved configuration and the source of each value.

    :param args: Parsed arguments carrying ``config`` and ``exclude``.
    :returns: ``0`` on success, ``2`` if config fails to load or a name is unknown.
    """
    resolved = _resolve(args)
    if resolved is None:
        return 2
    resolved_config, _ = resolved
    for line in _format_config(resolved_config, args.exclude):
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and dispatch to the selected subcommand.

    :param argv: Argument vector, or ``None`` to read from ``sys.argv``.
    :returns: Process exit code (``0`` success, ``2`` usage error).
    """
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_error:
        return exit_error.code if isinstance(exit_error.code, int) else 2
    if args.command == "list":
        return _run_list()
    if args.command == "pre":
        return _run_pre(args)
    if args.command == "post":
        return _run_post(args)
    if args.command == "render":
        return _run_render(args)
    if args.command == "config":
        return _run_config(args)
    parser.print_usage()
    return 2
