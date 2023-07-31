import {enableMarkerDnD} from "./drag-drop.js"
import $ from 'jquery'

// Foundation
import { Foundation, Toggler, Tooltip, Box, MediaQuery, Triggers } from 'foundation-sites'

window.jQueryOrig = window.$
window.jQuery = window.$ = $
let timelineCrawlForwardInterval = null
let timelineCrawlForwardTimeout = null
let timelineCrawlBackwardInterval = null
let timelineCrawlBackwardTimeout = null

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

export const autoplayStart = () => {
  window.autoplayTimer = setInterval(() => {
    window.htmx.trigger('#fi-arrow-right', 'click')
  }, 5000)
}

export const autoplayStop = () => {
  clearInterval(window.autoplayTimer)
}

export const moveTimelineCoin = (deltaX, drag = false) => {
  if(drag) {
    $('#fi-thumbnail-carousel-images').addClass('dragging')
  }
  else {
    $('#fi-thumbnail-carousel-images').removeClass('dragging')
  }
  let width = $('#fi-thumbnail-carousel-images li').outerWidth()
  let preItemNum = 20
  let quantizedX = (Math.round(deltaX / width) * -1)
  let itemNum = preItemNum + quantizedX + 1
  $('#fi-thumbnail-carousel-images li').removeAttr('data-active')
  $('#fi-thumbnail-carousel-images li:nth-child('+ itemNum +')').attr('data-active', '')
}

export const dropTimelineCoin = (deltaX) => {
  let width = $('#fi-thumbnail-carousel-images li').outerWidth()
  let quantizedX = (Math.round(deltaX / width))
  let itemNum = quantizedX
  $('#fi-thumbnail-carousel-images').css({left: itemNum * width})
  window.htmx.trigger($('#fi-thumbnail-carousel-images li[data-active] a').get(0), 'manual')
}
export const timelineZipForward = () => {
  if(timelineCrawlForwardInterval == null) { // only zip if we're not already crawling
    let numToZip = Math.floor((getNumVisibleTimelineTiles() - 0.5))
    let $activeLi = $('#fi-thumbnail-carousel-images li[data-active]')
    let $nextLi = $activeLi.nextAll().eq(numToZip)
    window.htmx.trigger($nextLi.find('a').get(0), 'manual')
  }
  return false
}

export const timelineZipBackward = () => {
  if(timelineCrawlBackwardInterval == null) { // only zip if we're not already crawling
    let numToZip = Math.floor((getNumVisibleTimelineTiles() - 0.5))
    let $activeLi = $('#fi-thumbnail-carousel-images li[data-active]')
    let $nextLi = $activeLi.prevAll().eq(numToZip)
    window.htmx.trigger($nextLi.find('a').get(0), 'manual')
  }
  return false
}

export const timelineForward = () => {
  window.htmx.trigger($('#fi-arrow-right').get(0), 'click')
}

export const timelineBackward = () => {
  window.htmx.trigger($('#fi-arrow-left').get(0), 'click')
}

export const timelineCrawlForward = () => {
  let self = this
  timelineCrawlForwardTimeout = setTimeout(() => {
    timelineCrawlForwardInterval = setInterval(() => {
      let left = $('#fi-thumbnail-carousel-images').position().left
      $('#fi-thumbnail-carousel-images').css('left', left - 20)
      moveTimelineCoin($('#fi-thumbnail-carousel-images').position().left)
    }, 100)
  }, 500)
}

export const timelineCrawlForwardRelease = () => {
  clearTimeout(timelineCrawlForwardTimeout)
  timelineCrawlForwardTimeout = null
  if(timelineCrawlForwardInterval) { // only execute when we're crawling
    clearInterval(timelineCrawlForwardInterval)
    dropTimelineCoin($('#fi-thumbnail-carousel-images').position().left)
    setTimeout(() => {
      timelineCrawlForwardInterval = null
    }, 250)
  }
}

export const timelineCrawlBackward = () => {
  timelineCrawlBackwardTimeout = setTimeout(() => {
    timelineCrawlBackwardInterval = setInterval(() => {
      let left = $('#fi-thumbnail-carousel-images').position().left
      $('#fi-thumbnail-carousel-images').css('left', left + 20)
      moveTimelineCoin($('#fi-thumbnail-carousel-images').position().left)
    }, 100)
  }, 500)
}

export const timelineCrawlBackwardRelease = () => {
  clearTimeout(timelineCrawlBackwardTimeout)
  timelineCrawlBackwardTimeout = null
  if(timelineCrawlBackwardInterval) { // only execute when we're crawling
    clearInterval(timelineCrawlBackwardInterval)
    dropTimelineCoin($('#fi-thumbnail-carousel-images').position().left)
    setTimeout(() => {
      timelineCrawlBackwardInterval = null
    }, 250)
  }
}

const getNumVisibleTimelineTiles = () => {
  let widthOfTimeline = $('#fi-image').width() // assumes the timeline is the same width as gallery image
  let $li = $('#fi-thumbnail-carousel-images li[data-active]')
  let widthOfTile = $li.outerWidth()
  return Math.floor(widthOfTimeline/widthOfTile)
}

export const initGalleryNav = () => {
  let hideGalleryTimeout = null;
  // When the mouse moves
  document.addEventListener('mousemove', () => {
    showGalleryNav()
    if(hideGalleryTimeout)
      clearTimeout(hideGalleryTimeout)
    hideGalleryTimeout = setTimeout(hideGalleryNav, 5000)
  })
}
const hideGalleryNav = () => {
  $('.gallery').addClass('hide-nav')
}

const showGalleryNav = () => {
  $('.gallery').removeClass('hide-nav')
}

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
