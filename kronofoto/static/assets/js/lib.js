import {enableMarkerDnD} from "./drag-drop.js"

import $ from 'jquery'

window.jQueryOrig = window.$;
window.jQuery = window.$ = $;

// Foundation
import { Foundation } from 'foundation-sites/js/foundation.core.js'
import { Toggler } from 'foundation-sites/js/foundation.toggler.js'
Foundation.plugin(Toggler, 'Toggler');

$(document).ready(function() {
    Foundation.addToJquery($);
    $(document).foundation();
});

$(document).on('on.zf.toggler', function(e) {
    $('.gallery__popup.expanded:not(#' + $(e.target).attr('id') + ')').removeClass('expanded');
});

window.jQuery = window.$ = window.jQueryOrig;

export const toggleLogin = evt => {
    const el = document.querySelector('#login');
    toggleElement(el);
}
export const toggleMenu = evt => {
    const el = document.querySelector('.hamburger-menu')
    toggleElement(el)
    toggleHover()
}
const toggleElement = el => {
    if (!el.classList.replace('hidden', 'gridden')) {
        el.classList.replace('gridden', 'hidden')
    }
}

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

const moveMarker = (root, marker) => {
    const markerYearElement = marker.querySelector('.marker-year');

    // Update year text
    const year = markerYearElement.textContent

    // Show Marker (might not be necessary to do this display stuff)
    marker.style.display = 'block';

    // move marker to position of tick
    let embedmargin = root.querySelector('.year-ticker').getBoundingClientRect().left;
    let tick = root.querySelector(`.year-ticker svg a rect[data-year="${year}"]`);
    let bounds = tick.getBoundingClientRect();
    let markerStyle = window.getComputedStyle(marker);
    let markerWidth = markerStyle.getPropertyValue('width').replace('px', ''); // trim off px for math
    let offset = (bounds.x - (markerWidth / 2) - embedmargin); // calculate marker width offset for centering on tick
    marker.style.transform = `translateX(${offset}px)`;
}

export const markerDnD = root => content => {
    if (content.id == 'active-year-marker') {
        moveMarker(root, content)
        enableMarkerDnD(root)
    }
    for (const marker of content.querySelectorAll('.active-year-marker')) {
        moveMarker(root, marker)
        enableMarkerDnD(root)
    }
}

export const installButtons = root => content => {
    const elems = Array.from(content.querySelectorAll('[data-popup-target]'))

    if (content.hasAttribute('data-popup-target')) {
        elems.push(content)
    }

    for (const elem of elems) {
        const datatarget = elem.getAttribute('data-popup-target')
        elem.addEventListener("click", evt => {
            for (const target of root.querySelectorAll('[data-popup]')) {
                if (target.hasAttribute(datatarget)) {
                    target.classList.remove("hidden")
                } else {
                    target.classList.add('hidden')
                }
            }
            elem.dispatchEvent(new Event(datatarget, {bubbles:true}))
        })
    }
}
