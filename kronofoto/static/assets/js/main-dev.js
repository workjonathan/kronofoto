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
  initJQuery,
  HTMX
}
  from "./lib.js"

window.toggleLogin = toggleLogin
const htmx = window.htmx = HTMX(document)
window.kfcontext = document
window.kfcontext.htmx = htmx

const init = () => {

  initJQuery(document.querySelector('#kfroot'))
  initHTMXListeners(document, $('body'))
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
