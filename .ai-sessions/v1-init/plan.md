# Plan: do-markdown — Python Markdown Extensions

## Current Status

**Status:** In Progress

| Step | Description | Status |
|------|-------------|--------|
| 1 | Project Scaffolding | Done |
| 2 | Highlight Extension (`<^>...<^>`) | Done |
| 3 | Fence Extension — Directive Parsing & Labels | Done |
| 4 | Fence Extension — Environment Classes | Done |
| 5 | Fence Extension — Line Prefixes | Done |
| 6 | YouTube Embed | Done |
| 7 | CodePen Embed | Done |
| 8 | Twitter & Instagram Embeds | Done |
| 9 | Slideshow & Image Compare Embeds | Done |
| 10 | CSS Stylesheet & MkDocs Integration | Not Started |

## Overview

Port selected features from DigitalOcean's `do-markdownit` (JavaScript/markdown-it) to Python-Markdown
extensions for use with MkDocs. The new library lives at `/home/mmegger/Code/MasonEgger/do-markdown/`.

### Features to Implement

**Fence Features (single coordinated extension — `do_markdown.fence`):**
- `[label ...]` — div above code block
- `[secondary_label ...]` — div inside code block
- `[environment ...]` — CSS class on code block for colored environments
- `line_numbers` — incremental line number prefixes
- `command` — `$` prefix (non-root)
- `super_user` — `#` prefix (root)
- `custom_prefix(...)` — arbitrary prefix string

**Highlight (`do_markdown.highlight`):**
- `<^>text<^>` → `<mark>text</mark>` in regular text, inline code, and fenced code blocks

**Embeds (one extension each):**
- `[youtube ID height width]`
- `[codepen USER HASH flags...]`
- `[twitter URL flags...]`
- `[instagram URL flags...]`
- `[slideshow URL1 URL2 ... height width]`
- `[compare URL1 URL2 height width]`

### Architecture

```
/home/mmegger/Code/MasonEgger/do-markdown/
├── pyproject.toml
├── justfile
├── CLAUDE.md
├── src/
│   └── do_markdown/
│       ├── __init__.py
│       ├── highlight.py          # <^>...<^> → <mark>
│       ├── fence.py              # All fence features (label, secondary_label, env, prefix)
│       ├── youtube.py            # YouTube embed
│       ├── codepen.py            # CodePen embed
│       ├── twitter.py            # Twitter/X embed
│       ├── instagram.py          # Instagram embed
│       ├── slideshow.py          # Image slideshow
│       └── image_compare.py      # Side-by-side image comparison
└── tests/
    ├── conftest.py               # Shared fixtures (md instances with extensions loaded)
    ├── test_highlight.py
    ├── test_fence.py
    ├── test_youtube.py
    ├── test_codepen.py
    ├── test_twitter.py
    ├── test_instagram.py
    ├── test_slideshow.py
    └── test_image_compare.py
```

### Key Design Decisions

1. **Fence features share one Extension class** (`do_markdown.fence`). All fence modifications
   (label, secondary_label, environment, prefix) run in a coordinated Preprocessor + Postprocessor
   pair, avoiding ordering bugs from multiple independent wrappers.

2. **Preprocessor + Postprocessor pattern for fences.** The Preprocessor runs BEFORE
   `pymdownx.superfences` (higher priority), extracts directives from fence content, stores
   metadata via HTML comments (`<!-- do-fence:{...} -->`), and cleans the info string. The
   Postprocessor runs after all rendering and applies transformations to the final HTML.

3. **Embeds use Preprocessors** that run AFTER `pymdownx.superfences` (lower priority), so
   embed syntax inside fenced code blocks is already stashed and won't be matched. Each embed
   Preprocessor matches a single-line `[name ...]` pattern and replaces it with raw HTML.

4. **Script injection for social embeds.** CodePen, Twitter, and Instagram need `<script>` tags.
   Each extension's Postprocessor appends the script once at the end of the rendered content if
   any embeds of that type were found.

5. **Compatible with the website's existing stack.** The extensions work alongside
   `pymdownx.superfences`, `pymdownx.highlight` (Pygments), and MkDocs Material.

### HTML Output Contracts

These match the do-markdownit output format (see `/home/mmegger/Code/MasonEgger/do-markdownit/fixtures/full-output.html`):

**Label:**
```html
<div class="code-label" title="filename.py">filename.py</div>
<div class="highlight"><pre>...</pre></div>
```

**Secondary Label:**
```html
<pre><code><div class="secondary-code-label" title="Output">Output</div>code here
</code></pre>
```

**Environment:**
```html
<pre class="environment-local ..."><code>...</code></pre>
```

**Prefix (command):**
```html
<pre class="prefixed command"><code><ol><li data-prefix="$">line 1
</li><li data-prefix="$">line 2
</li></ol>
</code></pre>
```

**YouTube:**
```html
<iframe src="https://www.youtube.com/embed/ID" class="youtube" height="270" width="480"
  style="aspect-ratio: 16/9" frameborder="0" allowfullscreen>
    <a href="https://www.youtube.com/watch?v=ID" target="_blank">View YouTube video</a>
</iframe>
```

**CodePen:**
```html
<p class="codepen" data-height="256" data-theme-id="light" data-default-tab="result"
  data-user="USER" data-slug-hash="HASH"
  style="height: 256px; box-sizing: border-box; display: flex; align-items: center;
  justify-content: center; border: 2px solid; margin: 1em 0; padding: 1em;">
    <span>See the Pen <a href="...">HASH by USER</a> ...</span>
</p>
<script async defer src="https://static.codepen.io/assets/embed/ei.js"></script>
```

**Twitter:**
```html
<div class="twitter">
    <blockquote class="twitter-tweet" data-dnt="true" data-width="550" data-theme="light">
        <a href="https://twitter.com/USER/status/ID">View tweet by @USER</a>
    </blockquote>
</div>
<script async defer src="https://platform.twitter.com/widgets.js"></script>
```

**Instagram:**
```html
<div class="instagram">
    <blockquote class="instagram-media" data-instgrm-permalink="URL" data-instgrm-version="14">
        <a href="URL">View post</a>
    </blockquote>
</div>
<script async defer src="https://www.instagram.com/embed.js"
  onload="window.instgrm && window.instgrm.Embeds.process()"></script>
```

