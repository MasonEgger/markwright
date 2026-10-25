# Plan: Material Reference Parity (0.4.0, Issue #16)

Turns `spec.md`'s 0.4.0 goals and `.ai-sessions/material-parity/spec.md` (decisions D1 through D7 and the six byte-level contracts) into TDD-sized steps.
Every step is test-first, keeps `just check` green, and changes no existing extension's output.

This plan was regenerated after a first implementation pass (2026-10-14) was discarded so the work could run under the goal loop.
The gotchas that pass found are folded into the relevant steps as `**NOTE**` blocks and in `.ai-sessions/material-parity/plan.md`; trust them rather than rediscovering them.

## Current Status

- [ ] Section 1: Shared helpers and the marker module (Steps 1-2)
- [ ] Section 2: Pre-only extensions (Steps 3-6)
- [ ] Section 3: Marker-comment extensions (Steps 7-8)
- [ ] Section 4: Cross-cutting tests and registration checks (Step 9)
- [ ] Section 5: Demo assets, docs, and release (Steps 10-11)

## Ordering and Dependencies

- Section 1 lands the shared helpers (`_html.matching_end`, `_html.add_classes`, `_fences.map_prose`) and the `_markers` module, and refactors `fence` and `highlight` onto them with no output change. Everything else builds on these.
- Section 2 adds the four pre-only extensions, simplest first (button, lightbox), then the two that parse structure (mermaid, icons). Each registers itself, so the registry-driven tests see it immediately.
- Section 3 adds the two marker-comment extensions, which depend on `_markers` (Section 1) and `_html.add_classes` / `_html.matching_end`.
- Section 4 extends the cross-cutting tests (roundtrip, registry, CLI, Hugo integration) once all six extensions exist.
- Section 5 is non-code: demo host assets, docs pages, and the CHANGELOG. The pyproject.toml version bump is Mason's release step (as for 0.3.0), since the spec freezes deps.

## Stage Priority Reference

The registry's stage priorities and the in-process processor priorities mirror these (from `.ai-sessions/material-parity/spec.md`):

| Extension | Pre (run_pre / preprocessor) | Post (run_post / postprocessor) | In-process inline |
|-----------|------------------------------|---------------------------------|-------------------|
| icons | 50 | none | InlineProcessor 175 |
| mermaid | 45 | none | n/a (preprocessor 45) |
| fence | 40 | 25 | n/a |
| annotate | 20 | 30 | n/a |
| grid | 20 | 30 | n/a |
| button, lightbox | 20 | none | n/a |
| highlight | 10 | 25 | InlineProcessor 175 |

Why icons (50) runs before mermaid (45) in the pipeline: icons' `expand_source` uses `map_prose`, which skips fenced blocks, so it must run while a mermaid fence is still a fence. If mermaid ran first its `<pre>` block would no longer be fenced, and icons could expand a `:shortcode:` inside a diagram.

---

## Section 1: Shared helpers and the marker module

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 1: Shared helpers in `_html` and `_fences`

**NOTE**: `add_classes` is moved out of `fence.py` (currently the private `_with_classes`), so after this step `fence` imports it from `_html`. `map_prose` is extracted from `highlight.expand_source`, which currently inlines the fenced-block-plus-inline-code scan; after this step `highlight.expand_source` calls `map_prose` and its behavior is unchanged. `matching_end` is new. These are second-caller extractions (grid, annotate, and icons are the second callers landing later), justified by the spec's Component boundaries.

```text
1. RED: Write helper tests first:
   - Create tests/test_html_helpers.py:
     - Test matching_end(tokens, start_index) returns the index of the end tag that closes the start tag at start_index, for a simple <ul>...</ul>.
     - Test matching_end counts nesting: for "<div><div>x</div></div>" tokenized, the outer <div> start resolves to the outer </div>, not the inner one.
     - Test matching_end returns None when the element is never closed ("<ul><li>x").
     - Test add_classes(tag, "new") puts "new" in front of an existing class attribute ('<ol class="steps">' -> '<ol class="new steps">').
     - Test add_classes adds a class attribute when the tag has none ('<ul>' -> '<ul class="new">').
     - Test add_classes with added_attrs appends extra attributes after the existing ones (add_classes(ol_tag, "mw-annotations", (("data-mw-version","1"),)) yields 'class="mw-annotations ..." ... data-mw-version="1"').
   - Use markwright._html.tokenize to build the token lists; import matching_end and add_classes from markwright._html.
   - Create tests/test_fences_map_prose.py:
     - Test map_prose(text, transform) applies transform to a plain paragraph.
     - Test map_prose leaves a fenced code block untouched (transform is not applied inside ```...```).
     - Test map_prose leaves an inline code span untouched (`:x:` inside backticks is not transformed).
     - Use a transform that uppercases, so the boundary is visible.
   - Confirm these fail (symbols absent).

2. GREEN: Implement the helpers:
   - In src/markwright/_html.py, add add_classes(tag: HtmlToken, added_classes: str, added_attrs: tuple[tuple[str, str], ...] = ()) -> str, moving the body of fence._with_classes here and extending it to append added_attrs after the existing attributes in both the has-class and no-class branches.
   - In src/markwright/_html.py, add matching_end(tokens: list[HtmlToken], start_index: int) -> int | None that walks forward counting depth by tag name (start +1, end -1) and returns the index where depth returns to 0, or None.
   - In src/markwright/_fences.py, add map_prose(text: str, transform: Callable[[str], str]) -> str: split into fenced and non-fenced line groups via find_fenced_blocks (reuse the itertools.groupby shape currently in highlight.expand_source), and within each prose chunk skip inline code spans via a module-level _INLINE_CODE_RE, applying transform only to the between-code runs. Move _INLINE_CODE_RE into _fences.py.

3. REFACTOR existing callers onto the helpers (no behavior change):
   - In src/markwright/fence.py, delete _with_classes and import add_classes from _html; update the one call site.
   - In src/markwright/highlight.py, rewrite expand_source to return map_prose(text, lambda prose: _PROSE_HIGHLIGHT_RE.sub(r"<mark>\1</mark>", prose)); drop the now-duplicated inline-code regex and the itertools import if unused.

4. Verify the existing fence and highlight suites still pass unchanged (tests/test_fence.py, tests/test_highlight.py), proving the refactor preserved behavior.

5. Run `just check` and confirm green.
```

