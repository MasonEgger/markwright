# ABOUTME: Tests for the load option (eager, lazy, click) on the youtube, codepen, twitter, and instagram embeds.
# Pins the click-to-load preview contract, eager byte-parity, and script injection on mixed pages.

from __future__ import annotations

# Callable appears only in annotations, but pydantic resolves EmbedCase's field annotations at runtime
from collections.abc import Callable  # noqa: TC003

import markdown
import pytest
from pydantic import BaseModel, ConfigDict

from markwright import OptionError, codepen, instagram, twitter, youtube


class EmbedCase(BaseModel):
    """One embed's source line and the click-to-load preview fields it should produce.

    :ivar name: The extension name.
    :ivar source: A standalone embed directive line.
    :ivar expand_source: The extension's source-stage function.
    :ivar script_src: The provider script URL the preview names, or ``None`` when it needs no script.
    :ivar provider: The preview's provider text.
    :ivar action: The load button text.
    :ivar link_href: The direct link to the original content.
    :ivar link_text: The direct link text.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    source: str
    expand_source: Callable[..., str]
    script_src: str | None
    provider: str
    action: str
    link_href: str
    link_text: str


EMBED_CASES = [
    EmbedCase(
        name="youtube",
        source="[youtube dQw4w9WgXcQ]",
        expand_source=youtube.expand_source,
        script_src=None,
        provider="YouTube video",
        action="Load video",
        link_href="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        link_text="Watch on YouTube",
    ),
    EmbedCase(
        name="codepen",
        source="[codepen MattCowley vwPzeX]",
        expand_source=codepen.expand_source,
        script_src="https://static.codepen.io/assets/embed/ei.js",
        provider="CodePen",
        action="Load pen",
        link_href="https://codepen.io/MattCowley/pen/vwPzeX",
        link_text="View on CodePen",
    ),
    EmbedCase(
        name="twitter",
        source="[twitter https://x.com/MattIPv4/status/1576415168426573825]",
        expand_source=twitter.expand_source,
        script_src="https://platform.twitter.com/widgets.js",
        provider="X (Twitter) post",
        action="Load post",
        link_href="https://twitter.com/MattIPv4/status/1576415168426573825",
        link_text="View on X",
    ),
    EmbedCase(
        name="instagram",
        source="[instagram https://www.instagram.com/p/CkQuv3_LRgS]",
        expand_source=instagram.expand_source,
        script_src="https://www.instagram.com/embed.js",
        provider="Instagram post",
        action="Load post",
        link_href="https://www.instagram.com/p/CkQuv3_LRgS",
        link_text="View on Instagram",
    ),
]

SCRIPT_EMBEDS = [
    (codepen.apply_html, "[codepen MattCowley vwPzeX]", codepen.expand_source, codepen.CODEPEN_SCRIPT),
    (
        twitter.apply_html,
        "[twitter MattIPv4/status/1576415168426573825]",
        twitter.expand_source,
        twitter.TWITTER_SCRIPT,
    ),
    (instagram.apply_html, "[instagram CkQuv3_LRgS]", instagram.expand_source, instagram.INSTAGRAM_SCRIPT),
]


def render(name: str, source: str, options: dict[str, object] | None = None) -> str:
    """Render Markdown in-process with one embed extension and optional extension config.

    :param name: The extension name.
    :param source: Markdown source.
    :param options: The extension's config, or ``None`` for defaults.
    :returns: The rendered HTML.
    """
    configs = {f"markwright.{name}": options} if options is not None else {}
    instance = markdown.Markdown(extensions=[f"markwright.{name}"], extension_configs=configs)
    return instance.convert(source)


def expected_preview(case: EmbedCase, load: str) -> str:
    """Build the documented click-to-load wrapper around the embed's eager markup.

    :param case: The embed case.
    :param load: The ``data-mw-load`` value.
    :returns: The exact preview HTML the contract specifies.
    """
    eager_markup = case.expand_source(case.source)
    script_attr = f' data-mw-script="{case.script_src}"' if case.script_src is not None else ""
    return (
        f'<div class="mw-embed" data-mw-version="1" data-mw-embed="{case.name}"'
        f' data-mw-load="{load}"{script_attr}>\n'
        f'    <template class="mw-embed-content">{eager_markup}</template>\n'
        f'    <div class="mw-embed-preview">\n'
        f'        <p class="mw-embed-provider">{case.provider}</p>\n'
        f'        <button type="button" class="mw-embed-load">{case.action}</button>\n'
        f'        <a class="mw-embed-link" href="{case.link_href}">{case.link_text}</a>\n'
        f"    </div>\n"
        f"</div>"
    )


@pytest.mark.parametrize("case", EMBED_CASES, ids=lambda case: case.name)
class TestLoadValues:
    """Tests for each load value on every embed that reaches a third party."""

    def test_eager_matches_default_output(self, case: EmbedCase) -> None:
        assert case.expand_source(case.source, {"load": "eager"}) == case.expand_source(case.source)
        assert render(case.name, case.source, {"load": "eager"}) == render(case.name, case.source)

    def test_options_without_load_match_default_output(self, case: EmbedCase) -> None:
        assert case.expand_source(case.source, {}) == case.expand_source(case.source)

    def test_click_emits_the_preview_contract(self, case: EmbedCase) -> None:
        assert case.expand_source(case.source, {"load": "click"}) == expected_preview(case, "click")

    def test_click_in_process_emits_the_preview_contract(self, case: EmbedCase) -> None:
        assert render(case.name, case.source, {"load": "click"}) == expected_preview(case, "click")

    def test_click_template_holds_no_script(self, case: EmbedCase) -> None:
        assert "<script" not in render(case.name, case.source, {"load": "click"})

    def test_unknown_value_raises_in_source_stage(self, case: EmbedCase) -> None:
        with pytest.raises(OptionError, match="load"):
            case.expand_source(case.source, {"load": "sometimes"})

    def test_unknown_value_raises_in_process(self, case: EmbedCase) -> None:
        with pytest.raises(OptionError, match="load"):
            render(case.name, case.source, {"load": "sometimes"})


class TestYouTubeLazy:
    """Tests for youtube's native lazy loading."""

    def test_lazy_adds_loading_attribute_and_nothing_else(self) -> None:
        eager = youtube.expand_source("[youtube dQw4w9WgXcQ]")
        lazy = youtube.expand_source("[youtube dQw4w9WgXcQ]", {"load": "lazy"})
        assert lazy == eager.replace(" allowfullscreen>", ' allowfullscreen loading="lazy">')
        assert lazy != eager

    def test_lazy_in_process_matches_source_stage(self) -> None:
        lazy = render("youtube", "[youtube dQw4w9WgXcQ]", {"load": "lazy"})
        assert lazy == youtube.expand_source("[youtube dQw4w9WgXcQ]", {"load": "lazy"})


