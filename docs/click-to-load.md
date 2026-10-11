# Click-to-Load

The YouTube, CodePen, Twitter, and Instagram embeds contact a third party.
With the default `load = "eager"`, that happens on page load: the provider sets cookies, a strict Content-Security-Policy blocks it, and an offline reader sees empty boxes.

`load = "click"` replaces the live embed with an inert preview.
The live markup still ships in the page, inside a `<template>`, which browsers parse but never render or fetch from.
Nothing reaches the provider until a reader clicks the button and a host script swaps the live markup in.

markwright ships no JavaScript and no CSS.
It owns the markup; your site owns the behavior and the styling.
This page is the contract a host script codes against.

## Turning It On

Set `load` per embed in `markwright.toml` (or `[tool.markwright]`, or a host tool's own config through `config_from_mapping`):

```toml
[youtube]
load = "click"

[twitter]
load = "click"
```

In-process, pass it through `extension_configs`:

```python
md = markdown.Markdown(
    extensions=["markwright.youtube"],
    extension_configs={"markwright.youtube": {"load": "click"}},
)
```

YouTube also takes `load = "lazy"`, which keeps the live iframe and adds the browser-native `loading="lazy"`.
The script embeds take only `eager` and `click`, since deferring a script embed needs host JavaScript either way, and `click` already covers that.

## The Preview Markup (Version 1)

A `[twitter MattIPv4/status/1576415168426573825]` line with `load = "click"` renders to:

```html
<div class="mw-embed" data-mw-version="1" data-mw-embed="twitter" data-mw-load="click" data-mw-script="https://platform.twitter.com/widgets.js">
    <template class="mw-embed-content"><div class="twitter">
    <blockquote class="twitter-tweet" data-dnt="true" data-width="550" data-theme="light">
        <a href="https://twitter.com/MattIPv4/status/1576415168426573825">View tweet by @MattIPv4</a>
    </blockquote>
</div></template>
    <div class="mw-embed-preview">
        <p class="mw-embed-provider">X (Twitter) post</p>
        <button type="button" class="mw-embed-load">Load post</button>
        <a class="mw-embed-link" href="https://twitter.com/MattIPv4/status/1576415168426573825">View on X</a>
    </div>
</div>
```

The `<template>` holds the exact `eager` markup, minus the provider `<script>` tag.

### Hooks

| Hook | Meaning |
|------|---------|
| `.mw-embed` | The wrapper; replace it with the live markup on load. |
| `data-mw-version` | The contract version, `1` today. |
| `data-mw-embed` | The extension name: `youtube`, `codepen`, `twitter`, or `instagram`. |
| `data-mw-load` | The load mode, `click`. |
| `data-mw-script` | The provider script to inject after cloning. Absent for YouTube, whose iframe needs no script. |
| `template.mw-embed-content` | The live markup. |
| `.mw-embed-preview` | The visible placeholder; style it however your site likes. |
| `.mw-embed-provider` | Text naming what the embed is. |
| `button.mw-embed-load` | The load button. |
| `a.mw-embed-link` | A direct link to the original, so the content stays reachable with JavaScript off and in feed readers. |

### Preview Text

| Embed | Provider text | Button | Link |
|-------|---------------|--------|------|
| `youtube` | YouTube video | Load video | Watch on YouTube |
| `codepen` | CodePen | Load pen | View on CodePen |
| `twitter` | X (Twitter) post | Load post | View on X |
| `instagram` | Instagram post | Load post | View on Instagram |

The text is fixed English.
A site that translates it rewrites the text through the hooks above.

### Script Injection

On an `eager` page, markwright appends each provider's `<script>` once.
It skips the script when every embed of that kind on the page is a preview, and still appends it once when the page mixes eager and click embeds.
The decision comes from the HTML alone, so `mw post` and the in-process render agree.

### Provider Processors

After cloning the live markup into the page, a host has to make the provider render it:

| Embed | After the script loads |
|-------|------------------------|
| `twitter` | `window.twttr.widgets.load(element)` |
| `instagram` | `window.instgrm.Embeds.process()` |
| `codepen` | `ei.js` scans the page when it first loads; for later embeds, call `window.__CPEmbed()` |
| `youtube` | Nothing; the iframe loads itself. |

### Versioning Policy

`data-mw-version` changes only for a breaking change to the markup above (a renamed hook, a moved element).
Adding a hook or an attribute keeps the version.

## A Host Script

This is a starting point, not package data: copy it into your site and adjust it.

```html
<script>
document.addEventListener("click", (event) => {
  const button = event.target.closest(".mw-embed-load");
  if (!button) return;
  const wrapper = button.closest(".mw-embed");
  const live = document.createElement("div");
  live.className = "mw-embed-live";
  live.append(wrapper.querySelector("template.mw-embed-content").content.cloneNode(true));
  wrapper.replaceWith(live);

  const scriptSrc = wrapper.dataset.mwScript;
  if (!scriptSrc) return;
  const process = () => {
    const embed = wrapper.dataset.mwEmbed;
    if (embed === "twitter") window.twttr?.widgets?.load(live);
    if (embed === "instagram") window.instgrm?.Embeds?.process();
    if (embed === "codepen") window.__CPEmbed?.();
  };
  if (document.querySelector(`script[src="${scriptSrc}"]`)) {
    process();
    return;
  }
  const script = document.createElement("script");
  script.src = scriptSrc;
  script.async = true;
  script.onload = process;
  document.body.append(script);
});
</script>
```

One listener on `document` handles every preview on the page, including ones added later.
The script loads each provider at most once; a second click on the same kind of embed reuses it.
