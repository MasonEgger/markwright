// Opens a <dialog> with the full image when an a.mw-lightbox link is clicked.
// markwright ships no JavaScript; this script is host code for the docs site.
(function () {
  var dialog = null;
  var image = null;

  function ensureDialog() {
    if (dialog) {
      return;
    }
    dialog = document.createElement("dialog");
    dialog.className = "mw-lightbox-dialog";
    image = document.createElement("img");
    dialog.appendChild(image);
    dialog.addEventListener("click", function () {
      dialog.close();
    });
    document.body.appendChild(dialog);
  }

  document.addEventListener("click", function (event) {
    var link = event.target.closest("a.mw-lightbox");
    if (!link || typeof HTMLDialogElement === "undefined") {
      return;
    }
    event.preventDefault();
    ensureDialog();
    var thumbnail = link.querySelector("img");
    image.src = link.getAttribute("href");
    image.alt = thumbnail ? thumbnail.getAttribute("alt") || "" : "";
    dialog.showModal();
  });
})();
