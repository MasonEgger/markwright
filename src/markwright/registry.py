# ABOUTME: Declarative registry mapping each extension to its stage functions, priorities, and options.
# Drives run_pre, run_post, describe, and the per-extension option names and checks for the mw CLI and config.

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import partial

# Extension is used only in a field annotation, but pydantic resolves those at runtime, so it stays a runtime import
from markdown.extensions import Extension  # noqa: TC002
from pydantic import BaseModel, ConfigDict

from markwright import (
    annotate,
    button,
    codepen,
    fence,
    grid,
    highlight,
    icons,
    image_compare,
    instagram,
    lightbox,
    mermaid,
    slideshow,
    tabs,
    twitter,
    youtube,
)
from markwright._diagnostics import Diagnostic
from markwright._embed_load import load_mode
from markwright._markers import rebase_marker_lines

PreFn = Callable[[str, Mapping[str, object] | None], str]
PostFn = Callable[[str, list[Diagnostic] | None, Mapping[str, object] | None], str]
OptionCheck = Callable[[Mapping[str, object]], object]


class StageSpec(BaseModel):
    """Stage functions, priorities, and options for a single extension.

    :ivar pre: Source-stage transform.
    :ivar post: HTML-stage transform, or ``None`` if the extension has no post stage.
    :ivar pre_priority: Descending order key for the pre stage (higher runs first).
    :ivar post_priority: Descending order key for the post stage (higher runs first).
    :ivar extension: The Python-Markdown extension class; its declared config keys are the options it accepts.
    :ivar check_options: Validator for the extension's option table, raising ``OptionError``, or ``None``
        when the extension takes no options.
    :ivar line_markers: Names of the markers whose ``line`` the pre stage records in its own input,
        so ``run_pre`` rebases them to the source line.
    """

    model_config = ConfigDict(frozen=True)

    pre: PreFn
    post: PostFn | None = None
    pre_priority: int
    post_priority: int = 0
    extension: type[Extension]
    check_options: OptionCheck | None = None
    line_markers: tuple[str, ...] = ()


REGISTRY: dict[str, StageSpec] = {
    "youtube": StageSpec(
        pre=youtube.expand_source,
        pre_priority=20,
        extension=youtube.YouTubeExtension,
        check_options=partial(load_mode, allowed=youtube.LOAD_MODES),
    ),
    "slideshow": StageSpec(pre=slideshow.expand_source, pre_priority=20, extension=slideshow.SlideshowExtension),
    "image_compare": StageSpec(
        pre=image_compare.expand_source, pre_priority=20, extension=image_compare.ImageCompareExtension
    ),
    "codepen": StageSpec(
        pre=codepen.expand_source,
        post=codepen.apply_html,
        pre_priority=20,
        post_priority=15,
        extension=codepen.CodePenExtension,
        check_options=partial(load_mode, allowed=codepen.LOAD_MODES),
    ),
    "twitter": StageSpec(
        pre=twitter.expand_source,
        post=twitter.apply_html,
        pre_priority=20,
        post_priority=15,
        extension=twitter.TwitterExtension,
        check_options=partial(load_mode, allowed=twitter.LOAD_MODES),
    ),
    "instagram": StageSpec(
        pre=instagram.expand_source,
        post=instagram.apply_html,
        pre_priority=20,
        post_priority=15,
        extension=instagram.InstagramExtension,
        check_options=partial(load_mode, allowed=instagram.LOAD_MODES),
    ),
    "fence": StageSpec(
        pre=fence.expand_source,
        post=fence.apply_html,
        pre_priority=40,
        post_priority=25,
        extension=fence.FenceExtension,
        check_options=fence.read_options,
    ),
    "highlight": StageSpec(
        pre=highlight.expand_source,
        post=highlight.apply_html,
        pre_priority=10,
        post_priority=25,
        extension=highlight.HighlightExtension,
    ),
    "button": StageSpec(pre=button.expand_source, pre_priority=20, extension=button.ButtonExtension),
    "lightbox": StageSpec(pre=lightbox.expand_source, pre_priority=20, extension=lightbox.LightboxExtension),
    "mermaid": StageSpec(pre=mermaid.expand_source, pre_priority=45, extension=mermaid.MermaidExtension),
    "icons": StageSpec(
        pre=icons.expand_source,
        pre_priority=5,
        extension=icons.IconsExtension,
        check_options=icons.read_options,
    ),
    "grid": StageSpec(
        pre=grid.expand_source,
        post=grid.apply_html,
        pre_priority=21,
        post_priority=27,
        extension=grid.GridExtension,
        line_markers=(grid.PROBLEM_MARKER_NAME,),
    ),
    "annotate": StageSpec(
        pre=annotate.expand_source,
        post=annotate.apply_html,
        pre_priority=20,
        post_priority=27,
        extension=annotate.AnnotateExtension,
    ),
    "tabs": StageSpec(
        pre=tabs.expand_source,
        post=tabs.apply_html,
        pre_priority=21,
        post_priority=27,
        extension=tabs.TabsExtension,
        line_markers=(tabs.PROBLEM_MARKER_NAME,),
    ),
}