**Slideshow:**
```html
<div class="slideshow" style="height: 270px; width: 480px;">
  <div class="action left" onclick="...">&#8249;</div>
  <div class="action right" onclick="...">&#8250;</div>
  <div class="slides">
    <img src="URL1" alt="Slide #1" />
    <img src="URL2" alt="Slide #2" />
  </div>
</div>
```

**Image Compare:**
```html
<div class="image-compare" style="--value:50%; height: 270px; width: 480px;">
    <img class="image-left" src="URL1" alt="Image left"/>
    <img class="image-right" src="URL2" alt="Image right"/>
    <input type="range" class="control" min="0" max="100" value="50"
      oninput="this.parentNode.style.setProperty('--value', `${this.value}%`)" />
    <svg class="control-arrow" ...>...</svg>
</div>
```

---

## Step 1: Project Scaffolding

**NOTE**: This creates a brand new Python project at `/home/mmegger/Code/MasonEgger/do-markdown/`.
Uses `uv` for dependency management. The website project will later reference this as a local
dependency.

```text
Prompt for code-generation LLM:

You are building a new Python library called "do-markdown" — a set of Python-Markdown extensions
that port features from DigitalOcean's do-markdownit JavaScript library to Python. The project
lives at /home/mmegger/Code/MasonEgger/do-markdown/.

1. Create project directory and initialize with uv:
   - Run: mkdir -p /home/mmegger/Code/MasonEgger/do-markdown
   - Run: cd /home/mmegger/Code/MasonEgger/do-markdown && uv init --lib --package --name do-markdown

2. Configure pyproject.toml at /home/mmegger/Code/MasonEgger/do-markdown/pyproject.toml:
   - Set name = "do-markdown"
   - Set version = "0.1.0"
   - Set description = "Python-Markdown extensions ported from DigitalOcean's do-markdownit"
   - Set requires-python = ">=3.14"
   - Set license = "MIT"
   - Add dependency: markdown>=3.4
   - Add dev dependencies (in [dependency-groups] dev): pytest>=8.0, pymdown-extensions>=10.5, ruff>=0.5, mypy>=1.10
   - Configure [tool.pytest.ini_options] with testpaths = ["tests"]
   - Configure [tool.ruff] with target-version = "py314", line-length = 120
   - Configure [tool.ruff.lint] with select = ["E", "F", "I", "UP", "B", "SIM"]
   - Configure [tool.mypy] with strict = true, python_version = "3.14"

3. Create justfile at /home/mmegger/Code/MasonEgger/do-markdown/justfile:
   - `install`: uv sync
   - `test`: uv run pytest
   - `test-verbose`: uv run pytest -v
   - `lint`: uv run ruff check src/ tests/
   - `format`: uv run ruff format src/ tests/
   - `check`: uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy --strict src/ && uv run pytest

4. Create src/do_markdown/__init__.py at /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/__init__.py:
   - Leave empty — never add anything to __init__.py

5. Create tests/conftest.py at /home/mmegger/Code/MasonEgger/do-markdown/tests/conftest.py:
   - Add ABOUTME comment: "ABOUTME: Shared pytest fixtures for do-markdown extension tests."
   - Second line: "Provides pre-configured Markdown instances that mirror the real site stack."
   - Import markdown, pytest
   - Create fixture `md_with_superfences` (with type hint `-> markdown.Markdown`) that returns
     markdown.Markdown(
       extensions=["pymdownx.superfences", "pymdownx.highlight"],
       extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}}
     )
   - Do NOT create a `md_basic` fixture — that tests the markdown library, not our code

6. Create a smoke test at /home/mmegger/Code/MasonEgger/do-markdown/tests/test_smoke.py:
   - Add ABOUTME comment
   - Test that `import do_markdown` works
   - Test that package version via importlib.metadata matches "0.1.0"
   - Do NOT test that markdown.Markdown() can be instantiated — that tests the library

7. Run: cd /home/mmegger/Code/MasonEgger/do-markdown && uv sync && uv run pytest -v
   - Verify smoke tests pass

8. Run full verification: just check
   - Verify ruff lint, ruff format, mypy strict, and pytest all pass

9. Fix any issues found by mypy or ruff format check
```

---

## Step 2: Highlight Extension (`<^>...<^>`)

**NOTE**: This extension handles `<^>text<^>` → `<mark>text</mark>`. It works in three contexts:
(a) regular inline text, (b) inside inline code, and (c) inside fenced code blocks. The site
already has `pymdownx.mark` for `==text==` → `<mark>`, but that doesn't work inside code blocks.
This extension specifically enables highlighting inside code via post-processing of rendered HTML.

```text
Prompt for code-generation LLM:

You are implementing the "highlight" extension for the do-markdown library at
/home/mmegger/Code/MasonEgger/do-markdown/. This extension converts `<^>text<^>` to
`<mark>text</mark>` everywhere — including inside code blocks where pymdownx.mark can't reach.

Reference: /home/mmegger/Code/MasonEgger/do-markdownit/rules/highlight.js

1. RED: Write tests first:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/tests/test_highlight.py:
     - Add ABOUTME comment
     - Test inline highlight: `"This is a <^>variable<^>"` → output contains `<mark>variable</mark>`
     - Test inline code highlight: `` "`code <^>var<^>`" `` → output contains `<code>code <mark>var</mark></code>`
     - Test fenced code highlight (use md_with_superfences fixture):
       "```\nhello\n<^>highlighted<^>\n```" → output contains `<mark>highlighted</mark>` inside pre/code
     - Test multiple highlights on same line: `"<^>a<^> and <^>b<^>"` →
       contains `<mark>a</mark>` and `<mark>b</mark>`
     - Test no match for incomplete syntax: `"<^>unclosed"` → no `<mark>` in output
     - Test no match for empty highlight: `"<^><^>"` → no `<mark>` tags wrapping empty content
       (or contains `<mark></mark>` — verify which behavior the JS version produces and match it)
     - Each test should load the highlight extension via
       `markdown.Markdown(extensions=["do_markdown.highlight"])`

2. GREEN: Implement the highlight extension:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/highlight.py:
     - Add ABOUTME comment: "ABOUTME: Highlight extension converting <^>text<^> to <mark> tags."
     - Second line: "Works in regular text, inline code, and fenced code blocks."
     - Create class `HighlightExtension(Extension)` with `extendMarkdown(self, md)` method
     - Register a `HighlightInlineProcessor(InlineProcessor)`:
       - Pattern: r'<\^>(.*?)<\^>' (non-greedy match between markers)
       - `handleMatch` creates an `etree.Element('mark')` with the matched text
       - Register at priority 175 (before emphasis)
     - Register a `HighlightPostprocessor(Postprocessor)`:
       - Replaces `&lt;^&gt;(.*?)&lt;^&gt;` with `<mark>\1</mark>` in rendered HTML
       - This catches <^> inside code blocks where the < > were HTML-escaped
       - Register at priority 25
     - Add `makeExtension(**kwargs)` function returning `HighlightExtension(**kwargs)`

3. Run tests: cd /home/mmegger/Code/MasonEgger/do-markdown && uv run pytest tests/test_highlight.py -v
   - All tests should pass

4. REFACTOR: Review the extension:
   - Ensure HTML escaping is correct (the postprocessor regex handles escaped entities)
   - Ensure the InlineProcessor doesn't interfere with code blocks (it won't — code blocks
     are processed separately)

5. Run full verification: just check
```