@pytest.mark.parametrize("name", ["codepen", "twitter", "instagram"])
class TestScriptEmbedsRejectLazy:
    """Script embeds would need host JS for lazy, which click already covers, so they reject it."""

    def test_lazy_raises(self, name: str) -> None:
        with pytest.raises(OptionError, match="load"):
            render(name, "anything", {"load": "lazy"})


@pytest.mark.parametrize(("apply_html", "source", "expand_source", "script"), SCRIPT_EMBEDS)
class TestScriptInjection:
    """Tests that apply_html injects a provider script only when an eager embed is on the page."""

    def test_click_only_page_injects_no_script(
        self, apply_html: Callable[[str], str], source: str, expand_source: Callable[..., str], script: str
    ) -> None:
        page = expand_source(f"{source}\n\n{source}", {"load": "click"})
        assert apply_html(page) == page

    def test_eager_only_page_injects_one_script(
        self, apply_html: Callable[[str], str], source: str, expand_source: Callable[..., str], script: str
    ) -> None:
        page = expand_source(f"{source}\n\n{source}")
        assert apply_html(page).count(script) == 1

    def test_mixed_page_injects_one_script(
        self, apply_html: Callable[[str], str], source: str, expand_source: Callable[..., str], script: str
    ) -> None:
        page = expand_source(source, {"load": "click"}) + "\n\n" + expand_source(source)
        injected = apply_html(page)
        assert injected.count(script) == 1
        assert apply_html(injected) == injected
