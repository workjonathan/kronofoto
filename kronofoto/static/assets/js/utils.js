export const getURLParams = () => {
    const s = window.location.search.split("+").join(encodeURIComponent("+"))
    return Object.fromEntries(new URLSearchParams(s))
}

export const trigger = (eventId, obj = {}, scope = document, doBubble = false) => {
    if (window.location.hostname === "localhost") {
        // eslint-disable-next-line no-console
        console.log(eventId, obj)
    }
    const event = new CustomEvent(eventId, {
        detail: obj,
        bubbles: doBubble,
    })
    scope.dispatchEvent(event)
}

export const appState = (state) => {
    return document.querySelector("body").classList.contains(state)
}

export const setAppState = (state) => {
    document.querySelector("body").classList.add(state)
}

export const removeAppState = (state) => {
    document.querySelector("body").classList.remove(state)
}

export const toggleAppState = (state) => {
    document.querySelector("body").classList.toggle(state)
}
