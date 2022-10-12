const themes = [
    { 
        color: "#6c84bd",
        logo: "assets/images/skyblue/logo.svg",
        menuSvg: "assets/images/skyblue/menu.svg",
        infoSvg: "assets/images/skyblue/info.svg",
        downloadSvg: "assets/images/skyblue/download.svg",
        searchSvg: "assets/images/skyblue/search.svg",
        carrotSvg: "assets/images/skyblue/carrot.svg",
        timelineSvg: 'assets/images/skyblue/toggle.svg'
    },
    {
        color: "#c28800",
        logo: "assets/images/golden/logo.svg",
        menuSvg: "assets/images/golden/menu.svg",
        infoSvg: "assets/images/golden/info.svg",
        downloadSvg: "assets/images/golden/download.svg",
        searchSvg: "assets/images/golden/search.svg",
        carrotSvg: "assets/images/golden/carrot.svg",
        timelineSvg: 'assets/images/golden/toggle.svg'
    },
    {
        color: "#c2a55e",
        logo: "assets/images/haybail/logo.svg",
        menuSvg: "assets/images/haybail/menu.svg",
        infoSvg: "assets/images/haybail/info.svg",
        downloadSvg: "assets/images/haybail/download.svg",
        searchSvg: "assets/images/haybail/search.svg",
        carrotSvg: "assets/images/haybail/carrot.svg",
        timelineSvg: 'assets/images/haybail/toggle.svg'
    },
    {
        color: "#445170",
        logo: "assets/images/navy/logo.svg",
        menuSvg: "assets/images/navy/menu.svg",
        infoSvg: "assets/images/navy/info.svg",
        downloadSvg: "assets/images/navy/download.svg",
        searchSvg: "assets/images/navy/search.svg",
        carrotSvg: "assets/images/navy/carrot.svg",
        timelineSvg: 'assets/images/navy/toggle.svg'
    }
]
class FortepanBase {
    constructor(element, initialState, {scrollSpeed=4, urlUpdater=undefined, root=document}={}) {
        this.elem = element
        this.root = root
        this.urlUpdater = urlUpdater || new URLUpdater(new Map())
        this.randomTheme = themes[Math.floor(Math.random()*themes.length)]
        this.scrollSpeed = scrollSpeed
        this.initializeWindowState(initialState)
        this.loadFrame(initialState)
        const _this = this
        this.root.addEventListener('click', function(e) {
            const jsonhref = e.target.getAttribute('data-json-href') || e.target.parentNode.getAttribute('data-json-href')
            const scrolltarget = e.target.getAttribute('data-json-scroll')
            if (jsonhref) {
                e.preventDefault()
                if (jsonhref !== "#") {
                    const updatedhref = _this.urlUpdater.update(jsonhref)
                    const id = e.target.parentNode.getAttribute('id')
                    if (id !== 'forward' && id !== 'backward') {
                        request('GET', updatedhref).then(data => {
                            _this.loadstate(data)
                            _this.pushWindowState(data)
                            if (scrolltarget) {
                                _this.elem.querySelector(`#${scrolltarget}`).scrollIntoView(true)
                            }
                        })
                    }
                }
            }
        })
    }
    toggleVis(evt) {
        const el = this.elem.querySelector('#metadata')
        toggleElement(el);
    }
    moveMarker(year) {
        const marker = this.elem.querySelector('.active-year-marker');
        const markerYearElement = this.elem.querySelector('.marker-year');

        // Update year text
        markerYearElement.textContent = year;

        // Show Marker (might not be necessary to do this display stuff)
        marker.style.display = 'block';

        // move marker to position of tick
        let embedmargin = this.elem.querySelector('.year-ticker').getBoundingClientRect().left;
        let tick = this.elem.querySelector(`.year-ticker svg a rect[data-year="${year}"]`);
        let bounds = tick.getBoundingClientRect();
        let markerStyle = window.getComputedStyle(marker);
        let markerWidth = markerStyle.getPropertyValue('width').replace('px', ''); // trim off px for math
        let offset = (bounds.x - (markerWidth / 2) - embedmargin); // calculate marker width offset for centering on tick
        marker.style.transform = `translateX(${offset}px)`;
    }
    loadFrame(initialState) {
        this.carousel = undefined
        this.currentState = initialState
        this.forward = undefined
        this.backward = undefined
        if (initialState.type === 'GRID') {
            this.elem.innerHTML = initialState.frame
            this.root.querySelector('.timeline-container').classList.remove('current-view')
            this.root.querySelector('.grid-icon').classList.add('current-view')
            this.root.querySelector('.timeline-icon').style.opacity = '0.5'
            this.root.querySelector('.grid-icon_reg').style.opacity = '1.0'
            for (let el of this.root.querySelectorAll('.collection-name')) {
                el.style.display = 'none'
            }
        }
        else if (initialState.type === 'TIMELINE') {
            this.elem.innerHTML = initialState.frame
            this.root.querySelector('.grid-icon').classList.remove('current-view')
            this.root.querySelector('.timeline-container').classList.add('current-view')
            this.root.querySelector('.grid-icon_reg').style.opacity = '0.5'
            this.root.querySelector('.timeline-icon').style.opacity = '1.0'
            for (let el of this.root.querySelectorAll('.collection-name')) {
                el.style.display = 'block'
            }
            this.carousel = this.elem.querySelector('#fi-thumbnail-carousel-images')
            this.carousel.innerHTML = this.currentState.thumbnails
            this.forward = this.elem.querySelector('#forward')
            this.backward = this.elem.querySelector('#backward')
            this.elem.querySelector('#metadata').innerHTML = initialState.metadata
            this.moveMarker(initialState.year)
            this.elem.querySelector("#expand").addEventListener("click", evt => {
                this.toggleVis()
            })
            this.forward.addEventListener("mousedown", () =>
                this.forward.getAttribute('href') != '#' ? 
                    Promise.race([
                        mouseUp(this.forward).then(() => ({event: 'click', position: -100})),
                        delay(500).then(() => ({event: 'startScroll', begin: new Date()}))
                    ]).then(scrollAction(this.forward, this, 'forward', -200, this.root)) : undefined)

            this.backward.addEventListener("mousedown", () =>
                this.backward.getAttribute('href') != '#' ? 
                Promise.race([
                    mouseUp(this.backward).then(() => ({event: 'click', position: -100})),
                    delay(500).then(() => ({event: 'startScroll', begin: new Date()}))
                ]).then(scrollAction(this.backward, this, 'backward', 0, this.root)) : undefined)
        }
        this.root.querySelector('#fi-timeline-a').setAttribute('href', initialState.timeline_url)
        this.root.querySelector('#fi-timeline-a').setAttribute('data-json-href', initialState.timeline_json_url)
        this.root.querySelector('#grid-a').setAttribute('href', initialState.grid_url)
        this.root.querySelector('#grid-a').setAttribute('data-json-href', initialState.grid_json_url)
        applyTheme(initialState.static_url, this.randomTheme, {root: this.root})
    }
    loadstate(data) {
        if (data.type === 'TIMELINE' && this.currentState.type === 'TIMELINE') {
            this.currentState = data
            this.carousel.innerHTML = data.thumbnails
            this.carousel.setAttribute('style', 'animation: none; animation-fill-mode: none;')
            this.elem.querySelector('#metadata').innerHTML = data.metadata
            this.elem.querySelector('.fi-image figure img').setAttribute('src', data.h700)
            this.elem.querySelector('.fi-image figure img').setAttribute('alt', data.tags)
            this.elem.querySelector('#fi-arrow-left').setAttribute('href', data.previous.url)
            this.elem.querySelector('#fi-arrow-left').setAttribute('data-json-href', data.previous.json_url)
            this.elem.querySelector('#fi-arrow-right').setAttribute('href', data.next.url)
            this.elem.querySelector('#fi-arrow-right').setAttribute('data-json-href', data.next.json_url)
            this.forward.setAttribute('href', data.forward && data.forward.url ? data.forward.url : "#")
            this.forward.setAttribute('data-json-href', data.forward ? data.forward.json_url : "#")
            this.backward.setAttribute('href', data.backward && data.backward.url ? data.backward.url : "#")
            this.backward.setAttribute('data-json-href', data.backward && data.backward.json_url ? data.backward.json_url : "#")
            this.root.querySelector('#grid-a').setAttribute('href', data.grid_url)
            this.root.querySelector('#grid-a').setAttribute('data-json-href', data.grid_json_url)
            this.elem.querySelector('#dl > a').setAttribute('href', data.original)
            for (let a of this.elem.querySelectorAll('#app a.fpi-fpilink')) {
                a.setAttribute('href', data.url)
            }
            this.moveMarker(data.year)
        }
        else {
            this.forward = this.elem.querySelector('#forward')
            this.backward = this.elem.querySelector('#backward')
            this.loadFrame(data)
        }
    }
}

