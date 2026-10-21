// Shows an annotation's list item as a tooltip when its a.mw-annotation marker is hovered or focused.
// Without this script the marker stays a plain link to the list item.
// markwright ships no JavaScript; this script is host code for the docs site.
(function () {
  var tooltip = null;

  function ensureTooltip() {
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.className = "mw-annotation-tooltip";
      tooltip.setAttribute("role", "tooltip");
      tooltip.hidden = true;
      document.body.appendChild(tooltip);
    }
    return tooltip;
  }

  function show(marker) {
    var item = document.getElementById((marker.getAttribute("href") || "").slice(1));
    if (!item) {
      return;
    }
    var box = ensureTooltip();
    box.innerHTML = item.innerHTML;
    box.hidden = false;
    var rect = marker.getBoundingClientRect();
    box.style.left = Math.max(8, rect.left + window.scrollX) + "px";
    box.style.top = rect.bottom + window.scrollY + 6 + "px";
  }

  function hide() {
    if (tooltip) {
      tooltip.hidden = true;
    }
  }

  function markerFrom(event) {
    return event.target.closest ? event.target.closest("a.mw-annotation") : null;
  }

  document.addEventListener("mouseover", function (event) {
    var marker = markerFrom(event);
    if (marker) {
      show(marker);
    }
  });
  document.addEventListener("mouseout", function (event) {
    if (markerFrom(event)) {
      hide();
    }
  });
  document.addEventListener("focusin", function (event) {
    var marker = markerFrom(event);
    if (marker) {
      show(marker);
    }
  });
  document.addEventListener("focusout", function (event) {
    if (markerFrom(event)) {
      hide();
    }
  });
})();
