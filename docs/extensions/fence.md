# Fence

Adds labels, secondary labels, environment classes, and line prefixes to fenced code blocks.
All fence features are coordinated through a single extension to avoid ordering issues.

```command
[environment local]
[label server.sh]
[secondary_label Output]
ssh root@192.168.1.1
apt update && apt upgrade -y
```

````
[label Markdown]
```command
[environment local]
[label server.sh]
[secondary_label Output]
ssh root@192.168.1.1
apt update && apt upgrade -y
```
````

## Usage

Load `markwright.fence` alongside `pymdownx.superfences` and `pymdownx.highlight`; the fence postprocessor rewrites the code-block HTML those produce.

```python
import markdown

md = markdown.Markdown(
    extensions=[
        "pymdownx.superfences",
        "pymdownx.highlight",
        "markwright.fence",
    ],
    extension_configs={
        "markwright.fence": {
            "allowed_environments": ["local", "second", "third", "fourth", "fifth"],
        },
    },
)
```

| Option | Default | Description |
|--------|---------|-------------|
| `allowed_environments` | omitted (allow all) | List of allowed environment names. Omit it to allow every name; an empty list allows none and emits a `ConfigWarning`. |
| `label_class` | `code-label` | CSS class for the label div. |
| `secondary_label_class` | `secondary-code-label` | CSS class for the secondary label div. |

An `[environment NAME]` line outside `allowed_environments` stays in the code as text, and the post stage reports it (`mw post --warn`, `mw render --warn`, or a `markwright.Diagnostic` with the reason `disallowed-environment` in-process) without changing the HTML.
A fence holding only such a line gains an `mw-fence` marker to carry the report, so it renders as its own block like any fence with a directive.
The report names the first such line of each fence; [`disallowed_environments`](../config.md#diagnostics) lists every name in a document.

All three options apply the same way in-process, through `mw render`, and through the `mw pre | renderer | mw post` pipeline.

Directives work in any fenced code block CommonMark recognizes, including a fence indented up to three spaces, one nested inside a list item, and one inside a block quote (a `> [!NOTE]` alert, for example).
An unclosed fence is not a code block, so its directives are left as text.

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Labels

Add a label above a code block with `[label TEXT]` as the first line inside the fence:

````
```python
[label app.py]
from flask import Flask

app = Flask(__name__)
```
````

```python
[label app.py]
from flask import Flask

app = Flask(__name__)
```

## Secondary Labels

Add a secondary label inside the code block with `[secondary_label TEXT]`:

````
```
[secondary_label Output]
Hello, world!
```
````

```
[secondary_label Output]
Hello, world!
```

## Both Labels Together

````
```python
[label app.py]
[secondary_label Output]
Hello from Flask!
```
````

```python
[label app.py]
[secondary_label Output]
Hello from Flask!
```

## Environments

Tint the whole code block with a color using `[environment NAME]` inside the fence. This helps distinguish code blocks for different server environments:

````
```
[environment local]
ssh user@local-server
```
````

```
[environment local]
ssh user@local-server
```

````
```
[environment second]
ssh user@staging-server
```
````

```
[environment second]
ssh user@staging-server
```

````
```
[environment third]
ssh user@production-server
```
````

```
[environment third]
ssh user@production-server
```

## Line Prefixes

Prefix flags go in the info string (after the backticks). They wrap each code line in `<ol><li>` with a `data-prefix` attribute.

### Line Numbers

````
```line_numbers,python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello!"
```
````

```line_numbers,python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello!"
```

### Command Prefix (`$`)

Implicitly sets the language to bash:

````
```command
sudo apt update
sudo apt install nginx
```
````

```command
sudo apt update
sudo apt install nginx
```

### Super User Prefix (`#`)

Implicitly sets the language to bash:

````
```super_user
systemctl restart nginx
```
````

```super_user
systemctl restart nginx
```

### Custom Prefix

Implicitly sets the language to bash. Use `\s` for spaces:

````
```custom_prefix(mysql>)
SELECT * FROM users;
SHOW TABLES;
```
````

```custom_prefix(mysql>)
SELECT * FROM users;
SHOW TABLES;
```


### Flags Beside Highlighter Attributes

The flags and the language are the part of the info string before its first space or `{`, comma-separated.
Whatever follows passes to the highlighter untouched, so a flag works beside `hl_lines`, `title`, or Hugo's brace form.
A comma inside an attribute value is not a separator.
`mw pre` writes the fence with its attributes after the language: `command title="deploy.sh"` becomes `bash title="deploy.sh"`.
With no language left (`line_numbers hl_lines="1"`), `mw pre` writes `text` before the attribute, so a renderer does not take the attribute as the language.

````
```command title="deploy.sh"
sudo apt update
sudo apt install nginx
```
````

```command title="deploy.sh"
sudo apt update
sudo apt install nginx
```

Under Hugo, `command {hl_lines=[1]}` keeps both the prefix and Chroma's highlighting.

## HTML Contract

A label is a `<div class="code-label">` before the highlighted block, and a secondary label is a `<div class="secondary-code-label">` inside its `<code>` element:

```html
<div class="code-label" title="app.py">app.py</div>

<div class="language-python highlight"><pre><span></span><code><div class="secondary-code-label" title="Output">Output</div>...</code></pre></div>
```

An environment and a line prefix add classes to the `<pre>` and wrap each line in an `<ol><li data-prefix="...">`:

```html
<div class="code-label" title="deploy.sh">deploy.sh</div>

<div class="language-bash highlight"><pre class="prefixed command environment-local"><span></span><code><ol><li data-prefix="$">ls
</li></ol>
</code></pre></div>
```

The `<pre>` class is `prefixed` plus the prefix type (`line_numbers`, `command`, `super_user`, or `custom_prefix`), and `environment-NAME` when an environment is set.
`data-prefix` is `$`, `#`, the custom text, or the line number.

## Host CSS and Script

markwright ships no CSS, JavaScript, or icons.
The fence extension emits these hooks:

| Hook | Where | Role |
|------|-------|------|
| `div.code-label` | Before the block | The label chip, with a `title`. The class is the `label_class` option's default. |
| `div.secondary-code-label` | Inside the `<code>` | The secondary label. The class is the `secondary_label_class` option's default. |
| `pre.environment-NAME` | On the `<pre>` | The environment tint, where `NAME` is the sanitized `[environment NAME]` value. |
| `pre.prefixed <type>` | On the `<pre>` | A line-prefixed block, where `<type>` is `line_numbers`, `command`, `super_user`, or `custom_prefix`. |
| `<ol><li data-prefix="...">` | Inside the `<code>` | One list item per line, each carrying its prefix string. |

No host script is involved; the block works as plain highlighted code, and the hooks only change how it looks.
This site draws the label chips, tints the five demo environments, and renders each line's `data-prefix` through a CSS `::before` in [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css), under the `.code-label`, `pre.environment-*`, and `pre.prefixed` rules.
A host that renames the label classes through the options styles its own names instead.
