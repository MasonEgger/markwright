# Fence

Adds labels, secondary labels, environment classes, and line prefixes to fenced code blocks. All fence features are coordinated through a single extension to avoid ordering issues.

## Configuration

```yaml
markdown_extensions:
  - do_markdown.fence:
      allowed_environments:
        - local
        - second
        - third
        - fourth
        - fifth
```

| Option | Default | Description |
|--------|---------|-------------|
| `allowed_environments` | `[]` (allow all) | List of allowed environment names. If empty, all names are accepted. |

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

## Full Combination

All features can be combined:

````
```command
[environment local]
[label server.sh]
ssh root@192.168.1.1
apt update && apt upgrade -y
```
````

```command
[environment local]
[label server.sh]
ssh root@192.168.1.1
apt update && apt upgrade -y
```
