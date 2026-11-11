# Highlight

Converts `\<^>text\<^>` to `<mark>text</mark>`.
Works in regular text, inline code, and fenced code blocks, anywhere that `pymdownx.mark` (`==text==`) cannot reach.

Set `config.<^>timeout<^>` to <^>30 seconds<^> before you deploy:

```python
config.timeout = <^>30<^>
```

````
[label Markdown]
Set `config.\<^>timeout\<^>` to \<^>30 seconds\<^> before you deploy:

```python
config.timeout = \<^>30\<^>
```
````

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.highlight"])
html = md.convert("This has a \<^>highlighted word\<^> in it.")
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Syntax

Wrap text in `<^>` delimiters:

```
This has a \<^>highlighted word\<^> in it.
```

Result: This has a <^>highlighted word<^> in it.

## In Inline Code

```
Check the `config.\<^>timeout\<^>` value.
```

Result: Check the `config.<^>timeout<^>` value.

## In Fenced Code Blocks

````
```python
def greet(name):
    print(f"Hello, \<^>{name}\<^>!")
```
````

Result:

```python
def greet(name):
    print(f"Hello, <^>{name}<^>!")
```

## Multiple Highlights

Multiple highlights work on the same line:

```
Both \<^>first\<^> and \<^>second\<^> are highlighted.
```

Result: Both <^>first<^> and <^>second<^> are highlighted.

## Escaping

Prefix a marker with a backslash (`\<^>`) to show it literally instead of applying a highlight.
This works consistently in regular text, inline code, and fenced code blocks, and produces the same literal marker whether you render in-process or through the `mw pre | post` pipeline.
This is how the code samples above print the raw `<^>` syntax.

## Host CSS and Script

markwright ships no CSS, JavaScript, or icons.
The only hook is the `<mark>` element, which browsers already draw with a default highlight, so highlights show with no host code.
This site restyles `<mark>` to match mkdocs-material, both in prose and inside a syntax-highlighted block, under the `.md-typeset mark` and `.md-typeset .highlight mark` rules in [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css).
A host that wants a different highlight color overrides those rules; no script is needed.
