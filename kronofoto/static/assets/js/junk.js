class FortepanApp {
    constructor(element, initialState, {scrollSpeed=4}={}) {
        this.elem = element
        this.randomTheme = themes[Math.floor(Math.random()*themes.length)]
        this.scrollSpeed = scrollSpeed
        window.history.replaceState(initialState, 'Fortepan Iowa', initialState.url)
        this.loadFrame(initialState)
        const _this = this
        document.addEventListener('click', function(e) {
            const jsonhref = e.target.getAttribute('data-json-href') || e.target.parentNode.getAttribute('data-json-href')
            if (jsonhref) {
                e.preventDefault()
                if (jsonhref !== "#") {
                    const id = e.target.getAttribute('id')
                    if (id !== 'forward' && id !== 'backward') {
                        request('GET', jsonhref).then(data => {
                            _this.loadstate(data)
                            window.history.pushState(data, 'Fortepan Iowa', data.url)
                        })
                    }
                }
            }
        })
        window.onpopstate = evt => {
            if (evt.state) {
                this.loadstate(evt.state)
            }
        }
    }
    loadFrame(initialState) {
        this.carousel = undefined
        this.currentState = initialState
        this.forward = undefined
        this.backward = undefined
        document.querySelector('#fi-timeline-a').setAttribute('href', initialState.timeline_url)
        document.querySelector('#grid-a').setAttribute('href', initialState.grid_url)
        document.querySelector('#grid-a').setAttribute('href', initialState.grid_url)
        if (initialState.type === 'GRID') {
            this.elem.innerHTML = initialState.frame
            $('.timeline-container').removeClass('current-view')
            $('.grid-icon').addClass('current-view')
            $('.timeline-icon').css('opacity', '0.5')
            $('.grid-icon_reg').css('opacity', '1.0')
            $('.collection-name').css('display', 'none')
        }
        else if (initialState.type === 'TIMELINE') {
            $('.grid-icon').removeClass('current-view')
            $('.timeline-container').addClass('current-view')
            $('.grid-icon_reg').css('opacity', '0.5')
            $('.timeline-icon').css('opacity', '1.0')
            $('.collection-name').css('display', 'block')
            this.elem.innerHTML = initialState.frame
            this.carousel = document.querySelector('#fi-thumbnail-carousel-images')
            this.carousel.innerHTML = this.currentState.thumbnails
            this.forward = document.querySelector('#forward')
            this.backward = document.querySelector('#backward')
            document.querySelector('#metadata').innerHTML = initialState.metadata
            moveMarker(initialState.year)
            this.forward.addEventListener("mousedown", () =>
                this.forward.getAttribute('href') != '#' ? 
                    Promise.race([
                        mouseUp(this.forward).then(() => ({event: 'click', position: -100})),
                        delay(500).then(() => ({event: 'startScroll', begin: new Date()}))
                    ]).then(scrollAction(this.forward, 'forward', -200)) : undefined)

            this.backward.addEventListener("mousedown", () =>
                this.backward.getAttribute('href') != '#' ? 
                Promise.race([
                    mouseUp(this.backward).then(() => ({event: 'click', position: -100})),
                    delay(500).then(() => ({event: 'startScroll', begin: new Date()}))
                ]).then(scrollAction(this.backward, 'backward', 0)) : undefined)
        }
        applyTheme(this.randomTheme)
    }
    loadstate(data) {
        if (data.type === 'TIMELINE' && this.currentState.type === 'TIMELINE') {
            this.currentState = data
            this.carousel.innerHTML = data.thumbnails
            this.carousel.setAttribute('style', 'animation: none; animation-fill-mode: none;')
            document.querySelector('#metadata').innerHTML = data.metadata
            document.querySelector('.fi-image figure img').setAttribute('src', data.h700)
            document.querySelector('.fi-image figure img').setAttribute('alt', data.tags)
            document.querySelector('#fi-arrow-left').setAttribute('href', data.previous.url)
            document.querySelector('#fi-arrow-left').setAttribute('data-json-href', data.previous.json_url)
            document.querySelector('#fi-arrow-right').setAttribute('href', data.next.url)
            document.querySelector('#fi-arrow-right').setAttribute('data-json-href', data.next.json_url)
            this.forward.setAttribute('href', data.forward && data.forward.url ? data.forward.url : "#")
            this.forward.setAttribute('data-json-href', data.forward ? data.forward.json_url : "#")
            this.backward.setAttribute('href', data.backward && data.backward.url ? data.backward.url : "#")
            this.backward.setAttribute('data-json-href', data.backward && data.backward.json_url ? data.backward.json_url : "#")
            document.querySelector('#grid-a').setAttribute('href', data.grid_url)
            document.querySelector('#dl > a').setAttribute('href', data.original)
            moveMarker(data.year)
        }
        else {
            this.loadFrame(data)
        }
    }
}
const scrollSpeed = 4 // seconds to scroll through one set of 10 images
const toggleVis = evt => {
    const el = document.querySelector('#metadata')
    toggleElement(el);
}
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


