# Demo

A demonstration of all do-markdown extensions on a single page.

## Highlight

Inline highlight: This has a <^>highlighted word<^> in it.

In inline code: Check `config.<^>timeout<^>` for the setting.

In a code block:

```python
def process(data):
    result = <^>transform(data)<^>
    return result
```

## Fence: Labels

```python
[label app.py]
from flask import Flask

app = Flask(__name__)
```

## Fence: Secondary Labels

```
[secondary_label Output]
Server started on port 8080
```

## Fence: Environments

```
[environment local]
[label local-server.sh]
ssh user@localhost
```

```
[environment second]
[label staging-server.sh]
ssh deploy@staging.example.com
```

```
[environment third]
[label production-server.sh]
ssh deploy@prod.example.com
```

## Fence: Line Numbers

```line_numbers,python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello, World!"
```

## Fence: Command Prefix

```command
sudo apt update
sudo apt install nginx
systemctl start nginx
```

## Fence: Super User Prefix

```super_user
systemctl restart nginx
journalctl -u nginx -f
```

## Fence: Custom Prefix

```custom_prefix(mysql>)
SELECT * FROM users;
SHOW DATABASES;
USE production;
```

## Fence: Full Combination

```command
[environment local]
[label deploy.sh]
ssh root@192.168.1.1
apt update && apt upgrade -y
systemctl restart nginx
```

## YouTube

[youtube dQw4w9WgXcQ]

## CodePen

[codepen MattCowley vwPzeX dark css 300]

## Twitter

[twitter https://twitter.com/github/status/1234567890]

## Instagram

[instagram https://www.instagram.com/p/CkQuv3_LRgS caption]

## Slideshow

[slideshow https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270 https://picsum.photos/id/30/480/270]

## Image Compare

[compare https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270]
