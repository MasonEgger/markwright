# Highlight

Converts `\<^>text\<^>` to `<mark>text</mark>`. Works in regular text, inline code, and fenced code blocks — anywhere that `pymdownx.mark` (`==text==`) cannot reach.

## Configuration

```yaml
markdown_extensions:
  - do_markdown.highlight
```

No configuration options.

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

Prefix a marker with a backslash (`\<^>`) inside code to show it literally
instead of applying a highlight — this is how the code samples above print the
raw `<^>` syntax.
