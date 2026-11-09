// Turns each markwright annotation into a Material-style tooltip: the a.mw-annotation marker opens a card
// holding its list item, and an annotation inside that card opens a second card on top, so annotations nest.
// markwright ships no JavaScript; this script is host code for the docs site. Without it, each marker is a plain
// link to its list item.
(function () {
  var CLOSE_DELAY = 250;
  var tooltipsById = {};
  var pairs = [];
  var lists = [];
  var stack = [];
  var closeTimer = null;

  function moveChildren(source, target) {
    while (source.firstChild) {
      target.appendChild(source.firstChild);
    }
  }

  // Each list item's content moves into its own tooltip, so a nested annotation list moves with it and
  // stays live inside the card. The hidden list keeps the empty items, which keep their ids.
  function setUp() {
    lists = Array.prototype.slice.call(document.querySelectorAll("ol.mw-annotations"));
    lists.forEach(function (list) {
      Array.prototype.forEach.call(list.children, function (item) {
        if (item.tagName !== "LI" || !item.id) {
          return;
        }
        var tooltip = document.createElement("div");
        tooltip.className = "mw-annotation-tooltip";
        tooltip.setAttribute("role", "tooltip");
        tooltip.id = item.id + "-tooltip";
        var inner = document.createElement("div");
        inner.className = "mw-annotation-tooltip__inner md-typeset";
        tooltip.appendChild(inner);
        moveChildren(item, inner);
        document.body.appendChild(tooltip);
        tooltipsById[item.id] = tooltip;
        pairs.push({ item: item, inner: inner });
      });
      list.hidden = true;
    });
    document.querySelectorAll("a.mw-annotation").forEach(function (marker) {
      var tooltip = tooltipsById[targetId(marker)];
      if (tooltip) {
        marker.setAttribute("aria-describedby", tooltip.id);
        marker.setAttribute("aria-expanded", "false");
      }
    });
  }

  function targetId(marker) {
    return (marker.getAttribute("href") || "").slice(1);
  }

  function depthOf(tooltip) {
    for (var index = 0; index < stack.length; index++) {
      if (stack[index].tooltip === tooltip) {
        return index;
      }
    }
    return -1;
  }

  function position(marker, tooltip) {
    var rect = marker.getBoundingClientRect();
    var gutter = 16;
    var width = tooltip.offsetWidth;
    var maxLeft = window.scrollX + document.documentElement.clientWidth - width - gutter;
    var left = Math.max(window.scrollX + gutter, Math.min(rect.left + window.scrollX - gutter, maxLeft));
    tooltip.style.left = left + "px";
    tooltip.style.top = rect.bottom + window.scrollY + 6 + "px";
  }

  function closeFrom(depth) {
    while (stack.length > depth) {
      var entry = stack.pop();
      entry.tooltip.classList.remove("mw-annotation-tooltip--active");
      entry.marker.classList.remove("mw-annotation--active");
      entry.marker.setAttribute("aria-expanded", "false");
    }
  }

  function open(marker) {
    var tooltip = tooltipsById[targetId(marker)];
    if (!tooltip) {
      return;
    }
    // A marker inside an open card stacks its card above that one; any other marker replaces the stack.
    var host = marker.closest(".mw-annotation-tooltip");
    var depth = host ? depthOf(host) + 1 : 0;
    if (stack[depth] && stack[depth].marker === marker) {
      closeFrom(depth + 1);
      return;
    }
    closeFrom(depth);
    stack.push({ marker: marker, tooltip: tooltip, pinned: false });
    tooltip.style.zIndex = String(20 + depth);
    position(marker, tooltip);
    tooltip.classList.add("mw-annotation-tooltip--active");
    marker.classList.add("mw-annotation--active");
    marker.setAttribute("aria-expanded", "true");
  }

  // How many open cards the element keeps open: it keeps every card up to the deepest one it sits in.
  function depthHolding(element) {
    for (var index = stack.length - 1; index >= 0; index--) {
      if (stack[index].tooltip.contains(element) || stack[index].marker.contains(element)) {
        return index + 1;
      }
    }
    return 0;
  }

  // Hover never closes a pinned card or the cards beneath it.
  function pinnedDepth() {
    for (var index = stack.length - 1; index >= 0; index--) {
      if (stack[index].pinned) {
        return index + 1;
      }
    }
    return 0;
  }

  function cancelClose() {
    clearTimeout(closeTimer);
    closeTimer = null;
  }

  function scheduleClose(depth) {
    cancelClose();
    closeTimer = setTimeout(function () {
      closeFrom(depth);
    }, CLOSE_DELAY);
  }

  function markerFrom(event) {
    return event.target.closest ? event.target.closest("a.mw-annotation") : null;
  }

  document.addEventListener("mouseover", function (event) {
    var marker = markerFrom(event);
    if (marker && tooltipsById[targetId(marker)]) {
      cancelClose();
      open(marker);
      return;
    }
    var depth = Math.max(depthHolding(event.target), pinnedDepth());
    if (depth < stack.length) {
      scheduleClose(depth);
    } else {
      cancelClose();
    }
  });

  // A click (or tap) pins the card open; a second click on the same marker closes it, as does a click outside
  // every open card. Hover has usually opened the card already, so the first click only pins it.
  document.addEventListener("click", function (event) {
    var marker = markerFrom(event);
    if (marker && tooltipsById[targetId(marker)]) {
      event.preventDefault();
      cancelClose();
      var depth = depthOf(tooltipsById[targetId(marker)]);
      if (depth >= 0 && stack[depth].marker === marker && stack[depth].pinned) {
        closeFrom(depth);
        return;
      }
      open(marker);
      stack[stack.length - 1].pinned = true;
      return;
    }
    if (depthHolding(event.target) === 0) {
      closeFrom(0);
    }
  });

  document.addEventListener("focusin", function (event) {
    var marker = markerFrom(event);
    if (marker && tooltipsById[targetId(marker)]) {
      cancelClose();
      open(marker);
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && stack.length) {
      var marker = stack[0].marker;
      closeFrom(0);
      marker.focus();
    }
  });

  window.addEventListener("resize", function () {
    closeFrom(0);
  });

  // Printing puts the content back in the lists, so the page prints the numbered notes.
  window.addEventListener("beforeprint", function () {
    closeFrom(0);
    pairs.forEach(function (pair) {
      moveChildren(pair.inner, pair.item);
    });
    lists.forEach(function (list) {
      list.hidden = false;
    });
  });
  window.addEventListener("afterprint", function () {
    pairs.forEach(function (pair) {
      moveChildren(pair.item, pair.inner);
    });
    lists.forEach(function (list) {
      list.hidden = true;
    });
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setUp);
  } else {
    setUp();
  }
})();
