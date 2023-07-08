import {enableMarkerDnD} from "./drag-drop.js"
import $ from 'jquery'

// Foundation
import { Foundation, Toggler, Tooltip, Box, MediaQuery, Triggers } from 'foundation-sites'

window.jQueryOrig = window.$
window.jQuery = window.$ = $

Foundation.MediaQuery = MediaQuery;
Foundation.plugin(Toggler, 'Toggler');
Foundation.plugin(Tooltip, 'Tooltip');

$(document).ready(function($) {
    $(document).foundation();
    $('.form--add-tag').each(function(i,e) {
        $('.link--icon', e).click(function() {
            $(e).addClass('expanded')
            $('input[type=text]', e).focus()
        })
        $(e).on('focusout', 'input[type=text]', function(f) {
            $(e).removeClass('expanded')
            $(f.currentTarget).val('')
        })
    })

});

new window.ClipboardJS('[data-clipboard-target]');

$(document).on('on.zf.toggler', function(e) {
    if($(e.target).hasClass('gallery__popup')) {
        $('.gallery__popup.expanded:not(#' + $(e.target).attr('id') + ')').removeClass('expanded');
    }
});

window.jQuery = window.$ = window.jQueryOrig

export const toggleLogin = evt => {
    const el = document.querySelector('#login');
    toggleElement(el);
}
export const toggleMenu = evt => {
    if(!$('.hamburger').hasClass('is-active')) {
      $('.hamburger').addClass('is-active')
      $('.hamburger-menu').removeClass('collapse')
      $('body').addClass('menu-expanded')
      $('.overlay').fadeIn()
    }
    else {
      $('.hamburger').removeClass('is-active')
      $('.hamburger-menu').addClass('collapse')
      $('body').removeClass('menu-expanded')
      $('.overlay').fadeOut()
    }
}
const toggleElement = el => {
    if (!el.classList.replace('hidden', 'gridden')) {
        el.classList.replace('gridden', 'hidden')
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