---

## Step 3: Fence Extension — Directive Parsing & Labels

**NOTE**: This is the first part of the fence extension. It implements the Preprocessor that
extracts `[label ...]` and `[secondary_label ...]` directives from fence content, and the
Postprocessor that injects the label HTML. The Preprocessor stores metadata in HTML comments
(`<!-- do-fence:{...} -->`) placed before each fence block.

The user's site uses `pymdownx.superfences` (Preprocessor priority ~38) and `pymdownx.highlight`.
Our Preprocessor must run BEFORE superfences (priority > 38, e.g., 40). Our Postprocessor runs
after all rendering (priority ~25).

```text
Prompt for code-generation LLM:

You are implementing the fence extension for do-markdown at
/home/mmegger/Code/MasonEgger/do-markdown/. This step handles [label] and [secondary_label]
directives inside fenced code blocks.

Reference files:
- /home/mmegger/Code/MasonEgger/do-markdownit/modifiers/fence_label.js
- /home/mmegger/Code/MasonEgger/do-markdownit/modifiers/fence_secondary_label.js
- /home/mmegger/Code/MasonEgger/do-markdownit/fixtures/full-output.html (lines 124-141)

1. RED: Write tests first:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/tests/test_fence.py:
     - Add ABOUTME comment
     - Import markdown, re, pytest, and the conftest fixtures
     - Helper function: `render_fence(source)` that creates a Markdown instance with
       extensions=["pymdownx.superfences", "pymdownx.highlight", "do_markdown.fence"]
       and extension_configs for highlight (pygments_lang_class: True), then calls md.convert(source)
     - Test label basic: input is "```\n[label test.py]\nhello\n```"
       → output contains `<div class="code-label" title="test.py">test.py</div>`
       → output contains `hello` inside a code element
       → output does NOT contain `[label test.py]` as visible text
     - Test label with language: "```python\n[label app.py]\nprint('hi')\n```"
       → output contains `<div class="code-label" title="app.py">app.py</div>`
       → output contains a pre element with language class
     - Test secondary_label: "```\n[secondary_label Output]\nerror msg\n```"
       → output contains `<div class="secondary-code-label" title="Output">Output</div>`
       → output does NOT contain `[secondary_label Output]` as visible text
     - Test no directives: "```\nplain code\n```"
       → output does NOT contain `do-fence` comment
       → output does NOT contain `code-label`
     - Test label with special characters: "```\n[label /etc/nginx/sites-available/default]\ncode\n```"
       → output contains the full path in the label, properly HTML-escaped
     - Test both label and secondary_label together:
       "```\n[label file.py]\n[secondary_label Output]\ncode\n```"
       → output contains both label divs
       → directives are stripped from code content

2. GREEN: Implement the fence extension:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/fence.py:
     - Add ABOUTME comment: "ABOUTME: Fence extension adding labels, environments, and line prefixes to code blocks."
       Second line: "Coordinates a Preprocessor and Postprocessor for all fence enhancements."
     - Import: markdown, re, json, html, xml.etree.ElementTree
     - Define FENCE_RE = re.compile(r'^(`{3,}|~{3,})') for detecting fence delimiters
     - Define LABEL_RE = re.compile(r'^\[label (.+)\]$')
     - Define SECONDARY_LABEL_RE = re.compile(r'^\[secondary_label (.+)\]$')

     - Create class `FencePreprocessor(Preprocessor)`:
       - `run(self, lines)` method:
         - Iterate through lines, tracking when inside a fence block
         - When a fence opening is found, scan subsequent lines for directives
         - For each matched directive ([label ...], [secondary_label ...]), store in a metadata dict
         - Remove directive lines from the output
         - Inject `<!-- do-fence:JSON_METADATA -->` on the line before the fence opening
         - Return modified lines
       - Priority: 40 (runs before superfences at ~38)

     - Create class `FencePostprocessor(Postprocessor)`:
       - `run(self, text)` method:
         - Find all `<!-- do-fence:(.*?) -->` patterns in the HTML
         - For each match, parse the JSON metadata
         - If label exists: inject `<div class="code-label" title="LABEL">LABEL</div>\n`
           before the next <div class="highlight"> or <pre> element
         - If secondary_label exists: inject
           `<div class="secondary-code-label" title="LABEL">LABEL</div>`
           immediately after the opening <code...> tag
         - Remove the do-fence comment from output
         - Return modified HTML
       - Priority: 25

     - Create class `FenceExtension(Extension)`:
       - `extendMarkdown(self, md)`: register FencePreprocessor and FencePostprocessor
       - Store config options: label_class (default "code-label"),
         secondary_label_class (default "secondary-code-label")
     - Add `makeExtension(**kwargs)` function

3. Run tests: uv run pytest tests/test_fence.py -v
   - All label/secondary_label tests should pass

4. REFACTOR:
   - Ensure HTML escaping on label text (use html.escape())
   - Ensure the preprocessor correctly handles nested fences (different delimiter lengths)
   - Ensure blank lines between directive lines are handled