### Step 2: The `_markers` module and `fence` refactored onto it

**NOTE**: This extracts the marker-comment contract (currently private to `fence.py`: `_encode_marker_payload`, `MARKER_COMMENT_RE`, `_InvalidMarkerError`, `_parse_marker`) into a shared `src/markwright/_markers.py`, then moves `fence` onto it. `grid` and `annotate` will reuse it. The `mw-fence` payload and `fence`'s output must not change; the existing `tests/test_fence.py` is the guard. The empty-page case (a document with no markers) needs an explicit test: a strict `zip` over an empty marker list raised in the first pass.

```text
1. RED: Write marker-module tests first:
   - Create tests/test_markers.py:
     - Test encode_marker("mw-x", {"a": 1}) returns '<!-- mw-x:{"version": 1, "a": 1} -->' (version injected first).
     - Test encode_marker escapes < and > so a payload value "-->" cannot close the comment: encode_marker("mw-x", {"v": "a-->b"}) contains neither "-->" inside the payload nor a literal "<"/">"; json.loads of the inner payload round-trips the original string.
     - Test find_markers("mw-x", html, tokens) returns one MarkerComment per matching comment, each with token_index, raw_payload, and block_end set to the next same-name marker's index (or len(tokens) for the last).
     - Test find_markers returns [] for HTML with no markers (the empty-page guard).
     - Test decode_marker("mw-x", raw, Model) returns a validated Model for good JSON, and raises InvalidMarkerError with the documented message for: malformed JSON, a non-object payload, version != 1, and a wrongly typed field (use a tiny strict pydantic Model fixture in the test).
   - Confirm these fail (module absent).

2. Document the contract:
   - In src/markwright/_markers.py top-of-file comment, state that the marker comment is <!-- NAME:{JSON} --> carrying "version", comment-safe encoded, read fail-soft, shared by the post stages.

3. GREEN: Implement src/markwright/_markers.py:
   - MARKER_VERSION = 1.
   - encode_marker(name, payload) -> str: json.dumps({"version": MARKER_VERSION, **payload}) with "<"->"\\u003c" and ">"->"\\u003e", wrapped in "<!-- {name}:{...} -->".
   - A frozen pydantic MarkerComment model (token_index, raw_payload, block_end).
   - find_markers(name, rendered_html, tokens) -> list[MarkerComment]: match comment tokens with re.compile(rf"<!-- {re.escape(name)}:(.*?) -->").fullmatch over each comment token's span; compute each block_end from the next match's token_index (plain loop, not a strict zip over an empty list).
   - InvalidMarkerError(Exception); decode_marker(name, raw_payload, model) -> model: json.loads, isinstance dict check, version check, model.model_validate wrapped so a ValidationError becomes InvalidMarkerError naming the invalid fields. Message strings must match the fence ones so fence's skip-reason tests keep passing.

4. REFACTOR fence onto _markers (no output change):
   - In src/markwright/fence.py: delete _encode_marker_payload, MARKER_COMMENT_RE, MARKER_VERSION, _InvalidMarkerError, and _parse_marker; import encode_marker, find_markers, decode_marker, InvalidMarkerError from _markers.
   - Replace the marker emission in _expand_lines with encode_marker(MARKER_NAME, metadata).
   - Replace the token/marker loop in _apply_marker with find_markers(MARKER_NAME, rendered_html, tokens) and decode_marker(MARKER_NAME, marker.raw_payload, FenceMarker), using marker.token_index and marker.block_end for the block slice. Keep the "no following code block" InvalidMarkerError raise.
   - Keep FenceMarker in fence.py (it is fence-specific).

5. Verify tests/test_fence.py passes unchanged (the mw-fence payload and output are identical), plus the new tests/test_markers.py.

6. Run `just check` and confirm green.
```

