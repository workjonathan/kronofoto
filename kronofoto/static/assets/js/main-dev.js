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
} from "./lib.js"
import AlpineJS from "alpinejs"
import resize from "@alpinejs/resize"
AlpineJS.plugin(resize)
window.AlpineJS = AlpineJS
window.kfcontext = document
import HTMX from "./htmx.js"

const htmx = HTMX(document)
htmx.config.historyCacheSize = 0
htmx.config.refreshOnHistoryMiss = true

const init = () => {
    initHTMXListeners(htmx, document)
    AlpineJS.start()
    initFoundation(document)
    initClipboardJS(document)
    document.addEventListener("htmx-process", (evt) => {
        htmx.process(evt.target)
    })
    document.addEventListener("htmx:afterSwap", (evt) => {
        AlpineJS.initTree(event.detail.target)
    })
}

const ready = (fn) => {
    if (document.readyState !== "loading") {
        fn()
    } else {
        document.addEventListener("DOMContentLoaded", fn)
    }
}

ready(init)
