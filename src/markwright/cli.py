# ABOUTME: Command-line entry point for the mw markwright pipeline tool.
# Builds the argparse parser and dispatches list/pre/post/render; --version reports the package version.

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version

import markdown

from markwright import registry


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
    return parser


def _add_selection_flags(subparser: argparse.ArgumentParser) -> None:
    """Add the shared ``--use`` and ``--exclude`` selection flags to a subparser.

    :param subparser: The subcommand parser to extend.
    """
    subparser.add_argument("--use", action="append", default=[], help="Restrict to the named extension (repeatable).")
    subparser.add_argument("--exclude", action="append", default=[], help="Drop the named extension (repeatable).")


def _run_list() -> int:
    """Print each registered extension and its available stages.

    :returns: Always ``0``.
    """
    for name, stages in registry.describe():
        print(f"{name}: {', '.join(stages)}")
    return 0


def _resolve_selection(args: argparse.Namespace) -> list[str] | None:
    """Resolve the active extension names, reporting unknown names to stderr.

    :param args: Parsed arguments carrying ``use`` and ``exclude`` lists.
    :returns: Selected extension names, or ``None`` if a name is unknown (the
        caller should then return exit code ``2``).
    """
    try:
        return registry.select_extensions(args.use, args.exclude)
    except ValueError as selection_error:
        print(selection_error, file=sys.stderr)
        return None


def _run_pre(args: argparse.Namespace) -> int:
    """Expand source directives from stdin and write the result to stdout.

    :param args: Parsed arguments carrying ``use`` and ``exclude``.
    :returns: ``0`` on success, ``2`` if a selected extension name is unknown.
    """
    names = _resolve_selection(args)
    if names is None:
        return 2
    sys.stdout.write(registry.run_pre(sys.stdin.read(), names))
    return 0


def _run_post(args: argparse.Namespace) -> int:
    """Post-process HTML from stdin and write the result to stdout.

    :param args: Parsed arguments carrying ``use``, ``exclude``, and ``warn``.
    :returns: ``0`` on success, ``2`` if a selected extension name is unknown.
    """
    names = _resolve_selection(args)
    if names is None:
        return 2
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

    :param args: Parsed arguments carrying ``use`` and ``exclude``.
    :returns: ``0`` on success, ``2`` if a selected extension name is unknown.
    """
    names = _resolve_selection(args)
    if names is None:
        return 2
    instance = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight", *(f"markwright.{name}" for name in names)],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
    )
    sys.stdout.write(instance.convert(sys.stdin.read()))
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
    parser.print_usage()
    return 2
