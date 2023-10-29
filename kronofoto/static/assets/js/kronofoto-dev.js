import {
  installButtons,
  markerDnD,
  initJQuery,
  initHTMXListeners,
  initEventHandlers,
  initGalleryNav,
  initFoundation,
  initNavSearch,
  initClipboardJS,
  initAutocomplete, initPopups, initDraggableThumbnails, initTimeline
} from "./lib.js"

import HTMX from "./htmx.js"


class FortepanViewer extends HTMLElement {
    constructor() {
        super()
        this.shadow = this.attachShadow({mode: "open"})
    }
    connectedCallback() {
        const constraint = this.getAttribute("constraint")
        const host = this.getAttribute("src") || "https://fortepan.us"
        const template = document.createElement("template")
        const body = document.querySelector("body")
        const f = document.createElement("style")
        f.innerHTML = `
/* cyrillic-ext */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 300;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTURjIg1_i6t8kCHKm45_cJD3gTD_u50.woff2) format('woff2');
  unicode-range: U+0460-052F, U+1C80-1C88, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F;
}
/* cyrillic */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 300;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTURjIg1_i6t8kCHKm45_cJD3g3D_u50.woff2) format('woff2');
  unicode-range: U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116;
}
/* vietnamese */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 300;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTURjIg1_i6t8kCHKm45_cJD3gbD_u50.woff2) format('woff2');
  unicode-range: U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+1EA0-1EF9, U+20AB;
}
/* latin-ext */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 300;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTURjIg1_i6t8kCHKm45_cJD3gfD_u50.woff2) format('woff2');
  unicode-range: U+0100-024F, U+0259, U+1E00-1EFF, U+2020, U+20A0-20AB, U+20AD-20CF, U+2113, U+2C60-2C7F, U+A720-A7FF;
}
/* latin */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 300;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTURjIg1_i6t8kCHKm45_cJD3gnD_g.woff2) format('woff2');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
/* cyrillic-ext */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 400;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTUSjIg1_i6t8kCHKm459WRhyzbi.woff2) format('woff2');
  unicode-range: U+0460-052F, U+1C80-1C88, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F;
}
/* cyrillic */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 400;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTUSjIg1_i6t8kCHKm459W1hyzbi.woff2) format('woff2');
  unicode-range: U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116;
}
/* vietnamese */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 400;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTUSjIg1_i6t8kCHKm459WZhyzbi.woff2) format('woff2');
  unicode-range: U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+1EA0-1EF9, U+20AB;
}
/* latin-ext */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 400;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTUSjIg1_i6t8kCHKm459Wdhyzbi.woff2) format('woff2');
  unicode-range: U+0100-024F, U+0259, U+1E00-1EFF, U+2020, U+20A0-20AB, U+20AD-20CF, U+2113, U+2C60-2C7F, U+A720-A7FF;
}
/* latin */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 400;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTUSjIg1_i6t8kCHKm459Wlhyw.woff2) format('woff2');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
/* cyrillic-ext */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 500;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTURjIg1_i6t8kCHKm45_ZpC3gTD_u50.woff2) format('woff2');
  unicode-range: U+0460-052F, U+1C80-1C88, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F;
}
/* cyrillic */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 500;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTURjIg1_i6t8kCHKm45_ZpC3g3D_u50.woff2) format('woff2');
  unicode-range: U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116;
}
/* vietnamese */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 500;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTURjIg1_i6t8kCHKm45_ZpC3gbD_u50.woff2) format('woff2');
  unicode-range: U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+1EA0-1EF9, U+20AB;
}
/* latin-ext */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 500;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTURjIg1_i6t8kCHKm45_ZpC3gfD_u50.woff2) format('woff2');
  unicode-range: U+0100-024F, U+0259, U+1E00-1EFF, U+2020, U+20A0-20AB, U+20AD-20CF, U+2113, U+2C60-2C7F, U+A720-A7FF;
}
/* latin */
@font-face {
  font-family: 'Montserrat';
  font-style: normal;
  font-weight: 500;
  src: url(https://fonts.gstatic.com/s/montserrat/v18/JTURjIg1_i6t8kCHKm45_ZpC3gnD_g.woff2) format('woff2');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
/* Font Awesome */
@font-face{
    font-family:"Font Awesome 5 Brands";
    font-style:normal;
    font-weight:400;
    font-display:block;
    src:url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-brands-400.eot);
    src:url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-brands-400.eot?#iefix) format("embedded-opentype"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-brands-400.woff2) format("woff2"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-brands-400.woff) format("woff"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-brands-400.ttf) format("truetype"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-brands-400.svg#fontawesome) format("svg")
}
.fab{
    font-family:"Font Awesome 5 Brands"
}
@font-face{
    font-family:"Font Awesome 5 Free";
    font-style:normal;
    font-weight:400;
    font-display:block;
    src:url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-regular-400.eot);
    src:url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-regular-400.eot?#iefix) format("embedded-opentype"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-regular-400.woff2) format("woff2"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-regular-400.woff) format("woff"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-regular-400.ttf) format("truetype"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-regular-400.svg#fontawesome) format("svg")
}
.fab,.far{
    font-weight:400
}
@font-face{
    font-family:"Font Awesome 5 Free";
    font-style:normal;
    font-weight:900;
    font-display:block;
    src:url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-solid-900.eot);
    src:url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-solid-900.eot?#iefix) format("embedded-opentype"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-solid-900.woff2) format("woff2"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-solid-900.woff) format("woff"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-solid-900.ttf) format("truetype"),url(//cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/webfonts/fa-solid-900.svg#fontawesome) format("svg")
}

`
        body.appendChild(f)
        const mode = 'cors'
        const headers = new Headers([['Embedded', '1'], ["Constraint", constraint]])
        const req = new Request(host, {mode, headers})
        initJQuery(this.shadowRoot)
        initFoundation(this.shadowRoot)
        fetch(req)
            .then(response => response.text())
            .then(response => {
                this.shadowRoot.innerHTML = response
                this.htmx = HTMX(this.shadowRoot)
                this.htmx.process(this.shadowRoot.querySelector("#kfroot"))
                //this.htmx.logAll()
                initHTMXListeners(this.htmx, this.shadowRoot)
            })
    }
}
customElements.define("fortepan-viewer", FortepanViewer)
