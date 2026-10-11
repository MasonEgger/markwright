# ABOUTME: Position-preserving HTML tokenizer for the post stages, built on the stdlib html.parser.
# Post stages locate elements from tokens and edit only those spans, so the rest of the page stays byte-identical.

from __future__ import annotations

import html
from html.parser import HTMLParser
from typing import Literal

from pydantic import BaseModel, ConfigDict

TokenKind = Literal["start", "startend", "end", "text", "comment", "other"]

# Elements whose content the parser reports as raw text, never as markup to style
RAW_TEXT_ELEMENTS = frozenset({"script", "style"})


class HtmlToken(BaseModel):
    """One construct of an HTML document and where it sits in the source.

    :ivar kind: ``start``, ``startend`` (self-closing), ``end``, ``text``, ``comment``, or ``other``
        (a doctype, processing instruction, or CDATA declaration).
    :ivar tag: The lowercased tag name for tag tokens, empty otherwise.
    :ivar attrs: The tag's attributes in source order, values unescaped; ``None`` for a bare attribute.
    :ivar start: Offset of the token's first character in the source.
    :ivar end: Offset just past the token's last character.
    """

    model_config = ConfigDict(frozen=True)

    kind: TokenKind
    tag: str = ""
    attrs: tuple[tuple[str, str | None], ...] = ()
    start: int
    end: int

    def attribute(self, name: str) -> str | None:
        """Return an attribute's value, or ``None`` when the tag lacks it or it is bare.

        :param name: The lowercased attribute name.
        :returns: The unescaped attribute value, or ``None``.
        """
        return next((value for attr_name, value in self.attrs if attr_name == name), None)

    def has_class(self, class_name: str) -> bool:
        """Report whether the tag's ``class`` attribute lists a class.

        :param class_name: The class to look for.
        :returns: ``True`` if ``class_name`` is one of the tag's classes.
        """
        return class_name in (self.attribute("class") or "").split()


class _Tokenizer(HTMLParser):
    """Collect parser events with their source offsets.

    :param source: The HTML being tokenized, used to turn ``getpos`` line and column pairs into offsets.
    """

    def __init__(self, source: str) -> None:
        # Keep entity references raw, so text tokens hold exactly the source characters
        super().__init__(convert_charrefs=False)
        # getpos counts lines by "\n" alone, so the offset table must too (str.splitlines also splits on "\r")
        self.line_offsets = [0]
        for line in source.split("\n"):
            self.line_offsets.append(self.line_offsets[-1] + len(line) + 1)
        self.events: list[tuple[TokenKind, str, list[tuple[str, str | None]], int]] = []

    def _record(self, kind: TokenKind, tag: str = "", attrs: list[tuple[str, str | None]] | None = None) -> None:
        """Record an event at the parser's current position, which is the start of the construct.

        :param kind: The token kind.
        :param tag: The tag name, for tag events.
        :param attrs: The tag's attributes, for start tags.
        """
        line_number, column = self.getpos()
        self.events.append((kind, tag, attrs or [], self.line_offsets[line_number - 1] + column))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record a start tag.

        :param tag: The lowercased tag name.
        :param attrs: The tag's attributes.
        """
        self._record("start", tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record a self-closing tag.

        :param tag: The lowercased tag name.
        :param attrs: The tag's attributes.
        """
        self._record("startend", tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        """Record an end tag.

        :param tag: The lowercased tag name.
        """
        self._record("end", tag)

    def handle_data(self, data: str) -> None:
        """Record a run of text.

        :param data: The text; its span comes from the source offsets.
        """
        self._record("text")

    def handle_entityref(self, name: str) -> None:
        """Record a named entity reference as text.

        :param name: The entity name.
        """
        self._record("text")

    def handle_charref(self, name: str) -> None:
        """Record a numeric character reference as text.

        :param name: The reference number.
        """
        self._record("text")

    def handle_comment(self, data: str) -> None:
        """Record a comment.

        :param data: The comment body.
        """
        self._record("comment")

    def handle_decl(self, decl: str) -> None:
        """Record a doctype declaration.

        :param decl: The declaration body.
        """
        self._record("other")

    def handle_pi(self, data: str) -> None:
        """Record a processing instruction.

        :param data: The instruction body.
        """
        self._record("other")

    def unknown_decl(self, data: str) -> None:
        """Record a CDATA or other marked section.

        :param data: The section body.
        """
        self._record("other")


def tokenize(source: str) -> list[HtmlToken]:
    """Split HTML into tokens that cover the source end to end.

    Adjacent text, entity, and character-reference events merge into one text token, so a text
    token's span is exactly the raw characters between two pieces of markup.

    :param source: The HTML to tokenize.
    :returns: Tokens in source order; their spans are contiguous and cover all of ``source``.
    """
    tokenizer = _Tokenizer(source)
    tokenizer.feed(source)
    tokenizer.close()

    tokens: list[HtmlToken] = []
    events = tokenizer.events
    for event_index, (kind, tag, attrs, start) in enumerate(events):
        end = events[event_index + 1][3] if event_index + 1 < len(events) else len(source)
        if kind == "text" and tokens and tokens[-1].kind == "text":
            tokens[-1] = tokens[-1].model_copy(update={"end": end})
        else:
            tokens.append(HtmlToken(kind=kind, tag=tag, attrs=tuple(attrs), start=start, end=end))
    return tokens


def render_start_tag(tag: str, attrs: tuple[tuple[str, str | None], ...]) -> str:
    """Serialize a start tag from its name and attributes, double-quoting and escaping each value.

    :param tag: The tag name.
    :param attrs: The attributes in output order; ``None`` renders a bare attribute.
    :returns: The start tag, for example ``<pre class="chroma">``.
    """
    rendered_attrs = "".join(
        f' {name}="{html.escape(value)}"' if value is not None else f" {name}" for name, value in attrs
    )
    return f"<{tag}{rendered_attrs}>"


def apply_edits(source: str, edits: list[tuple[int, int, str]]) -> str:
    """Replace non-overlapping spans of ``source``.

    :param source: The original text.
    :param edits: ``(start, end, replacement)`` triples; an insertion has ``start == end``.
    :returns: The text with every span replaced.
    """
    # Apply back to front so earlier offsets stay valid
    for start, end, replacement in sorted(edits, key=lambda edit: (edit[0], edit[1]), reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


def provider_script_needed(rendered_html: str, embed_class: str, script_src: str) -> bool:
    """Report whether a page needs a provider script appended.

    It does when at least one element with ``embed_class`` sits outside every ``<template>`` (an eager
    embed; nothing inside a template, such as a click-to-load preview's live markup, is live) and no
    ``<script>`` already loads ``script_src``.

    :param rendered_html: Rendered HTML content.
    :param embed_class: The embed's class, for example ``twitter-tweet``.
    :param script_src: The provider script URL.
    :returns: ``True`` if the script should be appended.
    """
    template_depth = 0
    has_eager_embed = False
    for token in tokenize(rendered_html):
        if token.kind == "start" and token.tag == "script" and token.attribute("src") == script_src:
            return False
        if token.kind == "start" and token.tag == "template":
            template_depth += 1
        elif token.kind == "end" and token.tag == "template" and template_depth:
            template_depth -= 1
        elif token.kind in ("start", "startend") and not template_depth and token.has_class(embed_class):
            has_eager_embed = True
    return has_eager_embed
