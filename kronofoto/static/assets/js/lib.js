import {enableMarkerDnD} from "./drag-drop.js"

// Foundation
import { Foundation, Toggler, Tooltip, Box, MediaQuery, Triggers } from 'foundation-sites'

window.$ = window.jQuery
let timelineCrawlForwardInterval = null
let timelineCrawlForwardTimeout = null
let timelineCrawlBackwardInterval = null
let timelineCrawlBackwardTimeout = null

$(document).ready(function() {
    $(document).foundation();
    $(document).on('click', '.form--add-tag .link--icon', (e) => {
      let $form = $(e.currentTarget).closest('form')
      $form.addClass('expanded')
      $('input[type=text]', $form).focus()
    })
    $(document).on('focusout', '.form--add-tag input[type=text]', function(e) {
        let $form = $(e.currentTarget).closest('form')
        $form.removeClass('expanded')
        $(e.currentTarget).val('')
    })
})

$(document).on('on.zf.toggler', function(e) {
    if($(e.target).hasClass('gallery__popup')) {
        $('.gallery__popup.expanded:not(#' + $(e.target).attr('id') + ')').removeClass('expanded');
    }
});

// window.jQuery = window.$ = window.jQueryOrig

export const initNavSearch = () => {
  $('#search-box').focus(function() {
    $('#search-box-container').addClass('expanded')
    $('.search-form').show()
    $('.search-icon').css('filter', 'brightness(0) invert(1)')
    $('.carrot').css('filter', 'brightness(0) invert(1)')
    $('#search-box').addClass('placeholder-light').css('color', 'white')

  })
  $('#search-box .close-icon').click(function() {
    $('#search-box-container').removeClass('expanded')
    $('.search-form').hide()
    $('#search-box').val('')
    $('.search-icon').css('filter', 'none')
    $('.carrot').css('filter', 'none')
    $('#search-box').removeClass('placeholder-light').css('color', '#333')
  });
}

export const showToast = (message) => {
  let content = $('#toast-template').html()
  let $message = $(content)
  $message.prepend('<p>'+message+'</p>')
  $('#messages').append($message)
  setTimeout(() => {
    $message.fadeOut(() => {
      $message.remove()
    })
  }, 5000)
}

export const autoplayStart = () => {
  window.autoplayTimer = setInterval(() => {
    window.htmx.trigger('#fi-arrow-right', 'click')
  }, 5000)
}

export const autoplayStop = () => {
  clearInterval(window.autoplayTimer)
}

export const moveTimelineCoin = (deltaX, drag = true) => {
  if(drag) {
    $('#fi-thumbnail-carousel-images').addClass('dragging')
  }
  else {
    $('#fi-thumbnail-carousel-images').removeClass('dragging')
  }
  let widthOfThumbnail = $('#fi-thumbnail-carousel-images li').outerWidth()
  let preItemNum = $('#fi-thumbnail-carousel-images [data-origin]').index()
  let quantizedPositionX = (Math.round(deltaX / widthOfThumbnail) * -1)
  let currentPosition = preItemNum + quantizedPositionX + 1

  let numThumbnails= $('#fi-thumbnail-carousel-images li').length

  if(drag && numThumbnails - currentPosition < preItemNum) {
    getMoreThumbnailsRight()
  }
  else if(drag && currentPosition < preItemNum) {
    getMoreThumbnailsLeft()
  }

  $('#fi-thumbnail-carousel-images li').removeAttr('data-active')
  $('#fi-thumbnail-carousel-images li:nth-child('+ currentPosition +')').attr('data-active', '')
}

let moreThumbnailsLoading = false

const getMoreThumbnailsRight = () => {
  let url = $('#fi-thumbnail-carousel-images li:last-child span').attr('hx-get')
  if(!moreThumbnailsLoading) {
    moreThumbnailsLoading = true
    $.ajax({
      url: url,
      type: 'GET',
      headers: {
        'Hx-Target': 'fi-preload-zone',
        'Hx-Request': true
      },
      success: (e) => {
        moreThumbnailsLoading = false

        let firstId = $('#fi-thumbnail-carousel-images li:last-child span').attr('hx-get')
        let $after = $(e).find('span[hx-get="'+firstId+'"]').parent().nextAll()
        // $after.find('[data-active]').removeAttr('data-active')
        let index = 1
        let offset = $('#fi-thumbnail-carousel-images li:last-child').position().left
        let width = $('#fi-thumbnail-carousel-images li:last-child').outerWidth()
        $after.each((i,e) => {
          $(e).css({
            position: 'absolute',
            left: (index * width) + offset
          })
          index += 1
        })
        $('#fi-thumbnail-carousel-images').append($after)
        htmx.process($('#fi-thumbnail-carousel-images').get(0))
      }
    })
  }
}

const getMoreThumbnailsLeft = () => {
  let url = $('#fi-thumbnail-carousel-images li:first-child span').attr('hx-get')
  if(!moreThumbnailsLoading) {
    moreThumbnailsLoading = true
    $.ajax({
      url: url,
      type: 'GET',
      headers: {
        'Hx-Target': 'fi-preload-zone',
        'Hx-Request': true
      },
      success: (e) => {
        moreThumbnailsLoading = false
        window.e = e
        let firstId = $('#fi-thumbnail-carousel-images li:first-child span').attr('hx-get')
        let $before = $(e).find('span[hx-get="'+firstId+'"]').parent().prevAll()
        // $before.find('[data-active]').removeAttr('data-active')
        let index = -1
        let offset = $('#fi-thumbnail-carousel-images li:first-child').position().left
        let width = $('#fi-thumbnail-carousel-images li:first-child').outerWidth()
        $($before.get().reverse()).each((i,e) => {
          $(e).css({
            position: 'absolute',
            left: index * width + offset
          })
          index -= 1
        })
        $('#fi-thumbnail-carousel-images').prepend($before)
        htmx.process($('#fi-thumbnail-carousel-images').get(0))
      }
    })
  }
}

