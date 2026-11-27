# ABOUTME: End-to-end integration test driving mw as a pre/post processor around a real Hugo build.
# Skipped unless both the mw console script and the hugo binary are on PATH; marked `integration`.

from __future__ import annotations

import itertools
import re
import shutil
import subprocess
from typing import TYPE_CHECKING

import markdown
import pytest

from markwright import registry

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.integration

MW = shutil.which("mw")
HUGO = shutil.which("hugo")

requires_tools = pytest.mark.skipif(
    MW is None or HUGO is None,
    reason="needs the mw console script and the hugo binary on PATH",
)

# Source exercising every stage: embeds (pre), prose highlight (pre), a command fence
# whose prefix wrapping must survive Chroma (the regression this test guards), and a
# line-numbers fence.
SOURCE = """\
[youtube dQw4w9WgXcQ]

[codepen MattCowley vwPzeX]

A <^>highlighted<^> word.

```command
[label deploy.sh]
./deploy.sh --prod
```

```line_numbers
alpha
beta
gamma
```
"""

# The 0.4.0 constructs: button, lightbox, mermaid, grid, both annotate forms, and an icon.
# The annotate code case uses bash so Chroma emits a comment token around the marker.
MATERIAL_SOURCE = """\
[button primary /start Get started]

[lightbox /a.png A diagram]

```mermaid
graph LR
    A --> B
```

[grid cards]

- card one
- card two

[annotate]
```bash
./deploy.sh --prod # (1)!
```

1. The first note.

[annotate]
Prose with a marker (1).

1. A prose note.

A :demo-check: icon.
"""

# The container constructs: a block grid with a column count and two cards, then a two-tab set.
# The first card holds a fenced code block so the build proves a Chroma-highlighted block sits
# inside a wrapped card without breaking the grid/card pairing (the reason this file uses Hugo and
# not the in-process Pygments round trip).
CONTAINERS_SOURCE = """\
[grid cards 2]

[card]

### Alpha

The first card, with a Chroma-highlighted block.

```python
print("hello")
```

[/card]

[card]

### Beta

The second card.

[/card]

[/grid]

[tab First]

The first tab body.

[/tab]

[tab Second]

The second tab body.

[/tab]
"""

# Two container problems left literal: a [card] outside any grid (a grid problem) and an unclosed
# [tab] (a tab problem). mw pre attaches an inline problem marker to each; mw post --warn removes
# the markers, keeps the literal directives, and reports each problem once on stderr.
CONTAINER_PROBLEMS_SOURCE = """\
[card]

A stray card outside any grid.

[/card]

[tab Lonely]

This tab never closes.
"""

# Goldmark must pass raw HTML and the mw-fence comment through (unsafe), and Chroma
# must emit CSS classes (noClasses = false) so the highlight markup carries class hooks.
HUGO_CONFIG = """\
baseURL = "https://example.org/"
title = "mw integration"
disableKinds = ["taxonomy", "term", "sitemap", "robotsTXT", "RSS", "404"]

[markup.goldmark.renderer]
unsafe = true

[markup.highlight]
noClasses = false
"""

SINGLE_LAYOUT = "<!DOCTYPE html><html><body>\n{{ .Content }}\n</body></html>"


