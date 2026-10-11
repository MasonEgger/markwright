# ABOUTME: Declarative registry mapping each extension to its pre/post stage functions.
# Drives run_pre, run_post, describe, and per-extension option names and checks for the mw CLI and config.

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import partial
from typing import TypedDict

from markdown.extensions import Extension

from markwright._embed_load import load_mode
from markwright.codepen import LOAD_MODES as CODEPEN_LOAD_MODES
from markwright.codepen import apply_html as codepen_post
from markwright.codepen import expand_source as codepen_pre
from markwright.codepen import makeExtension as codepen_extension
from markwright.fence import apply_html as fence_post
from markwright.fence import expand_source as fence_pre
from markwright.fence import makeExtension as fence_extension
from markwright.fence import read_options as fence_options
from markwright.highlight import apply_html as highlight_post
from markwright.highlight import expand_source as highlight_pre
from markwright.highlight import makeExtension as highlight_extension
from markwright.image_compare import expand_source as image_compare_pre
from markwright.image_compare import makeExtension as image_compare_extension
from markwright.instagram import LOAD_MODES as INSTAGRAM_LOAD_MODES
from markwright.instagram import apply_html as instagram_post
from markwright.instagram import expand_source as instagram_pre
from markwright.instagram import makeExtension as instagram_extension
from markwright.slideshow import expand_source as slideshow_pre
from markwright.slideshow import makeExtension as slideshow_extension
from markwright.twitter import LOAD_MODES as TWITTER_LOAD_MODES
from markwright.twitter import apply_html as twitter_post
from markwright.twitter import expand_source as twitter_pre
from markwright.twitter import makeExtension as twitter_extension
from markwright.youtube import LOAD_MODES as YOUTUBE_LOAD_MODES
from markwright.youtube import expand_source as youtube_pre
from markwright.youtube import makeExtension as youtube_extension

PreFn = Callable[[str, Mapping[str, object] | None], str]
PostFn = Callable[[str, list[str] | None, Mapping[str, object] | None], str]
OptionCheck = Callable[[Mapping[str, object]], object]


class StageSpec(TypedDict):
    """Stage functions and priorities for a single extension.

    :ivar pre: Source-stage transform, or ``None`` if the extension has no pre stage.
    :ivar post: HTML-stage transform, or ``None`` if the extension has no post stage.
    :ivar pre_priority: Descending order key for the pre stage (higher runs first).
    :ivar post_priority: Descending order key for the post stage (higher runs first).
    """

    pre: PreFn | None
    post: PostFn | None
    pre_priority: int
    post_priority: int


REGISTRY: dict[str, StageSpec] = {
    "youtube": {"pre": youtube_pre, "post": None, "pre_priority": 20, "post_priority": 0},
    "slideshow": {"pre": slideshow_pre, "post": None, "pre_priority": 20, "post_priority": 0},
    "image_compare": {"pre": image_compare_pre, "post": None, "pre_priority": 20, "post_priority": 0},
    "codepen": {"pre": codepen_pre, "post": codepen_post, "pre_priority": 20, "post_priority": 15},
    "twitter": {"pre": twitter_pre, "post": twitter_post, "pre_priority": 20, "post_priority": 15},
    "instagram": {"pre": instagram_pre, "post": instagram_post, "pre_priority": 20, "post_priority": 15},
    "fence": {"pre": fence_pre, "post": fence_post, "pre_priority": 40, "post_priority": 25},
    "highlight": {"pre": highlight_pre, "post": highlight_post, "pre_priority": 10, "post_priority": 25},
}

EXTENSION_NAMES: tuple[str, ...] = tuple(REGISTRY)

# Python-Markdown extension factories; each extension's declared config keys are the options it accepts.
_EXTENSION_FACTORIES: dict[str, Callable[[], Extension]] = {
    "youtube": youtube_extension,
    "slideshow": slideshow_extension,
    "image_compare": image_compare_extension,
    "codepen": codepen_extension,
    "twitter": twitter_extension,
    "instagram": instagram_extension,
    "fence": fence_extension,
    "highlight": highlight_extension,
}

OPTION_NAMES: dict[str, frozenset[str]] = {
    name: frozenset(factory().getConfigs()) for name, factory in _EXTENSION_FACTORIES.items()
}

# Validators for the extensions that take options; each raises OptionError naming the bad option.
OPTION_CHECKS: dict[str, OptionCheck] = {
    "youtube": partial(load_mode, allowed=YOUTUBE_LOAD_MODES),
    "codepen": partial(load_mode, allowed=CODEPEN_LOAD_MODES),
    "twitter": partial(load_mode, allowed=TWITTER_LOAD_MODES),
    "instagram": partial(load_mode, allowed=INSTAGRAM_LOAD_MODES),
    "fence": fence_options,
}


def _ordered(
    names: list[str],
    get_stage: Callable[[StageSpec], PreFn | PostFn | None],
    get_priority: Callable[[StageSpec], int],
) -> list[str]:
    """Return selected names that have the given stage, ordered by descending priority.

    :param names: Selected extension names.
    :param get_stage: Accessor returning the stage function (or ``None``) for a spec.
    :param get_priority: Accessor returning the stage priority for a spec.
    :returns: Names with a non-``None`` stage function, highest priority first.
    """
    selected = [name for name in EXTENSION_NAMES if name in names and get_stage(REGISTRY[name]) is not None]
    return sorted(selected, key=lambda name: get_priority(REGISTRY[name]), reverse=True)


def run_pre(text: str, names: list[str], options: Mapping[str, Mapping[str, object]] | None = None) -> str:
    """Apply each selected pre-stage transform to ``text`` in descending priority order.

    :param text: Markdown source text.
    :param names: Selected extension names.
    :param options: Per-extension option tables keyed by extension name; each stage receives
        its own table, or ``None`` when it has none.
    :returns: Source text after every selected pre stage has run.
    """
    for name in _ordered(names, lambda spec: spec["pre"], lambda spec: spec["pre_priority"]):
        pre_fn = REGISTRY[name]["pre"]
        assert pre_fn is not None
        text = pre_fn(text, options.get(name) if options is not None else None)
    return text


def run_post(
    html: str,
    names: list[str],
    warnings: list[str] | None = None,
    options: Mapping[str, Mapping[str, object]] | None = None,
) -> str:
    """Apply each selected post-stage transform to ``html`` in descending priority order.

    :param html: Rendered HTML.
    :param names: Selected extension names.
    :param warnings: Optional list collecting skip reasons from stages that validate markers.
    :param options: Per-extension option tables keyed by extension name; each stage receives
        its own table, or ``None`` when it has none.
    :returns: HTML after every selected post stage has run.
    """
    for name in _ordered(names, lambda spec: spec["post"], lambda spec: spec["post_priority"]):
        post_fn = REGISTRY[name]["post"]
        assert post_fn is not None
        html = post_fn(html, warnings, options.get(name) if options is not None else None)
    return html


def describe() -> list[tuple[str, list[str]]]:
    """Report each registered extension and the stages it provides.

    :returns: ``(name, stages)`` pairs in registry order, where ``stages`` lists
        ``"pre"`` and/or ``"post"`` depending on which stage functions exist.
    """
    described: list[tuple[str, list[str]]] = []
    for name in EXTENSION_NAMES:
        stages: list[str] = []
        if REGISTRY[name]["pre"] is not None:
            stages.append("pre")
        if REGISTRY[name]["post"] is not None:
            stages.append("post")
        described.append((name, stages))
    return described