---

## Section 2: Pre-only extensions

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 3: `button` extension

**NOTE**: button is inline raw HTML. Python-Markdown treats a lone `<a ...>...</a>` line as a paragraph with inline raw HTML, so one `_render_match` serves both the CLI `expand_source` and the in-process preprocessor with no stash; the renderer still processes Markdown inside the text. Pattern: the directive-expand pre stage, like the embeds (priority 20).

```text
1. RED: Write button tests first:
   - Create tests/test_button.py (import expand_source from markwright.button; render_button helper builds markdown.Markdown(extensions=["markwright.button"])):
     - expand_source("[button https://example.com/start Get started]") == '<a class="mw-button" href="https://example.com/start">Get started</a>'
     - expand_source("[button primary /start Get started]") == '<a class="mw-button mw-button-primary" href="/start">Get started</a>'
     - URL and text are HTML-escaped (input "[button /a?b=1&c=2 Tom & Jerry <3]" yields href="...&amp;..." and ">Tom &amp; Jerry &lt;3</a>").
     - "[button /docs]" (no text) is left as literal text.
     - An inline mention "Use [button /docs Docs] here." is left unchanged.
     - render_button("[button /start Get started]") == '<p><a class="mw-button" href="/start">Get started</a></p>'.
     - Two consecutive button lines with no blank line share one <p> (result.count("<p>") == 1, two mw-button links).
     - Inline Markdown in the text renders: render_button("[button /docs Read *the* docs]") contains ">Read <em>the</em> docs</a>".
   - Confirm failing (module absent).

2. GREEN: Implement src/markwright/button.py:
   - BUTTON_RE = r"^\[button(?:\s+(?P<primary>primary))?\s+(?P<url>\S+)\s+(?P<text>.+)\]$".
   - _render_match(line) -> str | None builds the <a> with html.escape on url and text; classes "mw-button" or "mw-button mw-button-primary".
   - expand_source(text, options=None): "\n".join(_render_match(line) or line for each line).
   - ButtonPreprocessor (priority 20) returning [_render_match(line) or line for line in lines]; ButtonExtension.extendMarkdown registers it as "mw-button"; makeExtension.
   - 2-line ABOUTME header, from __future__ import annotations, RST docstrings.

3. Wire up: register "button" in src/markwright/registry.py with StageSpec(pre=button.expand_source, pre_priority=20, extension=button.ButtonExtension), import button in the registry import block (keep alphabetical).

4. Run `just check` and confirm green.
```

### Step 4: `lightbox` extension

**NOTE**: Same inline-raw-HTML pattern as button; no stash needed.

```text
1. RED: Write lightbox tests first:
   - Create tests/test_lightbox.py (import expand_source from markwright.lightbox; render helper loads "markwright.lightbox"):
     - expand_source("[lightbox https://example.com/a.png A diagram]") == '<a class="mw-lightbox" href="https://example.com/a.png"><img src="https://example.com/a.png" alt="A diagram" /></a>'
     - expand_source("[lightbox /a.png]") == '<a class="mw-lightbox" href="/a.png"><img src="/a.png" alt="" /></a>'
     - URL and alt are escaped ('[lightbox /a.png?x=1&y=2 Tom & Jerry "q"]' -> href="...&amp;..." and alt="Tom &amp; Jerry &quot;q&quot;").
     - An inline mention is left unchanged.
     - render("[lightbox /a.png A diagram]") == '<p><a class="mw-lightbox" href="/a.png"><img src="/a.png" alt="A diagram" /></a></p>'.
   - Confirm failing.

2. GREEN: Implement src/markwright/lightbox.py:
   - LIGHTBOX_RE = r"^\[lightbox\s+(?P<url>\S+)(?:\s+(?P<alt>.+))?\]$".
   - _render_match escapes url (reused for href and src) and alt (empty when absent); emits '<a class="mw-lightbox" href="{url}"><img src="{url}" alt="{alt}" /></a>'.
   - expand_source, LightboxPreprocessor (priority 20, name "mw-lightbox"), LightboxExtension, makeExtension; same shape as button.

3. Wire up: register "lightbox" in registry.py (pre=lightbox.expand_source, pre_priority=20, extension=lightbox.LightboxExtension).

4. Run `just check` and confirm green.
```

### Step 5: `mermaid` extension

**NOTE**: Emit the `<pre class="mermaid">` block as raw HTML INLINE in both the CLI `expand_source` and the in-process preprocessor. Do NOT use `self.md.htmlStash.store`: mermaid's preprocessor registers at priority 45, above Python-Markdown's `normalize_whitespace` (30), which strips the STX/ETX bytes around a stash placeholder, so a stashed block above 30 breaks. The raw block is carried by the built-in `html_block` preprocessor (20) instead. Strip the fence's own indentation from the diagram lines (CommonMark rule) and prepend the fence indent to every output line so an indented fence stays in its list item. Do not assert the in-process result for an indented in-list fence: Python-Markdown's raw-HTML block scanner only recognizes a block within 3 spaces of indent, so that case is covered on the pre stage and through Hugo, not in-process.

