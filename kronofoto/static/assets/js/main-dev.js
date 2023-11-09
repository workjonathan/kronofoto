import {
  toggleLogin,
  installButtons,
  initGalleryNav,
  initNavSearch,
  initPopups,
  initEventHandlers,
  initDraggableThumbnails,
  initAutocomplete,
  initClipboardJS,
  initFoundation,
  initHTMXListeners,
}
  from "./lib.js"
window.kfcontext = document
import HTMX from "./htmx.js"

const htmx = HTMX(document)

const init = () => {
  initHTMXListeners(htmx, document)
  initFoundation(document)
  initClipboardJS(document)
}

const ready = fn => {
  if (document.readyState !== "loading") {
    fn()
  } else {
    document.addEventListener("DOMContentLoaded", fn)
  }
}

ready(init)
