const scrollSpeed = 4 // seconds to scroll through one set of 10 images
const toggleVis = evt => {
    const el = document.querySelector('#metadata')
    toggleElement(el);
}
const toggleLogin = evt => {
    const el = document.querySelector('#login');
    console.log('toggled login');
    toggleElement(el);
}
const toggleMenu = evt => {
    const el = document.querySelector('.hamburger-menu')
    toggleElement(el)
    toggleHover()
}
const toggleElement = el => {
    console.log('el:', el);
    if (!el.classList.replace('hidden', 'gridden')) {
        el.classList.replace('gridden', 'hidden')
    }
}
const forward = document.getElementById('forward')
const backward = document.getElementById('backward')
const carousel = document.getElementById('fi-thumbnail-carousel-images')

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

const loadstate = data => {
    current_state = data
    carousel.innerHTML = data.thumbnails
    carousel.setAttribute('style', 'animation: none; animation-fill-mode: none;')
    document.getElementById('metadata').innerHTML = data.metadata
    document.getElementById('fi-image').setAttribute('src', data.h700)
    document.getElementById('fi-arrow-left').setAttribute('href', data.previous.url)
    document.getElementById('fi-arrow-left').setAttribute('data-json-href', data.previous.json_url)
    document.getElementById('fi-arrow-right').setAttribute('href', data.next.url)
    document.getElementById('fi-arrow-right').setAttribute('data-json-href', data.next.json_url)
    forward.setAttribute('href', data.forward && data.forward.url ? data.forward.url : "#")
    forward.setAttribute('data-json-href', data.forward ? data.forward.json_url : "#")
    backward.setAttribute('href', data.backward && data.backward.url ? data.backward.url : "#")
    backward.setAttribute('data-json-href', data.backward && data.backward.json_url ? data.backward.json_url : "#")
    document.getElementById('grid-a').setAttribute('href', data.grid_url)
    document.querySelector('#dl > a').setAttribute('href', data.original)
}


document.addEventListener('click', e => {
    const jsonhref = e.target.getAttribute('data-json-href') || e.target.parentNode.getAttribute('data-json-href')
    if (jsonhref) {
        e.preventDefault()
        if (jsonhref !== "#") {
            id = e.target.getAttribute('id')
            if (id !== 'forward' && id !== 'backward') {
                request('GET', jsonhref).then(data => {
                    loadstate(data)
                    window.history.pushState(data, 'Fortepan Iowa', data.url)

                })
            }
        }
    }
})