```text
1. RED: Write mermaid tests first:
   - Create tests/test_mermaid.py (import expand_source from markwright.mermaid; render helper loads ["pymdownx.superfences","pymdownx.highlight","markwright.mermaid"]):
     - DIAGRAM = "```mermaid\ngraph LR\n    A --> B\n```"; EXPECTED = '<pre class="mermaid">graph LR\n    A --&gt; B\n</pre>'.
     - expand_source(DIAGRAM) == EXPECTED.
     - A ~~~mermaid tilde fence produces the same EXPECTED.
     - Source is HTML-escaped and otherwise intact: '```mermaid\nA["x & y"] --> B\n\n  C\n```' -> '<pre class="mermaid">A["x &amp; y"] --&gt; B\n\n  C\n</pre>'.
     - Other fences untouched: "```python\nx = 1\n```\n\n```\nplain\n```" is returned unchanged.
     - Prose around a diagram is preserved ("Intro\n\n"+DIAGRAM+"\n\nOutro").
     - A "[label a]" line inside a mermaid fence stays diagram text (fence directives are not read).
     - An indented fence in a list item keeps the indent on the pre stage: "- item\n\n    ```mermaid\n    graph LR\n        A --> B\n    ```" -> '- item\n\n    <pre class="mermaid">graph LR\n        A --&gt; B\n    </pre>'.
     - An unclosed "```mermaid\ngraph LR" is returned unchanged.
     - In-process: render_mermaid(DIAGRAM) == EXPECTED, and the result contains no "<code" and no "<span" (superfences did not highlight it).
   - Confirm failing.

2. GREEN: Implement src/markwright/mermaid.py:
   - MERMAID_CLASS = "mermaid".
   - _expand_lines(lines): iterate find_fenced_blocks; for a block whose info.strip() == "mermaid", strip the fence indent from the content lines, html.escape("\n".join(lines)+"\n", quote=False), build '<pre class="mermaid">{escaped}</pre>', and emit each of its lines prefixed with block.indent. Pass other content through.
   - expand_source(text, options=None) = "\n".join(_expand_lines(text.split("\n"))).
   - MermaidPreprocessor.run(lines) = _expand_lines(lines) (raw inline, NO stash); register at priority 45 as "mw-mermaid". MermaidExtension, makeExtension.

3. Wire up: register "mermaid" in registry.py (pre=mermaid.expand_source, pre_priority=45, extension=mermaid.MermaidExtension).

4. Run `just check` and confirm green.
```

### Step 6: `icons` extension

**NOTE**: Resolves `:pack-name:` against configured directories; markwright ships no icons. In-process uses an InlineProcessor (priority 175) that stashes the SVG; the CLI `expand_source` uses `map_prose` so code is skipped. Emit the wrapper with attributes in alphabetical order, `<span aria-hidden="true" class="mw-icon">...</span>`: Python-Markdown's serializer sorts attributes, so the pre stage must match that order for byte parity with the in-process path. `packs` is validated like fence's `allowed_environments`: a sentinel default (`_NO_PACKS = object()`) read in `extendMarkdown`, since Python-Markdown runs a None default through parseBoolValue. Omitted packs is silent (the all-on default must not warn for every user); an empty table warns; a missing directory or non-string value is an OptionError.

```text
1. RED: Write icons tests first:
   - Create tests/test_icons.py with a `packs` fixture that writes two packs under tmp_path (octicons/rocket-16.svg flat, lucide/arrows/up.svg nested with an XML declaration and multi-line body) and returns {"octicons": str(octicons_dir), "lucide": str(lucide_dir)}; import expand_source from markwright.icons and ConfigError/ConfigWarning/OptionError/config_from_mapping from markwright:
     - expand_source("Launch :octicons-rocket-16: now", {"packs": packs}) wraps the rocket SVG as '<span aria-hidden="true" class="mw-icon">{svg}</span>'.
     - Nested path joins with "-" and the XML declaration is dropped and the SVG is one line: expand_source(":lucide-arrows-up:", {"packs": packs}) has the <svg...> with no "<?xml".
     - Unknown pack stays literal ("at :material-rocket: and 10:30-11:00: sharp" unchanged).
     - Unknown name stays literal (":octicons-missing-16:" unchanged).
     - Inside inline code and a fenced block the shortcode is untouched.
     - No packs passes text through: expand_source(":octicons-rocket-16:") == input and expand_source(same, {}) warns (see options tests) but still returns input.
     - In-process: render with extension_configs {"markwright.icons": {"packs": packs}} wraps in <p>...</p>; inline code is untouched; unknown name stays literal; no packs passes text through.
     - Options: expand_source(":a-b:", {"packs": {}}) raises pytest.warns(ConfigWarning, match="'packs' is empty"); {"packs": ["x"]} and {"packs": {"x": 1}} raise OptionError("'packs' must be a table ..."); {"packs": {"octicons": str(tmp_path/'nope')}} raises OptionError matching "directory for 'octicons' not found"; markdown.Markdown(..., {"markwright.icons": {"packs": 1}}) raises OptionError at construction; config_from_mapping({"icons": {"packs": {"octicons": str(missing)}}}, "test") raises ConfigError matching "[icons] 'packs' directory for 'octicons' not found"; config_from_mapping with valid packs stores config.options["icons"] == {"packs": packs}.
   - Confirm failing.

