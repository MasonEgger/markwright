# ABOUTME: Declarative registry mapping each extension to its stage functions, priorities, and options.
# Drives run_pre, run_post, describe, and the per-extension option names and checks for the mw CLI and config.

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import partial

# Extension is used only in a field annotation, but pydantic resolves those at runtime, so it stays a runtime import
from markdown.extensions import Extension  # noqa: TC002
from pydantic import BaseModel, ConfigDict

from markwright import (
    button,
    codepen,
    fence,
    highlight,
    icons,
    image_compare,
    instagram,
    lightbox,
    mermaid,
    slideshow,
    twitter,
    youtube,
)
from markwright._embed_load import load_mode

PreFn = Callable[[str, Mapping[str, object] | None], str]
PostFn = Callable[[str, list[str] | None, Mapping[str, object] | None], str]
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
    """

    model_config = ConfigDict(frozen=True)

    pre: PreFn
    post: PostFn | None = None
    pre_priority: int
    post_priority: int = 0
    extension: type[Extension]
    check_options: OptionCheck | None = None


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
        pre_priority=50,
        extension=icons.IconsExtension,
        check_options=icons.read_options,
    ),
}

EXTENSION_NAMES: tuple[str, ...] = tuple(REGISTRY)

# Each extension accepts exactly the config keys its Python-Markdown class declares, so an option is declared once
OPTION_NAMES: dict[str, frozenset[str]] = {
    name: frozenset(spec.extension().getConfigs()) for name, spec in REGISTRY.items()
}


def run_pre(text: str, names: list[str], options: Mapping[str, Mapping[str, object]] | None = None) -> str:
    """Apply each selected pre-stage transform to ``text`` in descending priority order.

    :param text: Markdown source text.
    :param names: Selected extension names.
    :param options: Per-extension option tables keyed by extension name; each stage receives
        its own table, or ``None`` when it has none.
    :returns: Source text after every selected pre stage has run.
    """
    selected = [(name, spec) for name, spec in REGISTRY.items() if name in names]

    # A stable sort keeps registry order between stages of equal priority
    for name, spec in sorted(selected, key=lambda entry: entry[1].pre_priority, reverse=True):
        text = spec.pre(text, options.get(name) if options is not None else None)
    return text


def run_post(
    html: str,
    names: list[str],
    skip_reasons: list[str] | None = None,
    options: Mapping[str, Mapping[str, object]] | None = None,
) -> str:
    """Apply each selected post-stage transform to ``html`` in descending priority order.

    :param html: Rendered HTML.
    :param names: Selected extension names.
    :param skip_reasons: Optional list collecting skip reasons from stages that validate markers.
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
        html = post_fn(html, skip_reasons, options.get(name) if options is not None else None)
    return html


def describe() -> list[tuple[str, list[str]]]:
    """Report each registered extension and the stages it provides.

    :returns: ``(name, stages)`` pairs in registry order, where ``stages`` is ``["pre"]`` or
        ``["pre", "post"]``.
    """
    return [(name, ["pre", "post"] if spec.post is not None else ["pre"]) for name, spec in REGISTRY.items()]
