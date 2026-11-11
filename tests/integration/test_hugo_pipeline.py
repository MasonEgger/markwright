# ABOUTME: End-to-end integration test driving mw as a pre/post processor around a real Hugo build.
# Skipped unless both the mw console script and the hugo binary are on PATH; marked `integration`.

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

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