EXTENSION_NAMES: tuple[str, ...] = tuple(REGISTRY)

# Each extension accepts exactly the config keys its Python-Markdown class declares, so an option is declared once
OPTION_NAMES: dict[str, frozenset[str]] = {
    name: frozenset(spec.extension().getConfigs()) for name, spec in REGISTRY.items()
}


def run_pre(
    text: str,
    names: list[str],
    options: Mapping[str, Mapping[str, object]] | None = None,
    line_offset: int = 0,
) -> str:
    """Apply each selected pre-stage transform to ``text`` in descending priority order.

    :param text: Markdown source text.
    :param names: Selected extension names.
    :param options: Per-extension option tables keyed by extension name; each stage receives
        its own table, or ``None`` when it has none.
    :param line_offset: Lines that precede ``text`` in the document (front matter the caller split
        off), added to the source line a problem marker records.
    :returns: Source text after every selected pre stage has run.
    """
    selected = [(name, spec) for name, spec in REGISTRY.items() if name in names]

    source_lines = text.split("\n")

    # A stable sort keeps registry order between stages of equal priority
    for name, spec in sorted(selected, key=lambda entry: entry[1].pre_priority, reverse=True):
        stage_input_lines = text.split("\n")
        text = spec.pre(text, options.get(name) if options is not None else None)
        text = rebase_marker_lines(source_lines, stage_input_lines, text, spec.line_markers, line_offset)
    return text


def run_post(
    html: str,
    names: list[str],
    diagnostics: list[Diagnostic] | None = None,
    options: Mapping[str, Mapping[str, object]] | None = None,
) -> str:
    """Apply each selected post-stage transform to ``html`` in descending priority order.

    :param html: Rendered HTML.
    :param names: Selected extension names.
    :param diagnostics: Optional list collecting diagnostics from stages that validate markers.
    :param options: Per-extension option tables keyed by extension name; each stage receives
        its own table, or ``None`` when it has none.
    :returns: HTML after every selected post stage has run.
    """
    selected = [
        (name, spec.post, spec.post_priority)
        for name, spec in REGISTRY.items()
        if name in names and spec.post is not None
    ]

    # A stable sort keeps registry order between stages of equal priority
    for name, post_fn, _ in sorted(selected, key=lambda entry: entry[2], reverse=True):
        html = post_fn(html, diagnostics, options.get(name) if options is not None else None)
    return html


def describe() -> list[tuple[str, list[str]]]:
    """Report each registered extension and the stages it provides.

    :returns: ``(name, stages)`` pairs in registry order, where ``stages`` is ``["pre"]`` or
        ``["pre", "post"]``.
    """
    return [(name, ["pre", "post"] if spec.post is not None else ["pre"]) for name, spec in REGISTRY.items()]