2. GREEN: Implement src/markwright/icons.py:
   - ICON_CLASS = "mw-icon"; _NO_PACKS = object().
   - A frozen pydantic IconOptions(packs: dict[str, Path]); read_options(options) validates: sentinel/None -> empty packs; non-dict or non-string value -> OptionError; empty dict -> ConfigWarning via warnings.warn; each directory must is_dir() else OptionError; returns IconOptions with Path values.
   - _shortcode_pattern(packs) builds :(prefix)-(name): for configured prefixes (longest-first), or r"(?!)" when empty.
   - _load_icon(packs, pack, name): find the SVG by matching name against each file in packs[pack].rglob("*.svg") with "-".join(relative-path parts, no suffix); read it, drop everything before "<svg", collapse lines to one; return None if no match.
   - expand_source(text, options=None): read_options, then map_prose(text, lambda prose: pattern.sub(replace, prose)) where replace loads the icon or leaves the shortcode literal; emit '<span aria-hidden="true" class="mw-icon">{svg}</span>'.
   - IconInlineProcessor(InlineProcessor) (priority 175) stashing the SVG via self.md.htmlStash.store and building a span Element with {"class": ICON_CLASS, "aria-hidden": "true"} (serializer sorts to aria-hidden, class); returns (None, None, None) for an unknown icon. IconsExtension declares config {"packs": [_NO_PACKS, ...]} in __init__, reads read_options(self.getConfigs()) in extendMarkdown, registers "mw-icons". makeExtension.

3. Wire up: register "icons" in registry.py with StageSpec(pre=icons.expand_source, pre_priority=50, extension=icons.IconsExtension, check_options=icons.read_options).

4. Run `just check` and confirm green.
```

---

## Section 3: Marker-comment extensions

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 7: `grid` extension

**NOTE**: Marker-comment pre/post pair using `_markers` (Step 2) and `_html.add_classes`, `_html.matching_end`. Post priority 30. A `[grid]` or `[grid cards]` line becomes a marker plus a blank line; the post stage classes the next `<ul>`/`<ol>` and consumes the marker.

```text
1. RED: Write grid tests first:
   - Create tests/test_grid.py (import expand_source, apply_html from markwright.grid; render_grid loads "markwright.grid"; constants CARDS_MARKER, GRID_MARKER, LIST_HTML):
     - expand_source("[grid cards]\n- a\n- b") == CARDS_MARKER + "\n\n- a\n- b"; expand_source("[grid]\n\n- a") emits GRID_MARKER then a blank line.
     - Indent is preserved: "- item\n\n    [grid cards]\n    - a" keeps the 4-space indent on the marker.
     - An inline mention and an unknown variant ("[grid tiles]") are left unchanged.
     - apply_html(CARDS_MARKER+"\n"+LIST_HTML) classes the next <ul> 'mw-grid mw-cards' and removes the marker; GRID_MARKER gives 'mw-grid'; an <ol class="steps"> becomes 'mw-grid steps'.
     - Each marker styles only its own list (two markers, two lists, one plain list in between stays unclassed).
     - No following list is skipped and reported: apply_html(CARDS_MARKER+"\n<p>text</p>", skip_reasons) leaves the <p> and appends "Skipping mw-grid marker with no following list".
     - Malformed, unsupported-version, and wrongly-typed-field markers are skipped and reported with the _markers messages.
     - Running apply_html twice is stable.
     - In-process: render_grid("[grid cards]\n\n- a\n- b") == '<ul class="mw-grid mw-cards">\n<li>a</li>\n<li>b</li>\n</ul>'; a marker with no list is consumed (render_grid("[grid]\n\ntext") == "<p>text</p>").
   - Confirm failing.

2. GREEN: Implement src/markwright/grid.py:
   - MARKER_NAME = "mw-grid"; GRID_CLASS = "mw-grid"; CARDS_CLASS = "mw-cards"; GRID_RE = r"^\[grid(?P<cards>\s+cards)?\]$".
   - A frozen strict pydantic GridMarker(version: int, cards: bool = False).
   - _expand_lines: replace each grid line with indent + encode_marker(MARKER_NAME, {"cards": True} if cards else {}) then "".
   - expand_source(text, options=None).
   - apply_html(rendered_html, skip_reasons=None, options=None): tokenize; for each find_markers(MARKER_NAME, ...): edit the comment to ""; find the next <ul>/<ol> start token before block_end; decode_marker into GridMarker; raise/collect InvalidMarkerError("no following list") when absent; add_classes(list_tag, "mw-grid mw-cards" or "mw-grid"); apply_edits.
   - GridPreprocessor (priority 20, "mw-grid-pre"), GridPostprocessor (priority 30, "mw-grid-post"), GridExtension, makeExtension.

