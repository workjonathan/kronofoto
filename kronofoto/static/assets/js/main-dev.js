import { FortepanInstance }
  from "./lib.js"

// window.toggleLogin = toggleLogin
// const htmx = window.htmx = HTMX(document)
// window.kfcontext = document
// window.kfcontext.htmx = htmx

const init = () => {
  let fi = new FortepanInstance(document)
  fi.init()
}

const ready = fn => {
  if (document.readyState !== "loading") {
    fn()
  } else {
    document.addEventListener("DOMContentLoaded", fn)
  }
}

ready(init)