class FortepanApp extends FortepanBase {
    initializeWindowState(initialState) {
        window.history.replaceState(initialState, 'Fortepan Iowa', initialState.url)
        window.onpopstate = evt => {
            if (evt.state) {
                this.loadstate(evt.state)
            }
        }
    }
    pushWindowState(data) {
        window.history.pushState(data, 'Fortepan Iowa', data.url)
    }
}

class FortepanWidget extends FortepanBase {
    initializeWindowState(initialState) {
    }
    pushWindowState(data) {
    }
}

class FortepanViewer extends HTMLElement {
    constructor() {
        super()
        const shadow = this.attachShadow({mode: "open"})
    }
    connectedCallback() {
        const constraint = this.getAttribute("constraint")
        const host = this.getAttribute("host") || "https://fortepan.us"
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
`
        body.appendChild(f)
        template.innerHTML = `
            <style>
            @import "${host}/app.css";
* {
    --fp-main-font: 'Montserrat', sans-serif;
    --fp-secondary-ticker-color: #9d9d9c;
    --fp-main-grey: #d6d6da;
    --fp-main-grey-translucent: rgba(214, 214, 218, 0.95);
    --fp-light-grey: #efeff1;
    --fp-light-grey-translucent: rgba(239, 239, 241, 0.9);
    --fp-main-blue: #c2a55e;
}
            </style>
            <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>
            <link rel="stylesheet" href="//code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.14.0/css/all.min.css">
            <script
			  src="https://code.jquery.com/jquery-3.5.1.min.js"
			  integrity="sha256-9/aliU8dGd2tb6OSsuzixeV4y/faTqgFtohetphbbj0="
			  crossorigin="anonymous"></script>
            <div id="app"></div>
		`

        const doc = template.content.cloneNode(true)
        this.shadowRoot.appendChild(doc)
        initialize_fortepan(this.shadowRoot.querySelector("#app"), {host, constraint, root: this.shadowRoot})
    }
}
customElements.define("fortepan-viewer", FortepanViewer)

class URLUpdater {
    constructor(constraints) {
        this.constraints = constraints
    }
    update(href) {
        const url = new URL(href)
        this.updateParameters(url.searchParams)
        return url.toString()
    }
    updateParameters(params) {
        for (let [key, value] of this.constraints) {
            if (!params.has(key)) {
                params.append(key, value)
            }
        }
    }
}

const initialize_fortepan = (element, {constraint=undefined, host="https://fortepan.us", root=document}={}) => {
    const m = new Map()
    if (constraint) {
        m.set('constraint', constraint)
    }
    m.set('embed', 1)
    const updater = new URLUpdater(m)
    const req = new Request(updater.update(`${host}/search.json`), {mode:'cors'})
    fetch(req)
        .then(response => response.json())
        .then(response => {
            const app = new FortepanWidget(element, response, {urlUpdater:updater, root})
        })
}

const scrollSpeed = 4 // seconds to scroll through one set of 10 images
const toggleLogin = evt => {
    const el = document.querySelector('#login');
    toggleElement(el);
}
const toggleMenu = evt => {
    const el = document.querySelector('.hamburger-menu')
    toggleElement(el)
    toggleHover()
}
const toggleElement = el => {
    if (!el.classList.replace('hidden', 'gridden')) {
        el.classList.replace('gridden', 'hidden')
    }
}

const delay = ms => new Promise((resolve, reject) => setTimeout(resolve, ms))

const mouseUp = element => new Promise((resolve, reject) =>
    element.addEventListener("mouseup", resolve, {once: true})
)

const animationEnd = element => new Promise((resolve, reject) =>
    element.addEventListener('animationend', resolve, {once: true})
)

const request = (verb, resource) => new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open(verb, resource)
    xhr.onload = () => {
        if (xhr.status === 200) {
            resolve(JSON.parse(xhr.responseText))
        } else {
            reject(`${verb} ${resource} returned ${xhr.status}`)
        }
    }
    xhr.send()
})




const trace = v => {
    console.log(v)
    return v
}

const scrollAction = (element, app, direction, target, root) => evt => {
    const next_page = request('GET', app.urlUpdater.update(app.currentState[direction].json_url)).then(data => {
        root.querySelector('.fi-image').setAttribute('src', data.h700)
        root.getElementById('metadata').innerHTML = data.metadata
        root.getElementById('fi-preload-zone').innerHTML = data.thumbnails
        return data
    })
    let p
    if (evt.event === 'click') {
        p = Promise.resolve(evt)
    } else if (evt.event === 'startScroll') {
        const scrollEnd = animationEnd(app.carousel)
        void app.carousel.offsetWidth
        app.carousel.setAttribute('style', `animation: from-100-to${target} ${scrollSpeed}s linear;`)

        p = Promise.race([
            mouseUp(element).then(() => ({event: 'click', position: Math.round(-10 * scrollSpeed - (new Date() - evt.begin)/(-target - scrollSpeed * 10))})),
            scrollEnd.then(() => ({event: 'startScroll', begin: new Date()})),
        ])
    }
    const scroll2end = p.then(evt => {
        if (evt.event === 'click') {
            app.carousel.setAttribute('style', `animation: from${evt.position}-to${target} 500ms ease-out; animation-fill-mode: forwards`)
            return animationEnd(app.carousel)
        }
        return evt
    })
    Promise.all([next_page, scroll2end]).then(([data, evt]) => {
        app.loadstate(data)
        app.pushWindowState(data)
        if (evt.event === 'startScroll') {
            scrollAction(element, app, direction, target, root)(evt)
        }
    })
}

//RETRACT SEARCH DROPDOWN MENU WHEN CLICKING ON BACKGROUND OF WEBSITE WHILE THE DROPDOWN IS EXTENDED
//code copied from https://www.tutorialrepublic.com/codelab.php?topic=faq&file=jquery-close-dropdown-by-clicking-outside-of-them on 6/2/21 by SS
//Only issue with the function as of 6/4 is that it will not close the menu if you click on something with the class "<empty-string>" - SS
/*Pseudo Code:

    if the menu is open and anything else except the menu is clicked:
        close the menu

    if carrot is clicked:
        toggle the menu

*/

const init = () => {
    $(document).click(function(event)
    {
        //~TESTING LINE
        //console.log(event.target.className)

        var classOfThingClickedOn = event.target.className

        //~TESTING LINE
        //console.log($('.search-form').find('*'))

        //creates a jQuery collection of the components of the search menu EXCEPT for the menu itself
        var $descendantsOfSearchForm = $('.search-form').find('*')

        //---creates an array of all components of the search menu dropdown---
        //adds the search menu itself to the array
        var componentsOfSearchMenuArray = ['search-form']

        //adds the class of all the components of the search menu to the array
        $descendantsOfSearchForm.each(function(index)
        {
            //checks to make sure the class isn't already in the array
            if($.inArray(this.className, componentsOfSearchMenuArray) == -1)
            {
                //adds the class to the array
                componentsOfSearchMenuArray.push(this.className)
            }
        })

        //~TESTING LINES
        //console.log(componentsOfSearchMenuArray)
        //console.log('Class:'+'"'+classOfThingClickedOn+'"')
        //console.log(componentsOfSearchMenuArray.includes(classOfThingClickedOn))

        //if the search menu is open and the user clicks on something outside of the menu, close the menu
        if($('.search-form').is(":visible") && (!(componentsOfSearchMenuArray.includes(classOfThingClickedOn))))
        {
            $('.search-form').toggle()
        }
        //if the user clicks on the carrot or the small invisible box behind it, toggle the menu
        else if(classOfThingClickedOn == 'search-options' || classOfThingClickedOn == 'carrot')
        {
            $('.search-form').toggle()
        }
    })


    $('#tag-search').autocomplete({
        source: '/tags/',
        minLength: 2,
    })

    $('.overlay, .close-btn').click(() => {
        $('.gridden').removeClass('gridden').addClass('hidden')
        $('.overlay').css('display', 'none')
    })


    const toggleHover = () => {
        if($('.hamburger-menu').hasClass('gridden')) {
            $('.overlay').css('display', 'block')
            /* $('.hamburger-container').css('background-color', 'var(--fp-main-blue)')
            $('.hamburger-container div img').css('filter', 'brightness(0) invert(1)') */
            /* $('.hamburger-icon').attr('src', '/static/assets/images/close.png') */
        } else {
            $('.overlay').css('display', 'none')
            /* $('.hamburger-container').css('background-color', '')
            $('.hamburger-container div img').css('filter', '') */
            /* $('.hamburger-icon').attr('src', '/static/assets/images/hamburger.svg') */
        }
    }

    $('#login-btn').click(() => {
        if($('#login').hasClass('gridden')) {
            $('.overlay').css('display', 'block')
        } else {
            $('.overlay').css('display', 'none')
        }
    })


    $('#search-box').focus(function() {
        $('#search-box-container').css('background','var(--fp-main-blue)')
        $('.search-icon').css('filter', 'brightness(0) invert(1)')
        $('.carrot').css('filter', 'brightness(0) invert(1)')
        $('#search-box').addClass('placeholder-light').css('color', 'white')

    }).blur(function() {
        $('#search-box-container').css('background','var(--fp-light-grey)')
        $('.search-icon').css('filter', 'none')
        $('.carrot').css('filter', 'none')
        $('#search-box').removeClass('placeholder-light').css('color', '#333')
        //('#search-box').css('color', 'var(--fp-light-grey)')
    });

}

const ready = fn => {
    if (document.readyState !== "loading") {
        fn()
    } else {
        document.addEventListener("DOMContentLoaded", fn)
    }
}
ready(init)

//----------changes colors of icons and --fp-main-blue css variable on page load----------


const _static = (static_url, path) => static_url + path

const applyTheme = (static_url, theme, {root=document}={}) => {
    for (const hamburger of root.querySelectorAll(".hamburger-icon")) {
        hamburger.setAttribute("src", _static(static_url, theme.menuSvg))
    }
    for (const info of root.querySelectorAll('.meta-info-icon')) {
        info.setAttribute("src", _static(static_url, theme.infoSvg))
    }
    for (const dl of root.querySelectorAll('.meta-dl-icon')) {
        dl.setAttribute("src", _static(static_url, theme.downloadSvg))
    }
    for (const search of root.querySelectorAll('.search-icon')) {
        search.setAttribute("src", _static(static_url, theme.searchSvg))
    }
    for (const carrot of root.querySelectorAll('.carrot')) {
        carrot.setAttribute("src", _static(static_url, theme.carrotSvg))
    }
    for (const timelineMarker of root.querySelectorAll('.marker-image')) {
        timelineMarker.style.backgroundImage = `url('${_static(static_url, theme.timelineSvg)}')`
    }
    for (const logoImg of root.querySelectorAll(".logo-img")) {
        logoImg.src = _static(static_url, theme.logo)
    }
    if (root.documentElement) {
        root.documentElement.style.setProperty("--fp-main-blue", theme.color)
    }
}
//----------_----------