export const dropTimelineCoin = (deltaX) => {
  let width = $('#fi-thumbnail-carousel-images li').outerWidth()
  let quantizedX = (Math.round(deltaX / width))
  let itemNum = quantizedX
  $('#fi-thumbnail-carousel-images').css({left: itemNum * width})
  window.htmx.trigger($('#fi-thumbnail-carousel-images li[data-active] span').get(0), 'manual')
}

export const refreshThumbnails = () => {
  // Do we need thumbnails?
  // Which direction do we need more thumbnails?

  if($('#fi-preload-zone li').length) {
    let html = $('#fi-preload-zone').html()
    let firstId = $(html).find('li:first-child span').attr('hx-get')
    $('#fi-thumbnail-carousel-images').html(html)
    let $after = $('#fi-thumbnail-carousel-images li span[hx-get="'+firstId+'"]').nextAll()
    $('#fi-thumbnail-carousel-images').append($after)
    //   $('#fi-thumbnail-carousel-images').addClass('dragging')
    //   $('#fi-thumbnail-carousel-images').css('left', '0px')
    //   setTimeout(() => {
    //     $('#fi-thumbnail-carousel-images').removeClass('dragging')
    //   }, 100)
    htmx.process($('#fi-thumbnail-carousel-images').get(0))
    $('#fi-preload-zone').empty()
  }
}

export const gotoTimelinePosition = (delta) => {
  let width = $('#fi-thumbnail-carousel-images li').outerWidth()
  moveTimelineCoin(delta * -1 * width, false)
  dropTimelineCoin(delta * -1 * width)
}
export const timelineZipBackward = () => {
  if(timelineCrawlBackwardInterval == null) { // only zip if we're not already crawling
    let numToZip = Math.floor((getNumVisibleTimelineTiles() - 0.5))
    let $activeLi = $('#fi-thumbnail-carousel-images li[data-active]')
    let $nextLi = $activeLi.nextAll().eq(numToZip)
    gotoTimelinePosition(numToZip * -1)
    // window.htmx.trigger($nextLi.find('a').get(0), 'manual')
  }
  return false
}

export const timelineZipForward = () => {
  if(timelineCrawlForwardInterval == null) { // only zip if we're not already crawling
    let numToZip = Math.floor((getNumVisibleTimelineTiles() - 0.5))
    let $activeLi = $('#fi-thumbnail-carousel-images li[data-active]')
    let $nextLi = $activeLi.prevAll().eq(numToZip)
    gotoTimelinePosition(numToZip)
    // window.htmx.trigger($nextLi.find('a').get(0), 'manual')
  }
  return false
}

export const timelineForward = () => {
  gotoTimelinePosition(1)
}

export const timelineBackward = () => {
  gotoTimelinePosition(-1)
}

export const timelineCrawlForward = () => {
  let self = this
  timelineCrawlForwardTimeout = setTimeout(() => {
    let currentPosition = $('#fi-thumbnail-carousel-images').position().left
    timelineCrawlForwardInterval = setInterval(() => {
      if(canCrawlForward()) {
        currentPosition -= 20
        $('#fi-thumbnail-carousel-images').css('left', currentPosition)
        moveTimelineCoin(currentPosition)
      }
    }, 50)
  }, 500)
}

const canCrawlForward = () => {
  let length = $('#fi-thumbnail-carousel-images [data-active]').nextAll().length
  return length > 10
}

export const timelineCrawlForwardRelease = () => {
  clearTimeout(timelineCrawlForwardTimeout)
  timelineCrawlForwardTimeout = null
  if(timelineCrawlForwardInterval) { // only execute when we're crawling
    clearInterval(timelineCrawlForwardInterval)
    dropTimelineCoin($('#fi-thumbnail-carousel-images').position().left)
    setTimeout(() => {
      timelineCrawlForwardInterval = null
    }, 750)
  }
}

export const timelineCrawlBackward = () => {
  timelineCrawlBackwardTimeout = setTimeout(() => {
    let currentPosition = $('#fi-thumbnail-carousel-images').position().left
    timelineCrawlBackwardInterval = setInterval(() => {
      if(canCrawlBackward()) {
        currentPosition += 20
        $('#fi-thumbnail-carousel-images').css('left', currentPosition)
        moveTimelineCoin(currentPosition)
      }
    }, 50)
  }, 500)
}

const canCrawlBackward = () => {
  let length = $('#fi-thumbnail-carousel-images [data-active]').prevAll().length
  return length > 10
}

export const timelineCrawlBackwardRelease = () => {
  clearTimeout(timelineCrawlBackwardTimeout)
  timelineCrawlBackwardTimeout = null
  if(timelineCrawlBackwardInterval) { // only execute when we're crawling
    clearInterval(timelineCrawlBackwardInterval)
    dropTimelineCoin($('#fi-thumbnail-carousel-images').position().left)
    setTimeout(() => {
      timelineCrawlBackwardInterval = null
    }, 750)
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
    // if(!$('.hamburger').hasClass('is-active')) {
    //   $('.hamburger').addClass('is-active')
    //   $('.hamburger-menu').removeClass('collapse')
    //   $('body').addClass('menu-expanded')
    //   $('.overlay').fadeIn()
    // }
    // else {
    //   $('.hamburger').removeClass('is-active')
    //   $('.hamburger-menu').addClass('collapse')
    //   $('body').removeClass('menu-expanded')
    //   $('.overlay').fadeOut()
    // }
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