5. Run full verification: just check
```

---

## Step 4: Fence Extension — Environment Classes

**NOTE**: Extends the fence extension from Step 3 to support `[environment NAME]` directives
that add `environment-NAME` CSS class to the code block's `<pre>` element. This enables
different colored code blocks for different server environments.

```text
Prompt for code-generation LLM:

You are extending the fence extension at
/home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/fence.py to support environment
directives. The [environment NAME] directive adds an `environment-NAME` CSS class to the
rendered code block.

Reference: /home/mmegger/Code/MasonEgger/do-markdownit/modifiers/fence_environment.js

1. RED: Write additional tests:
   - Add to /home/mmegger/Code/MasonEgger/do-markdown/tests/test_fence.py:
     - Test environment basic: "```command\n[environment local]\nssh root@server\n```"
       → output contains class `environment-local` on the pre element
       → output does NOT contain `[environment local]` as visible text
     - Test environment with allowed list: configure extension with
       allowed_environments=["local", "staging", "production"]. Input with `[environment local]`
       → class is applied. Input with `[environment unknown]` → class is NOT applied,
       directive line remains as code content.
     - Test environment with label: "```\n[environment local]\n[label server.sh]\ncode\n```"
       → output contains both environment class AND label div
     - Test environment with secondary_label:
       "```\n[environment second]\n[secondary_label Output]\ncode\n```"
       → output contains both environment class AND secondary label
     - Test multiple environments defined in the allowed list produce different classes:
       Test "second" → "environment-second", "third" → "environment-third"

