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
    document.addEventListener("kronofoto-set-route-name", (evt) => {
        document.documentElement.setAttribute("route", evt.detail.value)
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