3. Wire up: register "grid" in registry.py (pre=grid.expand_source, post=grid.apply_html, pre_priority=20, post_priority=30, extension=grid.GridExtension).

4. Run `just check` and confirm green.
```

### Step 8: `annotate` extension

**NOTE**: The hardest step. Marker-comment pre/post pair; post priority 30 so it runs BEFORE the fence postprocessor (25), keeping the fence marker a comment token while the annotated block is located (otherwise the fence label `<div>` becomes the "block"). Links `(M)` markers in the block's text (text tokens only, never attributes/`<script>`/`<style>`) to the M-th item of the following `<ol>`. For a `# (M)!` form in code, replace the whole syntax-highlighter comment span (Pygments/Chroma class `c`, `c1`, `cm`, ...) when it wraps exactly that text token, preserving a trailing newline the span carries. Uses `_markers`, `_html.add_classes`, `_html.matching_end`, `_html.render_start_tag`, and `_html.RAW_TEXT_ELEMENTS`.

```text
1. RED: Write annotate tests first:
   - Create tests/test_annotate.py (import expand_source, apply_html from markwright.annotate; render_annotate loads ["pymdownx.superfences","pymdownx.highlight","markwright.annotate","markwright.fence"] with pygments_lang_class; constants MARKER, PROSE, PROSE_ANNOTATED, LINK_1, NOTES, NOTES_ANNOTATED):
     - Source stage: expand_source("[annotate]\nText (1)\n\n1. note") == MARKER + "\n\nText (1)\n\n1. note"; indent preserved; inline mention unchanged.
     - Prose: apply_html(MARKER+"\n"+PROSE) classes the <p> mw-annotated, the <ol> mw-annotations with data-mw-version="1", ids each <li> mw-annotation-1-M, and links each (M) marker; a (9) with no item stays text; markers in a title="(1)" attribute and in a later unrelated <p> are untouched; ids count per page (a second MARKER block uses mw-annotation-2-*); nested list items are not annotations (only direct <li> get ids); existing <ol class="steps"> becomes 'mw-annotations steps'; running apply_html twice is stable; a nested same-tag block (<div><div>(1)</div></div>) ends at its own close.
     - Code: a Pygments comment span ('<span class="c1"># (1)!</span>') is replaced whole by LINK_1 (the comment text disappears); a Chroma fixture ('<span class="cl">x <span class="c1"># (1)!</span>\n</span>') likewise; a comment span with a trailing newline keeps it (LINK_1 followed by "\n"); without a comment span only the marker text is replaced ('plain # (1)!' -> 'plain # '+LINK_1); a "# (1)" with no bang keeps the comment span.
     - Skips: no following block -> "Skipping mw-annotate marker with no following block"; an unclosed block -> same; a block then a non-list element -> "Skipping mw-annotate marker with no annotation list after the block"; malformed and unsupported-version markers reported with the _markers messages.
     - In-process: a paragraph renders PROSE_ANNOTATED; a labeled bash fence with "# (1)!" gets the fence label div AND the annotation link inside the code AND mw-annotated on the highlight div AND NOTES_ANNOTATED; a marker with no list is consumed.
   - Confirm failing.

2. GREEN: Implement src/markwright/annotate.py:
   - MARKER_NAME = "mw-annotate"; BLOCK_CLASS "mw-annotated"; LIST_CLASS "mw-annotations"; LINK_CLASS "mw-annotation"; CONTRACT_VERSION 1; ANNOTATE_RE r"^\[annotate\]$"; MARKER_RE r"\((?P<number>\d+)\)(?P<bang>!?)"; COMMENT_CLASSES = frozenset({"c","c1","cm","cp","cpf","cs","ch"}).
   - A frozen strict pydantic AnnotateMarker(version: int).
   - _expand_lines: each annotate line -> indent + encode_marker(MARKER_NAME, {}) then "".
   - expand_source(text, options=None).
   - _locate(rendered_html, tokens, token_index, block_end) -> (block_start, block_close, list_start, list_close): first start token after the marker is the block; matching_end closes it; the first non-comment, non-blank-text token after that must be an <ol> (else InvalidMarkerError with the two documented messages).
   - apply_html(rendered_html, skip_reasons=None, options=None): tokenize; block_number counter; for each find_markers: remove the comment; decode_marker; _locate; add_classes on the <ol> (LIST_CLASS + data-mw-version) and render_start_tag to id each direct <li> (skip nested lists via a depth counter); add_classes BLOCK_CLASS on the block tag; for each text token in the block (skip when the previous token's tag is in RAW_TEXT_ELEMENTS), for each MARKER_RE match with 1 <= number <= item_count, build the link; when the match has the bang and the text token is the sole content of a COMMENT_CLASSES span, replace the whole span (keeping a trailing newline), else replace just the marker span; apply_edits.
   - _enclosing_comment_span(tokens, token_index) returns the (open, close) span tokens when the text token is wrapped by a comment span, else None.
   - AnnotatePreprocessor (priority 20, "mw-annotate-pre"), AnnotatePostprocessor (priority 30, "mw-annotate-post"), AnnotateExtension, makeExtension.

3. Wire up: register "annotate" in registry.py (pre=annotate.expand_source, post=annotate.apply_html, pre_priority=20, post_priority=30, extension=annotate.AnnotateExtension), import in the alphabetical block.

4. Run `just check` and confirm green.
```