2. GREEN: Extend the fence extension:
   - Modify /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/fence.py:
     - Add ENVIRONMENT_RE = re.compile(r'^\[environment (.+)\]$')
     - In FencePreprocessor.run(): also scan for [environment ...] directives
       - Add "environment" key to the metadata dict
       - Strip the directive line from content
     - In FencePostprocessor.run():
       - If environment exists in metadata: add `environment-NAME` class to the <pre> element
       - Handle adding class to an existing class attribute or creating one
     - In FenceExtension config: add `allowed_environments` option (default: empty list = allow all)
     - In FencePreprocessor: check against allowed_environments if configured.
       If the environment is not allowed, leave the directive line in place (don't strip it).

3. Run tests: uv run pytest tests/test_fence.py -v

4. REFACTOR:
   - Ensure environment name is sanitized for use as a CSS class (alphanumeric + hyphens only)
   - Ensure the preprocessor handles directive ordering: [environment], [label],
     [secondary_label] can appear in any order in the first lines of the fence

5. Run full verification: just check
```

---

## Step 5: Fence Extension — Line Prefixes

**NOTE**: Extends the fence extension to support line prefixes via the info string:
`line_numbers`, `command` ($), `super_user` (#), and `custom_prefix(TEXT)`. These wrap each
code line in `<ol><li data-prefix="...">`. The `command`, `super_user`, and `custom_prefix`
flags also implicitly add `bash` as the language.

```text
Prompt for code-generation LLM:

You are extending the fence extension at
/home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/fence.py to support line prefix features.
These are specified in the fence info string (after the opening backticks).

Reference: /home/mmegger/Code/MasonEgger/do-markdownit/modifiers/fence_prefix.js

Info string syntax (comma-delimited, language can be mixed in):
- `line_numbers` or `line_numbers,js` → prefix each line with its line number
- `command` → prefix with "$", implicitly set language to bash
- `super_user` → prefix with "#", implicitly set language to bash
- `custom_prefix(mysql>)` → prefix with "mysql>", implicitly set language to bash
- `custom_prefix((my-server)\smysql>)` → \s becomes space in the prefix

1. RED: Write additional tests:
   - Add to /home/mmegger/Code/MasonEgger/do-markdown/tests/test_fence.py:
     - Test line_numbers: "```line_numbers,js\nconst a = 1;\nconst b = 2;\n```"
       → output contains `data-prefix="1"` and `data-prefix="2"`
       → output contains `<ol>` wrapping the `<li>` elements
       → output contains class `prefixed` and `line_numbers` on the pre element
     - Test command: "```command\nsudo apt update\n```"
       → output contains `data-prefix="$"`
       → output contains class `prefixed` and `command` on the pre element
       → code is highlighted as bash (language-bash class present)
     - Test super_user: "```super_user\nshutdown\n```"
       → output contains `data-prefix="#"`
       → output contains class `prefixed` and `super_user`
     - Test custom_prefix: "```custom_prefix(mysql>)\nSELECT 1;\n```"
       → output contains `data-prefix="mysql&gt;"` (HTML-escaped)
       → output contains class `prefixed` and `custom_prefix`
     - Test custom_prefix with \s: "```custom_prefix((srv)\smysql>)\nSELECT 1;\n```"
       → output contains `data-prefix="(srv) mysql&gt;"`
     - Test line_numbers with language: "```line_numbers,python\nprint('hi')\n```"
       → has line numbers AND python syntax highlighting
     - Test command with environment and label (full combo):
       "```command\n[environment local]\n[label server.sh]\nssh root@ip\n```"
       → has $ prefix, environment-local class, label div, all together
     - Test no prefix: "```python\ncode\n```" → no <ol>, no data-prefix, no prefixed class

2. GREEN: Extend the fence extension:
   - Modify /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/fence.py:
     - Add PREFIX_PATTERNS to detect prefix flags in the info string:
       - "line_numbers" → prefix_type="line_numbers", prefix_fn returns line index + 1
       - "command" → prefix_type="command", prefix_fn returns "$", add "bash" to language
       - "super_user" → prefix_type="super_user", prefix_fn returns "#", add "bash" to language
       - custom_prefix(TEXT) regex → prefix_type="custom_prefix", prefix_fn returns TEXT
         with \s replaced by space, add "bash" to language
     - In FencePreprocessor.run():
       - When a fence opening is found, parse the info string for prefix flags
       - Extract prefix metadata (type, value)
       - Clean the info string: remove prefix flags, keep language identifier
       - If command/super_user/custom_prefix and no language specified, add "bash"
       - Store prefix metadata in the do-fence comment JSON
       - Add CSS classes (prefixed, prefix_type) to the metadata for the pre element
     - In FencePostprocessor.run():
       - If prefix metadata exists:
         - Find the content inside <code>...</code>
         - Split content by newlines (handling potential Pygments span wrappers)
         - Wrap each line in <li data-prefix="VALUE">...</li>
         - Wrap all lines in <ol>...</ol>
         - For line_numbers, prefix is the 1-based index
         - For command, prefix is "$"
         - For super_user, prefix is "#"
         - For custom_prefix, prefix is the specified text
         - HTML-escape the prefix value
       - Add prefixed + type classes to <pre> element

3. Run tests: uv run pytest tests/test_fence.py -v

4. RED: Write a combined integration test:
   - Test the full combo from the DO playground:
     "```line_numbers,html\n[environment second]\n[label index.html]\n<html>\n<body>\n</body>\n</html>\n```"
     → has line numbers 1-5
     → has environment-second class
     → has label div with "index.html"
     → has HTML syntax highlighting
     → has prefixed and line_numbers classes

5. GREEN: Fix any issues found in integration test

6. REFACTOR:
   - Extract the line-wrapping logic into a helper function
   - Ensure the Pygments-highlighted HTML is not broken by line splitting
     (Pygments with line_spans wraps each line, making splitting reliable)
   - Review all fence tests to ensure they pass together

7. Run full verification: just check
```

---

## Step 6: YouTube Embed

**NOTE**: First embed implementation. Establishes the pattern for all subsequent embeds. Uses a
Preprocessor that matches `[youtube ID height width]` on standalone lines and replaces with
iframe HTML.

```text
Prompt for code-generation LLM:

You are implementing the YouTube embed extension for do-markdown at
/home/mmegger/Code/MasonEgger/do-markdown/. This is the first embed — it establishes the
pattern used by all subsequent embed extensions.

Reference: /home/mmegger/Code/MasonEgger/do-markdownit/rules/embeds/youtube.js

Syntax: `[youtube VIDEO_ID]` or `[youtube VIDEO_ID HEIGHT WIDTH]`
- Default height: 270, default width: 480
- Output: responsive iframe with aspect-ratio

1. RED: Write tests first:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/tests/test_youtube.py:
     - Add ABOUTME comment
     - Helper: `render(source)` using markdown.Markdown(extensions=["do_markdown.youtube"])
     - Test basic embed: "[youtube iom_nhYQIYk]"
       → output contains `<iframe src="https://www.youtube.com/embed/iom_nhYQIYk"`
       → output contains `height="270"` and `width="480"` (defaults)
       → output contains `class="youtube"`
       → output contains fallback link inside iframe
     - Test custom dimensions: "[youtube iom_nhYQIYk 225 400]"
       → output contains `height="225"` and `width="400"`
       → output contains `style="aspect-ratio: 16/9"` (225/400 reduces to 9/16 → displayed as 16/9)
     - Test height only: "[youtube iom_nhYQIYk 380]"
       → output contains `height="380"` and `width="480"` (width defaults)
     - Test not matched inside paragraph: "Some text [youtube abc] more text"
       → output does NOT contain iframe (must be standalone line)
     - Test not matched inside fence: "```\n[youtube abc]\n```"
       → output does NOT contain iframe (should be code content)
       (Use md_with_superfences fixture + youtube extension for this test)
     - Test video ID is URL-encoded in src: "[youtube a&b<c]"
       → src contains properly encoded ID
     - Test aspect ratio calculation: "[youtube abc 270 480]" → aspect-ratio: 16/9
       Test "[youtube abc 100 100]" → aspect-ratio: 1/1

2. Implement a shared utility:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/_util.py:
     - Add ABOUTME comment: "ABOUTME: Shared utility functions for do-markdown extensions."
       Second line: "Provides fraction reduction helper used by embed extensions."
     - Implement `reduce_fraction(a: int, b: int) -> tuple[int, int]`:
       Uses math.gcd to reduce a fraction. E.g., reduce_fraction(480, 270) → (16, 9)
     - Do NOT wrap html.escape() — call it directly where needed (no trivial wrappers)

3. GREEN: Implement the YouTube extension:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/youtube.py:
     - Add ABOUTME comment: "ABOUTME: YouTube embed extension for Python-Markdown."
       Second line: "Converts [youtube ID height width] syntax to responsive iframe embeds."
     - Create class `YouTubePreprocessor(Preprocessor)`:
       - Pattern: re.compile(r'^\[youtube (\S+?)(?:\s+(\d+))?(?:\s+(\d+))?\]$')
       - `run(self, lines)`: iterate lines, match pattern on stripped lines,
         replace matched lines with generated HTML
       - HTML template matches the do-markdownit output (see HTML contracts above)
       - Uses reduce_fraction for aspect-ratio calculation
       - URL-encodes the video ID with urllib.parse.quote
       - Priority: 20 (runs after superfences at ~38 has already processed fences)
     - Create class `YouTubeExtension(Extension)`:
       - `extendMarkdown(self, md)`: register YouTubePreprocessor
     - Add `makeExtension(**kwargs)`

4. Run tests: uv run pytest tests/test_youtube.py -v

5. REFACTOR:
   - Verify the HTML output matches the do-markdownit reference output exactly
   - Ensure the preprocessor only matches lines with no leading whitespace
     (or ≤3 spaces, consistent with Markdown block content)

6. Run full verification: just check
```

---

## Step 7: CodePen Embed

**NOTE**: More complex embed with flag parsing (theme, tabs, height, lazy, editable) and
script injection. The script tag should only be added once even if multiple CodePen embeds exist.

```text
Prompt for code-generation LLM:

You are implementing the CodePen embed extension for do-markdown at
/home/mmegger/Code/MasonEgger/do-markdown/.

Reference: /home/mmegger/Code/MasonEgger/do-markdownit/rules/embeds/codepen.js

Syntax: `[codepen USER HASH flags...]`
Flags (space-separated, any order after USER and HASH):
- `lazy` — adds data-preview="true"
- `light` or `dark` — theme (default: light, dark wins if both present)
- `html`, `css`, `js` — default tab (priority: html > css > js)
- `result` — result tab (default tab, can combine with others like "html,result")
- `editable` — adds data-editable="true"
- Any integer — custom height in px (default: 256)

Script injection: append CodePen embed script once at end of content.

1. RED: Write tests first:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/tests/test_codepen.py:
     - Add ABOUTME comment
     - Helper: `render(source)` using markdown.Markdown(extensions=["do_markdown.codepen"])
     - Test basic: "[codepen MattCowley vwPzeX]"
       → contains `data-user="MattCowley"` and `data-slug-hash="vwPzeX"`
       → contains `data-height="256"` (default)
       → contains `data-theme-id="light"` (default)
       → contains `data-default-tab="result"` (default)
       → contains the CodePen script tag
     - Test dark theme: "[codepen User Hash dark]"
       → contains `data-theme-id="dark"`
     - Test custom height: "[codepen User Hash 512]"
       → contains `data-height="512"` and `style="height: 512px;`
     - Test tab selection: "[codepen User Hash css]"
       → contains `data-default-tab="css"`
     - Test tab with result: "[codepen User Hash html result]"
       → contains `data-default-tab="html,result"`
     - Test lazy: "[codepen User Hash lazy]"
       → contains `data-preview="true"`
     - Test editable: "[codepen User Hash editable]"
       → contains `data-editable="true"`
     - Test combined flags: "[codepen User Hash dark css 384 lazy]"
       → dark theme, css tab, 384 height, lazy
     - Test tab priority (html wins over css): "[codepen User Hash css html]"
       → contains `data-default-tab="html"` (html preferred)
     - Test script injected only once for multiple embeds:
       "[codepen A B]\n\nSome text\n\n[codepen C D]"
       → output contains exactly ONE script tag for codepen

2. GREEN: Implement the CodePen extension:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/codepen.py:
     - Add ABOUTME comment
     - Create `CodePenPreprocessor(Preprocessor)`:
       - Regex matches `[codepen USER HASH optional_flags]`
       - Parse flags: extract height (integer), theme (dark/light), tab, lazy, editable
       - Tab priority: html > css > js. If result also present, combine: "html,result"
       - Track whether any codepen was found (instance var `self._found`)
       - Replace matched lines with HTML (see HTML contract above)
       - Priority: 20
     - Create `CodePenPostprocessor(Postprocessor)`:
       - If self.preprocessor._found is True, append script tag at end of content
       - Script: `<script async defer src="https://static.codepen.io/assets/embed/ei.js" type="text/javascript"></script>`
       - Priority: 15
     - Create `CodePenExtension(Extension)`:
       - Register both processors, link them so postprocessor can check preprocessor state
     - Add `makeExtension(**kwargs)`

3. Run tests: uv run pytest tests/test_codepen.py -v

4. REFACTOR:
   - Verify HTML output matches do-markdownit reference
   - Ensure user/hash are properly HTML-escaped and URL-encoded

5. Run full verification: just check
```

---

## Step 8: Twitter & Instagram Embeds

**NOTE**: Both follow a similar pattern to CodePen: line matching with flags, script injection.
Grouped together since the implementation pattern is established. Twitter accepts both
twitter.com and x.com URLs. Instagram accepts instagram.com URLs.

```text
Prompt for code-generation LLM:

You are implementing Twitter and Instagram embed extensions for do-markdown at
/home/mmegger/Code/MasonEgger/do-markdown/.

References:
- /home/mmegger/Code/MasonEgger/do-markdownit/rules/embeds/twitter.js
- /home/mmegger/Code/MasonEgger/do-markdownit/rules/embeds/instagram.js

Twitter syntax: `[twitter URL flags...]`
- URL: https://twitter.com/USER/status/ID or https://x.com/USER/status/ID
- Flags: `light`/`dark` (default: light), `left`/`center`/`right` (default: center),
  integer for width (clamped 250-550, default: 550)
- Output always canonicalizes to twitter.com URL

Instagram syntax: `[instagram URL flags...]`
- URL: https://www.instagram.com/p/POST_ID
- Flags: `caption`, `left`/`center`/`right` (default: center),
  integer for width (clamped 326-550, default: 0 = auto)

1. RED: Write Twitter tests:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/tests/test_twitter.py:
     - Add ABOUTME comment
     - Helper: `render(source)` using markdown.Markdown(extensions=["do_markdown.twitter"])
     - Test basic: "[twitter https://twitter.com/User/status/123]"
       → contains `<div class="twitter">`
       → contains `<blockquote class="twitter-tweet"` with `data-dnt="true"`
       → contains `data-width="550"` and `data-theme="light"` (defaults)
       → contains link to `https://twitter.com/User/status/123`
       → contains twitter widgets.js script tag
     - Test x.com domain: "[twitter https://x.com/User/status/123]"
       → output canonicalizes to twitter.com in the link
     - Test dark theme: "[twitter https://twitter.com/U/status/1 dark]"
       → contains `data-theme="dark"`
     - Test alignment: "[twitter https://twitter.com/U/status/1 left]"
       → contains `align="left"` on the div
     - Test center alignment (default): no align attribute on div (center is default)
     - Test custom width: "[twitter https://twitter.com/U/status/1 400]"
       → contains `data-width="400"`
     - Test width clamping: "[twitter https://twitter.com/U/status/1 100]"
       → contains `data-width="250"` (min clamp)
     - Test width clamping max: "[twitter https://twitter.com/U/status/1 999]"
       → contains `data-width="550"` (max clamp)
     - Test combined flags: "[twitter https://twitter.com/U/status/1 left 400 dark]"
       → dark, left-aligned, width 400
     - Test script injected once for multiple tweets

2. RED: Write Instagram tests:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/tests/test_instagram.py:
     - Add ABOUTME comment
     - Helper: `render(source)` using markdown.Markdown(extensions=["do_markdown.instagram"])
     - Test basic: "[instagram https://www.instagram.com/p/CkQuv3_LRgS]"
       → contains `<div class="instagram">`
       → contains `<blockquote class="instagram-media"`
       → contains `data-instgrm-permalink` with the URL
       → contains `data-instgrm-version="14"`
       → contains instagram embed.js script
     - Test caption flag: "[instagram https://www.instagram.com/p/ABC caption]"
       → contains `data-instgrm-captioned`
     - Test alignment: "[instagram https://www.instagram.com/p/ABC left]"
       → contains `align="left"` on the div
     - Test custom width: "[instagram https://www.instagram.com/p/ABC 400]"
       → contains `style="width: 400px;"`
     - Test width clamping min: "[instagram https://www.instagram.com/p/ABC 100]"
       → width clamped to 326
     - Test combined: "[instagram https://www.instagram.com/p/ABC left caption 400]"
       → left-aligned, captioned, 400px width
     - Test script injected once for multiple posts

3. GREEN: Implement Twitter extension:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/twitter.py:
     - Add ABOUTME comment
     - Regex accepts both twitter.com and x.com domains
     - Extract user and status ID from URL
     - Parse flags: theme, alignment, width (with clamping)
     - TwitterPreprocessor (priority 20) + TwitterPostprocessor (priority 15 for script)
     - HTML output matches do-markdownit reference
     - Add `makeExtension(**kwargs)`

4. GREEN: Implement Instagram extension:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/instagram.py:
     - Add ABOUTME comment
     - Regex parses instagram.com/p/POST_ID URL
     - Parse flags: caption, alignment, width (with clamping)
     - InstagramPreprocessor (priority 20) + InstagramPostprocessor (priority 15 for script)
     - HTML output matches do-markdownit reference
     - Add `makeExtension(**kwargs)`

5. Run tests: uv run pytest tests/test_twitter.py tests/test_instagram.py -v

6. REFACTOR:
   - Look for shared patterns between CodePen, Twitter, and Instagram
   - If there's significant duplication in script injection logic, extract a base class
     or mixin (e.g., ScriptInjectingExtension) into _util.py
   - Do NOT over-abstract — only extract if 3+ extensions share the same pattern

7. Run full verification: just check
```

---

## Step 9: Slideshow & Image Compare Embeds

**NOTE**: These are simpler embeds with no script injection. Slideshow takes multiple image URLs.
Image compare takes exactly two URLs. Both have optional height/width dimensions.

```text
Prompt for code-generation LLM:

You are implementing Slideshow and Image Compare embed extensions for do-markdown at
/home/mmegger/Code/MasonEgger/do-markdown/.

References:
- /home/mmegger/Code/MasonEgger/do-markdownit/rules/embeds/slideshow.js
- /home/mmegger/Code/MasonEgger/do-markdownit/rules/embeds/compare.js

Slideshow syntax: `[slideshow URL1 URL2 ...URLs HEIGHT WIDTH]`
- 2+ image URLs required
- Height/width are optional trailing integers (default: 270, 480)
- Integers are distinguished from URLs by being purely numeric

Image Compare syntax: `[compare URL1 URL2 HEIGHT WIDTH]`
- Exactly 2 image URLs
- Height/width optional (default: 270, 480)

1. RED: Write Slideshow tests:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/tests/test_slideshow.py:
     - Add ABOUTME comment
     - Helper: `render(source)` using markdown.Markdown(extensions=["do_markdown.slideshow"])
     - Test basic: "[slideshow https://img1.png https://img2.png https://img3.png]"
       → contains `<div class="slideshow"`
       → contains 3 img tags with alt="Slide #1", "Slide #2", "Slide #3"
       → contains default dimensions: height: 270px; width: 480px
       → contains left/right navigation divs with &#8249; and &#8250;
     - Test custom dimensions: "[slideshow https://a.png https://b.png 225 400]"
       → contains `height: 225px; width: 400px`
       → scroll amount in onclick matches width (400)
     - Test two images (minimum): "[slideshow https://a.png https://b.png]"
       → contains 2 img tags
     - Test single image not matched: "[slideshow https://a.png]"
       → not rendered as slideshow (need 2+ images)
     - Test URLs are HTML-escaped: "[slideshow https://a.png?q=1&b=2 https://c.png]"
       → src contains properly escaped URL

2. RED: Write Image Compare tests:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/tests/test_image_compare.py:
     - Add ABOUTME comment
     - Helper: `render(source)` using markdown.Markdown(extensions=["do_markdown.image_compare"])
     - Test basic: "[compare https://left.png https://right.png]"
       → contains `<div class="image-compare"`
       → contains `style="--value:50%;` with default dimensions
       → contains `class="image-left"` and `class="image-right"` imgs
       → contains range input with min=0, max=100, value=50
       → contains SVG control arrow
     - Test custom dimensions: "[compare https://a.png https://b.png 500 600]"
       → contains `height: 500px; width: 600px`
     - Test URLs are HTML-escaped in src attributes
     - Test only two URLs accepted (no more, no fewer)

3. GREEN: Implement Slideshow extension:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/slideshow.py:
     - Add ABOUTME comment
     - SlideshowPreprocessor: parse line, separate URLs from trailing integers,
       require at least 2 URLs
     - HTML output matches do-markdownit reference (see HTML contracts)
     - Priority 20
     - Add `makeExtension(**kwargs)`

4. GREEN: Implement Image Compare extension:
   - Create /home/mmegger/Code/MasonEgger/do-markdown/src/do_markdown/image_compare.py:
     - Add ABOUTME comment
     - ImageComparePreprocessor: regex matches exactly 2 URLs + optional dimensions
     - HTML includes the range slider and SVG arrow (copy SVG path from JS reference)
     - Priority 20
     - Add `makeExtension(**kwargs)`

5. Run tests: uv run pytest tests/test_slideshow.py tests/test_image_compare.py -v

6. REFACTOR: Review all embed extensions for consistent patterns

7. Run full verification: just check
```

---

## Step 10: CSS Stylesheet & MkDocs Integration

**NOTE**: Final step. Creates the CSS for all extensions, adds the library as a dependency to
the website project, configures the extensions in mkdocs.yml, and verifies everything renders
correctly with `just build`.

```text
Prompt for code-generation LLM:

You are finalizing the do-markdown library by creating a CSS stylesheet for all extensions and
wiring it into the MkDocs website at /home/mmegger/Code/MasonEgger/website/.

Reference CSS patterns:
- /home/mmegger/Code/MasonEgger/do-markdownit/fixtures/full-output.html (for class names)

1. Create CSS stylesheet:
   - Add styles to /home/mmegger/Code/MasonEgger/website/docs/stylesheets/extra.css
     (append to existing file, clearly section off do-markdown styles):

     /* --- do-markdown extension styles --- */

     /* Code labels */
     .code-label:
       - Background color matching the site theme (dark green #283618 or similar)
       - White/cream text, padding, rounded top corners
       - Sits flush above the code block (margin-bottom: 0, border-bottom-radius: 0)
       - The following pre should have no top margin and no top border-radius

     .secondary-code-label:
       - Smaller, muted label inside the code block
       - Positioned at top of code content

     /* Environment colors — 5 distinct colors */
     .environment-local → green-ish left border or background accent
     .environment-second → blue-ish
     .environment-third → orange-ish
     .environment-fourth → purple-ish
     .environment-fifth → red-ish
     (Use thick left border, 4px solid COLOR, on the pre element)

     /* Prefixed code blocks */
     pre.prefixed code ol:
       - list-style: none, margin: 0, padding: 0
     pre.prefixed code ol li:
       - position: relative, padding-left appropriate for prefix
     pre.prefixed code ol li::before or [data-prefix]::before:
       - Use data-prefix attr for content: attr(data-prefix)
       - Style: muted color, fixed width, right-aligned, user-select: none

     /* YouTube */
     iframe.youtube:
       - max-width: 100%, display: block, margin: 0 auto

     /* CodePen — mostly handled by CodePen's own styles, minimal overrides */

     /* Twitter */
     .twitter:
       - margin: 1em 0

     /* Instagram */
     .instagram:
       - margin: 1em 0

     /* Slideshow */
     .slideshow:
       - position: relative, overflow: hidden, margin: 1em auto
     .slideshow .slides:
       - display: flex, overflow-x: auto, scroll-snap-type: x mandatory
       - scroll-behavior: smooth
     .slideshow .slides img:
       - scroll-snap-align: start, flex-shrink: 0, width: 100%, object-fit: cover
     .slideshow .action:
       - position: absolute, top: 50%, cursor: pointer, font-size: 2em
       - background: rgba(0,0,0,0.3), color: white, padding, z-index: 1

     /* Image Compare */
     .image-compare:
       - position: relative, overflow: hidden, margin: 1em auto
     .image-compare .image-left:
       - position: absolute, clip-path using --value CSS variable
     .image-compare .image-right:
       - width: 100%
     .image-compare .control:
       - position: absolute, width: 100%, appearance: none, cursor: pointer
     .image-compare .control-arrow:
       - position: absolute, pointer-events: none

2. Add do-markdown as a local dependency to the website:
   - Edit /home/mmegger/Code/MasonEgger/website/pyproject.toml:
     - Add to dependencies: `do-markdown = { path = "../do-markdown", editable = true }`
   - Run: cd /home/mmegger/Code/MasonEgger/website && uv sync

3. Configure extensions in mkdocs.yml:
   - Edit /home/mmegger/Code/MasonEgger/website/mkdocs.yml:
     - Add to markdown_extensions section:
       - do_markdown.highlight
       - do_markdown.fence:
           allowed_environments: [local, second, third, fourth, fifth]
       - do_markdown.youtube
       - do_markdown.codepen
       - do_markdown.twitter
       - do_markdown.instagram
       - do_markdown.slideshow
       - do_markdown.image_compare

4. Create a test page:
   - Create /home/mmegger/Code/MasonEgger/website/docs/do-markdown-test.md with test content
     covering all features (use the content from
     /home/mmegger/Code/MasonEgger/do-markdownit/fixtures/full-input.md Steps 2 and 5
     as a starting point, keeping only the features we implemented)

5. Build and verify:
   - Run: cd /home/mmegger/Code/MasonEgger/website && just build
   - Check that the build succeeds with no errors
   - Run: just serve (start dev server)
   - Manually verify the test page renders correctly

6. Run the do-markdown test suite one final time:
   - cd /home/mmegger/Code/MasonEgger/do-markdown && just check

7. Clean up:
   - Remove the test page from nav (keep the file for reference but don't link it)
   - Verify just build still passes on the website
```

---

## Implementation Guidelines

### Code Standards
- **Type hints everywhere** — all functions, all parameters, all return types. No `Any`.
- **RST docstrings on all public interfaces** — classes, public methods, module-level functions
- **Absolute imports only** — never use relative imports (e.g., `from do_markdown._util import ...`)
- **Empty `__init__.py`** — never add anything to `__init__.py`
- **ABOUTME comments** — every source file starts with a 2-line comment (first line: `ABOUTME: ...`)
- **No trivial wrappers** — use `html.escape()` directly, don't wrap standard library functions

### Verification (just check)
After EVERY code change, run the full verification suite:

    just check   # which runs:
    # uv run ruff check src/ tests/          — Linting
    # uv run ruff format --check src/ tests/ — Formatting verification
    # uv run mypy --strict src/              — Type checking
    # uv run pytest                          — Tests

All four must pass before moving on. Type errors are bugs.

### Testing Strategy
- Each extension has its own test file with focused unit tests
- Tests create Markdown instances with the extension loaded and assert HTML output
- Use `md_with_superfences` fixture when testing fence extension (matches real site config)
- Test edge cases: empty input, special characters, missing parameters, multiple instances
- Do NOT test Python-Markdown or pymdownx behavior — only test our extension logic
- Do NOT test trivial code (getters, setters, simple assignments)
- Test behavior and outcomes, not implementation details

### HTML Output Matching
- Match the do-markdownit HTML output format as closely as possible
- The exact whitespace may differ from the JS version — that's OK
- Class names, attribute names, and structure must match
- Always HTML-escape user-provided content (labels, URLs, etc.)

### Extension Registration
- Every extension file must have a `makeExtension(**kwargs)` function at module level
- This is how Python-Markdown discovers and loads extensions
- Extensions are referenced in mkdocs.yml as `do_markdown.extensionname`

### Priority Reference
- Preprocessor priority > 38: runs before pymdownx.superfences
- Preprocessor priority 20: runs after superfences (safe for embeds)
- Postprocessor priority 25: standard post-processing
- Postprocessor priority 15: script injection (runs after other postprocessors)

## Success Metrics
1. Full verification passes: `cd /home/mmegger/Code/MasonEgger/do-markdown && just check`
2. Website builds cleanly: `cd /home/mmegger/Code/MasonEgger/website && just build`
3. Test page renders all features correctly in the browser
4. No regressions in existing website content
5. HTML output matches do-markdownit reference for all implemented features
