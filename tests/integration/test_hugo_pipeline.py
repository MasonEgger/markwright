# ABOUTME: End-to-end integration test driving mw as a pre/post processor around a real Hugo build.
# Skipped unless both the mw console script and the hugo binary are on PATH; marked `integration`.

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

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


def _run_mw(args: list[str], stdin_text: str) -> str:
    assert MW is not None
    completed = subprocess.run(
        [MW, *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


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
