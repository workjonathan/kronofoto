const toggleVis = evt => {
    const el = document.querySelector('#metadata')
    toggleElement(el);
}
const toggleLogin = evt => {
    const el = document.querySelector('#login');
    console.log('toggled login');
    toggleElement(el);
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
    forward.setAttribute('href', data.forward.url)
    backward.setAttribute('href', data.backward.url)
}


let current_state = JSON.parse(document.getElementById('initial-state').textContent)
window.history.replaceState(current_state, 'Fortepan Iowa', current_state.url)
document.addEventListener('click', e => {
    if (e.target.getAttribute('data-json-href')) {
        e.preventDefault()
        id = e.target.getAttribute('id')
        if (id !== 'forward' && id !== 'backward') {
            request('GET', e.target.getAttribute('data-json-href')).then(data => {
                loadstate(data)
                window.history.pushState(data, 'Fortepan Iowa', data.url)

            })
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
        carousel.setAttribute('style', `animation: from-100-to${target} 10s linear;`)
        p = Promise.race([
            mouseUp(element).then(() => ({event: 'click', position: Math.round(-100 - (new Date() - evt.begin)/(-target - 100))})),
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
        Promise.race([
            mouseUp(forward).then(() => ({event: 'click', position: -100})),
            delay(500).then(() => ({event: 'startScroll', begin: new Date()}))
        ]).then(scrollAction(forward, 'forward', -200)))
}
if (backward) {
    backward.addEventListener("mousedown", () =>
        Promise.race([
            mouseUp(backward).then((backward) => ({event: 'click', position: -100})),
            delay(500).then(() => ({event: 'startScroll', begin: new Date()}))
        ]).then(scrollAction(backward, 'backward', 0)))
}