const moveMarker = year => {
    const marker = document.querySelector('.active-year-marker');
    const markerYearElement = document.querySelector('.marker-year');

    // Update year text
    markerYearElement.textContent = year;

    // Show Marker (might not be necessary to do this display stuff)
    marker.style.display = 'block';

    // move marker to position of tick
    let tick = document.querySelector(`.year-ticker svg a rect[data-year="${year}"]`);
    let bounds = tick.getBoundingClientRect();
    let markerStyle = window.getComputedStyle(marker);
    let markerWidth = markerStyle.getPropertyValue('width').replace('px', ''); // trim off px for math
    let offset = (bounds.x - (markerWidth / 2)); // calculate marker width offset for centering on tick
    marker.style.transform = `translateX(${offset}px)`;
}


const trace = v => {
    console.log(v)
    return v
}

const scrollAction = (element, direction, target) => evt => {
    const next_page = request('GET', current_state[direction].json_url).then(data => {
        document.getElementById('fi-image').setAttribute('src', data.h700)
        document.getElementById('metadata').innerHTML = data.metadata
        document.getElementById('fi-preload-zone').innerHTML = data.thumbnails
        return data
    })
    let p
    if (evt.event === 'click') {
        p = Promise.resolve(evt)
    } else if (evt.event === 'startScroll') {
        const scrollEnd = animationEnd(carousel)
        void carousel.offsetWidth
        carousel.setAttribute('style', `animation: from-100-to${target} ${scrollSpeed}s linear;`)

        p = Promise.race([
            mouseUp(element).then(() => ({event: 'click', position: Math.round(-10 * scrollSpeed - (new Date() - evt.begin)/(-target - scrollSpeed * 10))})),
            scrollEnd.then(() => ({event: 'startScroll', begin: new Date()})),
        ])
    }
    const scroll2end = p.then(evt => {
        if (evt.event === 'click') {
            carousel.setAttribute('style', `animation: from${evt.position}-to${target} 500ms ease-out; animation-fill-mode: forwards`)
            return animationEnd(carousel)
        }
        return evt
    })
    Promise.all([next_page, scroll2end]).then(([data, evt]) => {
        loadstate(data)
        window.history.pushState(data, 'Fortepan Iowa', data.url)
        if (evt.event === 'startScroll') {
            scrollAction(element, direction, target)(evt)
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

$('input[name="startYear"]').parent().parent('div').addClass('daterange')


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


//----------changes colors of icons and --fp-main-blue css variable on page load----------

const themes = [
    { 
        color: "#6c84bd",
        logo: "/static/assets/images/skyblue/logo.svg",
        menuSvg: "/static/assets/images/skyblue/menu.svg",
        infoSvg: "/static/assets/images/skyblue/info.svg",
        downloadSvg: "/static/assets/images/skyblue/download.svg",
        searchSvg: "/static/assets/images/skyblue/search.svg",
        carrotSvg: "/static/assets/images/skyblue/carrot.svg",
        timelineSvg: '/static/assets/images/skyblue/toggle.svg'
    },
    {
        color: "#c28800",
        logo: "/static/assets/images/golden/logo.svg",
        menuSvg: "/static/assets/images/golden/menu.svg",
        infoSvg: "/static/assets/images/golden/info.svg",
        downloadSvg: "/static/assets/images/golden/download.svg",
        searchSvg: "/static/assets/images/golden/search.svg",
        carrotSvg: "/static/assets/images/golden/carrot.svg",
        timelineSvg: '/static/assets/images/golden/toggle.svg'
    },
    {
        color: "#c2a55e",
        logo: "/static/assets/images/haybail/logo.svg",
        menuSvg: "/static/assets/images/haybail/menu.svg",
        infoSvg: "/static/assets/images/haybail/info.svg",
        downloadSvg: "/static/assets/images/haybail/download.svg",
        searchSvg: "/static/assets/images/haybail/search.svg",
        carrotSvg: "/static/assets/images/haybail/carrot.svg",
        timelineSvg: '/static/assets/images/haybail/toggle.svg'
    },
    {
        color: "#445170",
        logo: "/static/assets/images/navy/logo.svg",
        menuSvg: "/static/assets/images/navy/menu.svg",
        infoSvg: "/static/assets/images/navy/info.svg",
        downloadSvg: "/static/assets/images/navy/download.svg",
        searchSvg: "/static/assets/images/navy/search.svg",
        carrotSvg: "/static/assets/images/navy/carrot.svg",
        timelineSvg: '/static/assets/images/navy/toggle.svg'
    }
]


const applyTheme = theme => {
    const hamburger = document.querySelector(".hamburger-icon")
    const info = document.querySelector('.meta-info-icon')
    const dl = document.querySelector('.meta-dl-icon')
    const search = document.querySelector('.search-icon')
    const carrot = document.querySelector('.carrot')
    const timelineMarker = document.querySelector('.marker-image')

    document.getElementsByClassName("logo-img")[0].src = theme.logo
    document.documentElement.style.setProperty("--fp-main-blue", theme.color)
    hamburger.setAttribute("src", theme.menuSvg)
    if(info && dl) {
        info.setAttribute("src", theme.infoSvg)
        dl.setAttribute("src", theme.downloadSvg)
    }
    search.setAttribute("src", theme.searchSvg);
    carrot.setAttribute("src", theme.carrotSvg);
    if (timelineMarker) {
        timelineMarker.style.backgroundImage = `url('${theme.timelineSvg}')`
    }
}
//----------_----------