---

## Section 4: Cross-cutting tests and registration checks

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 9: Round-trip, registry, CLI, and Hugo coverage

**NOTE**: Extends existing tests so the six extensions are proven through the CLI pipeline, the registry listing, and a real Hugo build, matching how the existing eight are covered. No new source. The Hugo test needs `hugo` and `mw` on PATH (it skips otherwise); run `just test-integration` to exercise it.

```text
1. RED/extend: Round-trip parity (tests/test_roundtrip.py):
   - Extend FIXTURE with a button line, a lightbox line, a mermaid fence, a [grid cards] list, an [annotate] code block with "# (1)!" and an [annotate] prose block.
   - Add presence assertions for each: the mw-button-primary link, the mw-lightbox linked image, '<pre class="mermaid">graph LR\n    A --&gt; B\n</pre>', '<ul class="mw-grid mw-cards">', the annotation link, "(1)!" absent, and the second block's '<li id="mw-annotation-2-1">'.
   - Extend the degradation test: after stripping comments, "mw-grid" and "mw-annotation" are absent but the button and '<pre class="mermaid">' survive (they do not use the comment channel).
   - Add a TestRoundTripIcons case with a tmp_path pack: pipeline and in_process_render agree and exactly one '<span aria-hidden="true" class="mw-icon"><svg' lands, with an inline-code shortcode left literal.
   - Extend the hypothesis grammar with a _grid_block, an _annotate_block (prose and code forms), and a _directive_blocks sampler (button, lightbox, mermaid), and add them to the composite st.one_of.

2. RED/extend: Registry and CLI (tests/test_registry.py, tests/test_cli.py):
   - OPTION_NAMES["icons"] == {"packs"}; describe() reports button/lightbox/mermaid/icons as ["pre"] and grid/annotate as ["pre","post"].
   - The mw list and mw config output tests already assert on substrings; confirm they pass with the six new extensions present (the all-on default now lists 14 extensions). Adjust any exact-count assertion.

3. RED/extend: Hugo integration (tests/integration/test_hugo_pipeline.py):
   - Add a MATERIAL_SOURCE page using all six constructs plus a committed tmp_path demo pack, driven through mw pre | hugo | mw post.
   - Assert the button link, the lightbox image, '<pre class="mermaid">graph LR\n    A --&gt; B\n</pre>', '<ul class="mw-grid mw-cards">', no "<!-- mw-" comments survive, the annotation link inside Chroma's comment token, "(1)!" absent, both annotation list ids, and exactly one mw-icon span.

4. GREEN: no source changes expected; if an assertion fails, fix the responsible extension, not the test.

5. Run `just check` and `just test-integration`; confirm both green.
```

---

## Section 5: Demo assets, docs, and release

**Tools:**
- Skills: content-design:review-content
- MCPs: none
- Linters: none

### Step 10: Demo host assets (task)

**NOTE**: These are host assets under `docs/`, not package code. markwright still ships no JS, no CSS, no icons. The docs site is the host, exactly as `docs/stylesheets/extra.css` already is for the existing extensions. This introduces the first `docs/javascripts/` in the repo and the first committed icons.

```text
1. Scope:
   - Artifacts: docs/stylesheets/extra.css (append), docs/javascripts/mermaid.js, docs/javascripts/lightbox.js, docs/javascripts/annotate.js, docs/icons/<pack>/*.svg, docs/icons/LICENSE (or a NOTICE block), mkdocs.yml (extra_javascript, extra_css already present, and a markwright.icons config with packs).
   - Desired end state: all six extensions render live on `mkdocs serve`; mermaid diagrams draw, the lightbox opens a <dialog>, annotation markers show a tooltip, and demo icons display inline.

2. Tooling:
   - Skills: none
   - MCPs: none
   - External: `just docs-serve` for a visual check; `just docs-build` for the strict build.

3. Do the work:
   - Append CSS to docs/stylesheets/extra.css for .mw-button / .mw-button-primary, .mw-grid (CSS grid, auto-fit minmax) and .mw-cards, .mw-lightbox, .mw-icon (inline sizing, currentColor fill), .mw-annotation (superscript marker) and .mw-annotations, and the mw-embed-style tooltip for annotations.
   - Create docs/javascripts/mermaid.js importing a pinned mermaid 11.x from a CDN (jsdelivr or cdnjs, exact version) and calling mermaid.initialize({ startOnLoad: true }).
   - Create docs/javascripts/lightbox.js: one document click listener that opens a <dialog> showing the image from a clicked .mw-lightbox link's href and alt, preventing navigation.
   - Create docs/javascripts/annotate.js: wire .mw-annotation links to show their list item's content as a tooltip (a small positioned element, or the popover API), with a footnote-link fallback.
   - Commit a small set of liberally-licensed SVGs under docs/icons/ (for example a Lucide subset, ISC, and an Octicons subset, MIT), 2-3 per pack; add docs/icons/LICENSE crediting each set.
   - In mkdocs.yml: add the three scripts under extra_javascript (mermaid first); add a markwright.icons entry under markdown_extensions with packs mapping each prefix to its docs/icons/<pack> directory.

4. Verify:
   - `just docs-build` exits 0 with no "^WARNING|^ERROR" lines.
   - A `just docs-serve` visual check (human) confirms each of the six renders. Note this as a human-check in the step.

5. Document:
   - docs/icons/LICENSE records each icon set and its license (the credit the invariant requires).
```