# The warn path (mw post --warn) reports container problems on stderr, so the runner returns the
# whole process and _run_mw keeps the stdout-only shape every other test uses.
def _run_mw_process(args: list[str], stdin_text: str) -> subprocess.CompletedProcess[str]:
    assert MW is not None
    return subprocess.run(
        [MW, *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        check=True,
    )


def _run_mw(args: list[str], stdin_text: str) -> str:
    return _run_mw_process(args, stdin_text).stdout


@requires_tools
def test_pre_render_post_pipeline_through_hugo(tmp_path: Path) -> None:
    assert HUGO is not None
    site = tmp_path / "site"
    (site / "content").mkdir(parents=True)
    (site / "layouts" / "_default").mkdir(parents=True)
    (site / "hugo.toml").write_text(HUGO_CONFIG)
    (site / "layouts" / "_default" / "single.html").write_text(SINGLE_LAYOUT)

    # 1. pre: expand embeds, resolve prose highlight, extract fence directives.
    pre_md = _run_mw(["pre"], SOURCE)
    (site / "content" / "page.md").write_text('+++\ntitle = "Page"\n+++\n\n' + pre_md)

    # 2. Hugo (Goldmark + Chroma) renders the markdown to HTML.
    subprocess.run([HUGO, "--quiet"], cwd=site, check=True)
    rendered = (site / "public" / "page" / "index.html").read_text()
    assert "mw-fence" in rendered, "Goldmark with unsafe=true must preserve the marker comment"

    # 3. post: apply fence styling, in-code highlight, and script injection.
    final = _run_mw(["post"], rendered)

    # Embeds survived the render.
    assert "youtube.com/embed/dQw4w9WgXcQ" in final
    assert 'class="codepen"' in final
    assert final.count("static.codepen.io/assets/embed/ei.js") == 1
    # Fence styling applied from the marker.
    assert '<div class="code-label" title="deploy.sh">deploy.sh</div>' in final
    # Prose highlight.
    assert "<mark>highlighted</mark>" in final
    # The Chroma prefix regression: exactly one prefixed <li> for the one-line command.
    assert final.count('<li data-prefix="$">') == 1
    # line_numbers fence: three numbered lines, no fourth.
    assert 'data-prefix="1"' in final
    assert 'data-prefix="3"' in final
    assert 'data-prefix="4"' not in final
    # The marker comment is consumed by post.
    assert "<!-- mw-fence" not in final


@requires_tools
def test_click_to_load_preview_survives_hugo(tmp_path: Path) -> None:
    assert HUGO is not None
    site = tmp_path / "site"
    (site / "content").mkdir(parents=True)
    (site / "layouts" / "_default").mkdir(parents=True)
    (site / "hugo.toml").write_text(HUGO_CONFIG)
    (site / "layouts" / "_default" / "single.html").write_text(SINGLE_LAYOUT)
    config_path = tmp_path / "markwright.toml"
    config_path.write_text('[youtube]\nload = "click"\n\n[twitter]\nload = "click"\n')
    source = "[youtube dQw4w9WgXcQ]\n\n[twitter MattIPv4/status/1576415168426573825]\n\n[codepen MattCowley vwPzeX]\n"

    pre_md = _run_mw(["pre", "--config", str(config_path)], source)
    (site / "content" / "page.md").write_text('+++\ntitle = "Page"\n+++\n\n' + pre_md)
    subprocess.run([HUGO, "--quiet"], cwd=site, check=True)
    rendered = (site / "public" / "page" / "index.html").read_text()
    final = _run_mw(["post", "--config", str(config_path)], rendered)

    # Goldmark passes both previews through with the live markup still inside <template>.
    assert final.count('<div class="mw-embed"') == 2
    assert '<template class="mw-embed-content"><iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"' in final
    assert '<template class="mw-embed-content"><div class="twitter">' in final
    # Only the eager CodePen embed gets its provider script.
    assert 'platform.twitter.com/widgets.js"></script>' not in final
    assert final.count('static.codepen.io/assets/embed/ei.js" type=') == 1


@requires_tools
def test_indented_and_list_item_fences_survive_hugo(tmp_path: Path) -> None:
    assert HUGO is not None
    site = tmp_path / "site"
    (site / "content").mkdir(parents=True)
    (site / "layouts" / "_default").mkdir(parents=True)
    (site / "hugo.toml").write_text(HUGO_CONFIG)
    (site / "layouts" / "_default" / "single.html").write_text(SINGLE_LAYOUT)
    source = (
        "- item\n\n    ```bash\n    [label a.sh]\n    [environment local]\n    echo hi\n    ```\n\n"
        "  ```command\n  [label b.sh]\n  ls\n  ```\n"
    )

    pre_md = _run_mw(["pre"], source)
    (site / "content" / "page.md").write_text('+++\ntitle = "Page"\n+++\n\n' + pre_md)
    subprocess.run([HUGO, "--quiet"], cwd=site, check=True)
    final = _run_mw(["post"], (site / "public" / "page" / "index.html").read_text())

    # Both fences get their directives applied; none is left as literal code text
    assert '<div class="code-label" title="a.sh">a.sh</div>' in final
    assert '<div class="code-label" title="b.sh">b.sh</div>' in final
    assert 'class="environment-local chroma"' in final
    assert 'class="prefixed command chroma"' in final
    assert "[label" not in final


def _pipeline_through_hugo(tmp_path: Path, source: str) -> str:
    """Run ``source`` through ``mw pre``, a Hugo build, and ``mw post``.

    :param tmp_path: A scratch directory for the Hugo site.
    :param source: Markdown source text.
    :returns: The final HTML of the built page.
    """
    assert HUGO is not None
    site = tmp_path / "site"
    (site / "content").mkdir(parents=True)
    (site / "layouts" / "_default").mkdir(parents=True)
    (site / "hugo.toml").write_text(HUGO_CONFIG)
    (site / "layouts" / "_default" / "single.html").write_text(SINGLE_LAYOUT)
    (site / "content" / "page.md").write_text('+++\ntitle = "Page"\n+++\n\n' + _run_mw(["pre"], source))
    subprocess.run([HUGO, "--quiet"], cwd=site, check=True)
    return _run_mw(["post"], (site / "public" / "page" / "index.html").read_text())


@requires_tools
def test_block_quote_fence_survives_hugo(tmp_path: Path) -> None:
    source = (
        "> [!NOTE]\n> Run this:\n> ```command\n> [label restart.sh]\n"
        "> systemctl restart <^>nginx<^>\n> ```\n> Then check it.\n"
    )

    final = _pipeline_through_hugo(tmp_path, source)

    # The label, the prefix, and the in-code highlight all land inside the quote
    quote_end = final.index("</blockquote>")
    assert final.index('<div class="code-label" title="restart.sh">restart.sh</div>') < quote_end
    assert final.index('class="prefixed command chroma"') < quote_end
    assert final.index("<mark>nginx</mark>") < quote_end
    assert "[label" not in final
    assert "mw-fence" not in final


def _mindmap_fence(indent: str, leaf: str) -> str:
    """Build a mermaid fence whose text has a blank line and two levels of its own indentation.

    :param indent: The indentation of every line of the fence.
    :param leaf: The text of the deepest node, which names the diagram in the output.
    :returns: The fence, ending with a blank line.
    """
    lines = ["```mermaid", "mindmap", "", "  root", f"    {leaf}", "```"]
    return "".join(f"{indent}{line}\n" if line else "\n" for line in lines) + "\n"


@requires_tools
def test_mermaid_fence_at_the_column_hugo_strips_keeps_its_exact_text(tmp_path: Path) -> None:
    source = (
        _mindmap_fence("", "top")
        + "- item\n\n"
        + _mindmap_fence("  ", "bullet")
        + "1. item\n\n"
        + _mindmap_fence("   ", "ordered")
        + "para\n\n1. - a\n\n"
        + _mindmap_fence("     ", "nested")
        + "Term\n: definition\n\n"
        + _mindmap_fence("  ", "defined")
    )

    final = _pipeline_through_hugo(tmp_path, source)

    assert final.count('<pre class="mermaid">') == 5
    for leaf in ("top", "bullet", "ordered", "nested", "defined"):
        assert f'<pre class="mermaid">mindmap\n\n  root\n    {leaf}\n</pre>' in final


@requires_tools
def test_mermaid_fence_past_the_column_hugo_strips_keeps_the_rest_of_its_indent(tmp_path: Path) -> None:
    source = (
        _mindmap_fence("  ", "top")
        + "1. item\n\n"
        + _mindmap_fence("    ", "ordered")
        + "para\n\n1. - a\n\n"
        + _mindmap_fence("      ", "nested")
        + "para\n\n100. - a\n\n"
        + _mindmap_fence("        ", "wide")
    )

    final = _pipeline_through_hugo(tmp_path, source)

    assert final.count('<pre class="mermaid">') == 4
    assert '  <pre class="mermaid">mindmap\n\n    root\n      top\n  </pre>' in final
    for leaf in ("ordered", "nested", "wide"):
        assert f' <pre class="mermaid">mindmap\n\n   root\n     {leaf}\n </pre>' in final


@requires_tools
def test_material_parity_directives_survive_hugo(tmp_path: Path) -> None:
    assert HUGO is not None
    site = tmp_path / "site"
    (site / "content").mkdir(parents=True)
    (site / "layouts" / "_default").mkdir(parents=True)
    (site / "hugo.toml").write_text(HUGO_CONFIG)
    (site / "layouts" / "_default" / "single.html").write_text(SINGLE_LAYOUT)
    pack = tmp_path / "demo"
    pack.mkdir()
    (pack / "check.svg").write_text('<svg viewBox="0 0 24 24"><path d="M1 1h22v22H1z"/></svg>')
    config_path = tmp_path / "markwright.toml"
    config_path.write_text(f'[icons.packs]\ndemo = "{pack}"\n')

    pre_md = _run_mw(["pre", "--config", str(config_path)], MATERIAL_SOURCE)
    (site / "content" / "page.md").write_text('+++\ntitle = "Page"\n+++\n\n' + pre_md)
    subprocess.run([HUGO, "--quiet"], cwd=site, check=True)
    rendered = (site / "public" / "page" / "index.html").read_text()
    final = _run_mw(["post", "--config", str(config_path)], rendered)

    assert '<a class="mw-button mw-button-primary" href="/start">Get started</a>' in final
    assert '<a class="mw-lightbox" href="/a.png"><img src="/a.png" alt="A diagram" /></a>' in final
    assert '<pre class="mermaid">graph LR\n    A --&gt; B\n</pre>' in final
    assert '<ul class="mw-grid mw-grid-cards">' in final
    assert "<!-- mw-" not in final
    assert '<a class="mw-annotation" href="#mw-annotation-1-1">1</a>' in final
    assert "(1)!" not in final
    assert '<li id="mw-annotation-1-1">The first note.</li>' in final
    assert '<li id="mw-annotation-2-1">A prose note.</li>' in final
    assert final.count('<span aria-hidden="true" class="mw-icon"><svg') == 1


@requires_tools
def test_container_constructs_survive_hugo(tmp_path: Path) -> None:
    assert HUGO is not None
    site = tmp_path / "site"
    (site / "content").mkdir(parents=True)
    (site / "layouts" / "_default").mkdir(parents=True)
    (site / "hugo.toml").write_text(HUGO_CONFIG)
    (site / "layouts" / "_default" / "single.html").write_text(SINGLE_LAYOUT)

    pre_md = _run_mw(["pre"], CONTAINERS_SOURCE)
    (site / "content" / "page.md").write_text('+++\ntitle = "Page"\n+++\n\n' + pre_md)
    subprocess.run([HUGO, "--quiet"], cwd=site, check=True)
    rendered = (site / "public" / "page" / "index.html").read_text()
    final = _run_mw(["post"], rendered)

    # The grid wraps as a div carrying the cards class and the column count.
    assert '<div class="mw-grid mw-grid-cards mw-grid-cols-2">' in final
    # Two cards, both nested inside the grid div: the first is the grid's immediate child, and both
    # cards come before the sibling tab set that follows the grid.
    assert '<div class="mw-grid mw-grid-cards mw-grid-cols-2">\n<div class="mw-card">' in final
    assert final.count('<div class="mw-card">') == 2
    grid_open = final.index('<div class="mw-grid mw-grid-cards mw-grid-cols-2">')
    first_card = final.index('<div class="mw-card">', grid_open)
    second_card = final.index('<div class="mw-card">', first_card + 1)
    tabbed_set = final.index('<div class="tabbed-set tabbed-alternate mw-tabs" data-tabs="1:2">')
    assert grid_open < first_card < second_card < tabbed_set
    # The Chroma-highlighted fence survives inside the first card.
    assert 'class="chroma"' in final
    highlighted = final.index('class="language-python"')
    assert first_card < highlighted < second_card
    # The tab set: data-tabs count, the first tab checked, both mw-tab-S-T inputs and labels.
    assert '<input checked="checked" type="radio" id="mw-tab-1-1" name="mw-tab-1" />' in final
    assert '<input type="radio" id="mw-tab-1-2" name="mw-tab-1" />' in final
    assert '<label for="mw-tab-1-1">First</label>' in final
    assert '<label for="mw-tab-1-2">Second</label>' in final
    # Every container marker comment is consumed by post.
    assert "<!-- mw-" not in final


@requires_tools
def test_container_problems_survive_hugo(tmp_path: Path) -> None:
    assert HUGO is not None
    site = tmp_path / "site"
    (site / "content").mkdir(parents=True)
    (site / "layouts" / "_default").mkdir(parents=True)
    (site / "hugo.toml").write_text(HUGO_CONFIG)
    (site / "layouts" / "_default" / "single.html").write_text(SINGLE_LAYOUT)

    pre_md = _run_mw(["pre"], CONTAINER_PROBLEMS_SOURCE)
    (site / "content" / "page.md").write_text('+++\ntitle = "Page"\n+++\n\n' + pre_md)
    subprocess.run([HUGO, "--quiet"], cwd=site, check=True)
    rendered = (site / "public" / "page" / "index.html").read_text()
    completed = _run_mw_process(["post", "--warn"], rendered)
    final = completed.stdout

    # The literal directive text survives the round trip.
    assert "[card]" in final
    assert "[tab Lonely]" in final
    # Neither inline problem marker comment is left behind.
    assert "mw-grid-problem" not in final
    assert "mw-tab-problem" not in final
    # mw post --warn names each problem once on stderr.
    assert completed.stderr.count("Leaving [card] on line 1 literal") == 1
    assert completed.stderr.count("Leaving [tab] on line 7 literal") == 1


# The block starts a CommonMark renderer reads, as a line prefix, and the lines they join. Left out: a raw HTML
# block start (`<div>`, `<!-- `), whose text content `mw pre` rewrites and the in-process path leaves alone
# (spec.md, Roadmap Deferred, mw pre parity), and a fence start, since an unclosed fence is code to Goldmark and prose
# to `_fences` and Python-Markdown. A code span that holds a line end is read with continuation lines that
# start no block.
_PAIRING_BLOCK_STARTS = ("", "- ", "* ", "+ ", "1. ", "1) ", "- [ ] ", "> ", "# ", "    ", "\t", "    - ", "---")
_PAIRING_TWO_LINE_TEXTS = (
    ("a <^>b", "c<^> d"),
    ("a <^>b<^> c", "d <^>e<^> f"),
    ("a <^>b `x<^>y` c<^> d", "e <^>f<^> g"),
)
_PAIRING_THREE_LINE_TEXTS = (("a <^>b", "x", "c<^> d"), ("a <^>b<^> c", "x <^>y<^> z", "c<^> d"))
_PAIRING_CODE_SPAN_DOCUMENTS = ("a <^>b `x\ny` c<^> d\n", "a <^>b `x\ny\nz` c<^> d\n")
_MARK_RE = re.compile(r"<mark>(.*?)</mark>", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def _pairing_documents() -> list[str]:
    """Generate the two-line and three-line documents that join each pair of block starts with each text.

    Indented text straight after a heading line is left out: CommonMark reads it as indented code, which
    ``_fences`` reads as prose, since it needs a blank line before it there.
    """
    indented = {"    ", "\t", "    - "}
    documents = list(_PAIRING_CODE_SPAN_DOCUMENTS)
    for (first_text, second_text), first_start, second_start in itertools.product(
        _PAIRING_TWO_LINE_TEXTS, _PAIRING_BLOCK_STARTS, _PAIRING_BLOCK_STARTS
    ):
        if not (first_start == "# " and second_start in indented):
            documents.append(f"{first_start}{first_text}\n{second_start}{second_text}\n")
    for (first_text, middle_text, last_text), middle_start, last_start in itertools.product(
        _PAIRING_THREE_LINE_TEXTS, _PAIRING_BLOCK_STARTS, _PAIRING_BLOCK_STARTS
    ):
        if not (middle_start == "# " and last_start in indented):
            documents.append(f"{first_text}\n{middle_start}{middle_text}\n{last_start}{last_text}\n")
    return documents


def _marked_text(html: str) -> list[str]:
    """Return the text of each ``<mark>``, tags removed and whitespace collapsed.

    Goldmark renders a line end inside a code span as a space and Python-Markdown keeps it, so whitespace is
    not compared.
    """
    return [" ".join(_TAG_RE.sub("", marked).split()) for marked in _MARK_RE.findall(html)]


@requires_tools
def test_highlight_pairing_matches_in_process_over_generated_documents_through_hugo(tmp_path: Path) -> None:
    assert HUGO is not None
    names = ["highlight"]
    documents = _pairing_documents()
    site = tmp_path / "site"
    (site / "content").mkdir(parents=True)
    (site / "layouts" / "_default").mkdir(parents=True)
    (site / "hugo.toml").write_text(HUGO_CONFIG)
    (site / "layouts" / "_default" / "single.html").write_text(SINGLE_LAYOUT)
    for document_number, document in enumerate(documents):
        page = '+++\ntitle = "Page"\n+++\n\n' + registry.run_pre(document, names)
        (site / "content" / f"page-{document_number}.md").write_text(page)
    subprocess.run([HUGO, "--quiet"], cwd=site, check=True)

    in_process = markdown.Markdown(extensions=["markwright.highlight"])
    differing = []
    highlighted_documents = 0
    for document_number, document in enumerate(documents):
        built = (site / "public" / f"page-{document_number}" / "index.html").read_text()
        pipeline_marks = _marked_text(registry.run_post(built, names))
        in_process_marks = _marked_text(in_process.reset().convert(document))
        highlighted_documents += bool(in_process_marks)
        if pipeline_marks != in_process_marks:
            differing.append((document, in_process_marks, pipeline_marks))

    assert differing == []
    # The corpus must reach a highlight, or equality proves nothing
    assert highlighted_documents


@requires_tools
def test_commented_out_directives_stay_inside_the_comment_through_hugo(tmp_path: Path) -> None:
    source = "<!--\n[tab A]\n\nbody\n\n[/tab]\n[youtube dQw4w9WgXcQ]\n-->\n\nafter\n"

    final = _pipeline_through_hugo(tmp_path, source)

    assert "<!--\n[tab A]" in final
    assert "[youtube dQw4w9WgXcQ]\n-->" in final
    assert "tabbed-set" not in final
    assert "<iframe" not in final


@requires_tools
def test_an_embed_beside_text_is_its_own_block_through_hugo(tmp_path: Path) -> None:
    final = _pipeline_through_hugo(tmp_path, "Intro\n[youtube abc]\nOutro *line*\n")

    assert "youtube.com/embed/abc" in final
    assert "Outro <em>line</em>" in final
    assert "<p>Intro</p>" in final


@requires_tools
def test_a_tight_list_item_holding_an_embed_keeps_both_items_through_hugo(tmp_path: Path) -> None:
    final = _pipeline_through_hugo(tmp_path, "- item\n    [youtube abc]\n- next\n")

    assert final.count("<li>") == 2
    assert "youtube.com/embed/abc" in final
    assert "<p>next</p>" in final


@requires_tools
def test_a_marked_fence_under_a_tight_list_item_keeps_both_items_through_hugo(tmp_path: Path) -> None:
    final = _pipeline_through_hugo(tmp_path, "- Run this:\n    ```command\n    ls\n    ```\n- next\n")

    assert final.count("<ul>") == 1
    first_item = final.index("<li>")
    second_item = final.index("<li>", first_item + 1)
    assert first_item < final.index('class="prefixed command chroma"') < second_item
    assert "next" in final[second_item:]
    assert '<li data-prefix="$">' in final


@requires_tools
def test_a_shallow_marked_fence_and_embed_stay_in_their_items_through_hugo(tmp_path: Path) -> None:
    final = _pipeline_through_hugo(
        tmp_path, "- Run this:\n  ```command\n  ls\n  ```\n- item\n  [youtube abc]\n- next\n"
    )

    assert final.count("<ul>") == 1
    assert final.index('class="prefixed command chroma"') < final.index("next")
    assert final.index("youtube.com/embed/abc") < final.index("next")


@requires_tools
def test_the_item_after_text_that_follows_an_embed_or_a_marked_fence_stays_an_item_through_hugo(
    tmp_path: Path,
) -> None:
    final = _pipeline_through_hugo(
        tmp_path,
        "1. Watch this:\n    [youtube abc]\n    Then run *this* command.\n"
        "2. Run this:\n    ```command\n    ls\n    ```\n    After.\n3. Next\n",
    )

    assert final.count("<li>") == 3
    assert "<p>Then run <em>this</em> command.</p>" in final
    assert "<p>After.</p>" in final
    assert "<li>\n<p>Next</p>\n</li>" in final


@requires_tools
def test_a_flag_and_attribute_with_no_language_keep_highlighting_through_hugo(tmp_path: Path) -> None:
    final = _pipeline_through_hugo(tmp_path, "```line_numbers {hl_lines=[1]}\nalpha\nbeta\n```\n")

    assert 'class="language-text"' in final
    assert "hl_lines" not in final
    assert 'data-prefix="1"' in final
    assert 'data-prefix="2"' in final
    assert 'class="line hl"' in final


@requires_tools
def test_a_prefix_flag_beside_hugo_attribute_braces_keeps_the_prefix_and_highlighting(tmp_path: Path) -> None:
    final = _pipeline_through_hugo(tmp_path, "```command {hl_lines=[1]}\nls\n```\n")

    assert 'class="prefixed command chroma"' in final
    assert '<li data-prefix="$">' in final
    assert 'class="language-bash"' in final


@requires_tools
@pytest.mark.parametrize(
    ("source", "list_tag"),
    [
        ("1. Watch this:\n   [youtube abc]\n   Then run *this* command.\n2. Next\n", "ol"),
        ("- Watch this:\n  [youtube abc]\n  Then run *this* command.\n- Next\n", "ul"),
    ],
    ids=["ordered-3", "bullet-2"],
)
def test_a_shallow_embed_keeps_its_item_and_the_text_after_it_renders_through_hugo(
    tmp_path: Path, source: str, list_tag: str
) -> None:
    final = _pipeline_through_hugo(tmp_path, source)

    assert final.count(f"<{list_tag}>") == 1
    first_item = final.index("<li>")
    second_item = final.index("<li>", first_item + 1)
    assert first_item < final.index("youtube.com/embed/abc") < second_item
    assert "<em>this</em>" in final[first_item:second_item]
    assert "Next" in final[second_item:]