window.onpopstate = evt => {
    loadstate(evt.state)
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

if (forward) {
    forward.addEventListener("mousedown", () =>
        forward.getAttribute('href') != '#' ? 
            Promise.race([
                mouseUp(forward).then(() => ({event: 'click', position: -100})),
                delay(500).then(() => ({event: 'startScroll', begin: new Date()}))
            ]).then(scrollAction(forward, 'forward', -200)) : undefined)
}

if (backward) {
    backward.addEventListener("mousedown", () =>
        backward.getAttribute('href') != '#' ? 
        Promise.race([
            mouseUp(backward).then((backward) => ({event: 'click', position: -100})),
            delay(500).then(() => ({event: 'startScroll', begin: new Date()}))
        ]).then(scrollAction(backward, 'backward', 0)) : undefined)
}

//search dropdown
$('.search-options').click(() => {
    $('.search-form').toggle()
    /* $('.overlay').toggle() */
})
/* $('.search-options').click(() => {
    if($('.arrow').hasClass('down')) {
        $('.search-form').show()
        $('.arrow').removeClass('down').addClass('up')
    } else if ($('.arrow').hasClass('up')) {
        $('.search-form').hide()
        $('.arrow').removeClass('up').addClass('down')
    }
}) */

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

$(() => {
    if(window.location.href.includes('grid')) {
        $('.grid-icon').addClass('current-view')
        $('.timeline-icon').css('opacity', '0.5')
        $('.collection-name').css('display', 'none')
    } else {
        $('.timeline-container').addClass('current-view')
        $('.grid-icon_reg').css('opacity', '0.5')
        $('.collection-name').css('display', 'block')
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

var rect = document.querySelector("svg.tl");

if(rect) {
    rect.addEventListener("click", function(e) {
    var target = e.target,
        active = document.querySelector(".stroke");
    
    if (active !== null) {
        active.classList.remove("stroke");
    }
    
    if (target.nodeName === "rect")  {
        target.classList.add("stroke");   
    }
    });
}



//changes colors of icons and --fp-main-blue css variable on page load
//NEEDS CLEANED UP
const img1 = "/static/assets/images/skyblue/logo.svg"
const img2 = "/static/assets/images/golden/logo.svg"
const img3 = "/static/assets/images/haybail/logo.svg"
const img4 = "/static/assets/images/navy/logo.svg"
//const img5 = "/static/assets/images/purple/logo.svg"
//const img6 = "/static/assets/images/turquoise/logo.svg"
const images = [img1, img2, img3, img4]

const randomImg = images[Math.floor(Math.random()*images.length)]
window.onload = function() {
    let hamburger = document.querySelector(".hamburger-icon");
    let info = document.querySelector('.meta-info-icon')
    let dl = document.querySelector('.meta-dl-icon')
    let search = document.querySelector('.search-icon')
    let carrot = document.querySelector('.carrot')
    document.getElementsByClassName("logo-img")[0].src = randomImg;
    console.log(randomImg)
    if(randomImg == img1) {
        document.documentElement.style.setProperty("--fp-main-blue", "#6c84bd");
        hamburger.setAttribute("src", "/static/assets/images/skyblue/menu.svg");
        if(info && dl) {
            info.setAttribute("src", "/static/assets/images/skyblue/info.svg");
            dl.setAttribute("src", "/static/assets/images/skyblue/download.svg");
        }
        search.setAttribute("src", "/static/assets/images/skyblue/search.svg");
        carrot.setAttribute("src", "/static/assets/images/skyblue/carrot.svg");
    } else if(randomImg == img2) {
        document.documentElement.style.setProperty("--fp-main-blue", "#c28800");
        hamburger.setAttribute("src", "/static/assets/images/golden/menu.svg");
        if(info && dl) {
            info.setAttribute("src", "/static/assets/images/golden/info.svg");
            dl.setAttribute("src", "/static/assets/images/golden/download.svg");
        }
        search.setAttribute("src", "/static/assets/images/golden/search.svg");
        carrot.setAttribute("src", "/static/assets/images/golden/carrot.svg");
    } else if(randomImg == img3) {
        document.documentElement.style.setProperty("--fp-main-blue", "#c2a55e");
        hamburger.setAttribute("src", "/static/assets/images/haybail/menu.svg");
        if(info && dl) {
            info.setAttribute("src", "/static/assets/images/haybail/info.svg");
            dl.setAttribute("src", "/static/assets/images/haybail/download.svg");
        }
        search.setAttribute("src", "/static/assets/images/haybail/search.svg");
        carrot.setAttribute("src", "/static/assets/images/haybail/carrot.svg");
    } else if(randomImg == img4) {
        document.documentElement.style.setProperty("--fp-main-blue", "#445170");
        hamburger.setAttribute("src", "/static/assets/images/navy/menu.svg");
        if(info && dl) {
            info.setAttribute("src", "/static/assets/images/navy/info.svg");
            dl.setAttribute("src", "/static/assets/images/navy/download.svg");
        }
        search.setAttribute("src", "/static/assets/images/navy/search.svg");
        carrot.setAttribute("src", "/static/assets/images/navy/carrot.svg");
    }/*  else if(randomImg == img5) {
        document.documentElement.style.setProperty("--fp-main-blue", "#9769ac");
        hamburger.setAttribute("src", "/static/assets/images/purple/menu.svg");
        if(info && dl) {
            info.setAttribute("src", "/static/assets/images/purple/info.svg");
            dl.setAttribute("src", "/static/assets/images/purple/download.svg");
        }
        search.setAttribute("src", "/static/assets/images/purple/search.svg");
        carrot.setAttribute("src", "/static/assets/images/purple/carrot.svg");
    } else if(randomImg == img6) {
        document.documentElement.style.setProperty("--fp-main-blue", "#5ebbc2");
        hamburger.setAttribute("src", "/static/assets/images/turquoise/menu.svg");
        if(info && dl) {
            info.setAttribute("src", "/static/assets/images/turquoise/info.svg");
            dl.setAttribute("src", "/static/assets/images/turquoise/download.svg");
        }
        search.setAttribute("src", "/static/assets/images/turquoise/search.svg");
        carrot.setAttribute("src", "/static/assets/images/turquoise/carrot.svg");
    } */

};

    