### Step 11: Docs pages, nav, README, and CHANGELOG (task)

**NOTE**: Prose follows the `content-design` skill and the writing hard rules (no em-dashes, no banned vocab, Title Case headings, straight quotes, one sentence per line in committed Markdown). Each extension page mirrors the shape of the existing `docs/extensions/*.md`: intro, usage, syntax table, the mw- contract, a live demo, and the host CSS or script it needs.

```text
1. Scope:
   - Artifacts: docs/extensions/{button,lightbox,mermaid,icons,grid,annotate}.md; mkdocs.yml nav; docs/index.md and README.md feature lists; docs/cli.md (mw list and mw config now show 14 extensions); docs/config.md (the icons packs option and its Config Rules behavior); docs/integrations/mkdocs.md (the six added to the example); CHANGELOG.md (an Added section under an Unreleased heading; the version bump is the release step, not this step); CLAUDE.md (the new patterns, the priority table, the _markers boundary).
   - Desired end state: every nav page exists, the docs build strict-clean, and the version and CHANGELOG reflect 0.4.0.

2. Tooling:
   - Skills: content-design:review-content
   - MCPs: none
   - External: `just docs-build` strict; the content-design Vale/style check.

3. Do the work:
   - Write the six docs/extensions/*.md pages with the contract and a live demo block; cross-reference the icons page to the committed demo pack and its license.
   - Add the six pages to the mkdocs.yml Extensions nav, alphabetical with the existing entries.
   - Update docs/index.md and README.md feature lists with one bullet per new extension.
   - Update docs/cli.md so the mw list and mw config sample output include the six (keep the existing format).
   - Add the icons packs option to docs/config.md with its Config Rules behavior (omitted silent, empty warns, bad directory errors).
   - Add the six to the docs/integrations/mkdocs.md example markdown_extensions block, with the markwright.icons packs note.
   - Add a CHANGELOG.md "## [Unreleased]" heading with an Added section listing the six extensions and the demo-site changes, and an Upgrading note that output for existing documents is unchanged.
   - Update CLAUDE.md: add the four new patterns to The Three Extension Patterns discussion (or note the six follow existing patterns), add the new rows to the Processor Priority Reference table, and add the _markers.py module to the Architecture description.

4. Verify:
   - `just docs-build` exits 0 with no "^WARNING|^ERROR" lines and every nav page present.
   - `just check` still green (docs do not touch the gate, but confirm).
   - Run the content-design review over the new and changed prose.

5. Document:
   - The CHANGELOG and the docs pages are themselves the documentation; no separate note.
```

---

## Implementation Guidelines

- TDD: RED (failing test) then GREEN (minimal code) then REFACTOR, per the `python:python` skill. `just check` must pass before a step is considered complete.
- Every source file opens with a 2-line `# ABOUTME:` comment and `from __future__ import annotations`, uses RST docstrings, descriptive names (never single letters), and frozen pydantic models for data shapes, per CLAUDE.md.
- Each new extension registers itself in `registry.py` in the same step it is written, so the registry-driven tests and the CLI see it immediately; no orphaned modules.
- Test the project's own logic only: the stage functions (`expand_source`, `apply_html`) directly, and in-process behavior through a `render_*` helper. Do not test Python-Markdown, pymdownx, or Pygments.
- The `mw-fence` payload and `fence`'s output must stay byte-identical across Steps 1 and 2; `tests/test_fence.py` is the guard.
- Prose (docs, README, CHANGELOG, CLAUDE.md) follows the writing hard rules and the `content-design` skill.
- Never commit to `main`; the work is on the `material-parity-0.4.0` branch, one PR, squash-merged by Mason.

## Success Metrics

- `just check` green: ruff, ruff format, mypy strict, pytest, coverage reported (test or delete every uncovered line).
- `just test-integration` green: the six new constructs through a real Hugo build, plus the clean-venv wheel install.
- `just docs-build` strict-clean with every nav page present, and a visual check that all six render live.
- The six extensions match their contracts in `.ai-sessions/material-parity/spec.md`; the `mw-grid` and `mw-annotate` markers and the `mw-annotation` version read fail-soft.
- CHANGELOG.md carries an Unreleased entry for the six extensions (the 0.4.0 bump is the release step); no existing extension's output changed.
