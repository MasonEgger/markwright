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

All three options apply the same way in-process, through `mw render`, and through the `mw pre | renderer | mw post` pipeline.

Directives work in any fenced code block CommonMark recognizes, including a fence indented up to three spaces or one nested inside a list item.
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
