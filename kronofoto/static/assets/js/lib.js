"use strict";

import {enableMarkerDnD} from "./drag-drop.js"
import timeline from "./timeline";
import $ from "jquery"
import ClipboardActionCopy from 'clipboard/src/actions/copy'
import 'jquery-ui-pack'

// Foundation
import { Foundation } from 'foundation-sites/js/foundation.core';
import * as CoreUtils from 'foundation-sites/js/foundation.core.utils';
import { Motion, Move } from 'foundation-sites/js/foundation.util.motion';
import { Touch } from 'foundation-sites/js/foundation.util.touch';
import { Triggers } from 'foundation-sites/js/foundation.util.triggers';
import { Toggler } from 'foundation-sites/js/foundation.toggler';
import { Tooltip } from 'foundation-sites/js/foundation.tooltip';
import { Box } from 'foundation-sites/js/foundation.util.box';
import { MediaQuery } from 'foundation-sites/js/foundation.util.mediaQuery';


let timelineCrawlForwardInterval = null
let timelineCrawlForwardTimeout = null
let timelineCrawlBackwardInterval = null
let timelineCrawlBackwardTimeout = null
var timelineInstance = null
let htmx = undefined

export const initJQuery = (context) => {
  var initjQuery = $.fn.init;
  $.fn.init = function(s,c,r) {
    c = c || context;
    return new initjQuery(s,c,r);
  };
}

export const initHTMXListeners = (_htmx, context, root) => {
  htmx = _htmx
  

  htmx.onLoad((e) => {
    if (e.querySelectorAll(".photos-timeline").length) {
        timelineInstance = undefined
        initTimeline(context)
    }
    initNavSearch(e)
    initPopups(e)
    initEventHandlers(e)
    initGalleryNav(e)
    if (window.st && e.querySelectorAll('.sharethis-inline-share-buttons').length) {
        st.initialize()
    }

    initDraggableThumbnails()
    initAutocomplete()
    // Init gallery thumbnails
    if ($('#fi-preload-zone li').length) {


      let html = $('#fi-preload-zone').html()
      // let firstId = $(html).find('li:first-child span').attr('hx-get')
      $('#fi-thumbnail-carousel-images').html(html)
      // let $after = $('#fi-thumbnail-carousel-images li span[hx-get="'+firstId+'"]').nextAll()
      // $('#fi-thumbnail-carousel-images').append($after)
      $('#fi-thumbnail-carousel-images').addClass('dragging')
      $('#fi-thumbnail-carousel-images').css('left', '0px')
      setTimeout(() => {
        $('#fi-thumbnail-carousel-images').removeClass('dragging')
        if (!$('#fi-thumbnail-carousel-images [data-origin]').length) {
          $('#fi-thumbnail-carousel-images [data-active]').attr('data-origin', '')
        }
      }, 100)

      htmx.process($('#fi-thumbnail-carousel-images').get(0))
      $('#fi-preload-zone').empty()
    }

    if ($('#fi-image-preload img').length && !$('#fi-image-preload img').data('loaded')) {
      $('#fi-image-preload img').data('loaded', true)
      let url = $('#fi-image-preload img').attr('src')
      const image = new Image();
      image.src = url;
      image.onload = () => {
        let html = $('#fi-image-preload').html()
        $('#fi-image').html(html)
        $('#fi-image-preload').empty()
      }
    }

  })

  return htmx

}
export const initFoundation = (context) => {

  Foundation.addToJquery($);
  Foundation.Box = Box;
  Foundation.MediaQuery = MediaQuery;
  Foundation.Motion = Motion;
  Foundation.Move = Move;
  Triggers.Initializers.addToggleListener($(context));

  Foundation.plugin(Toggler, 'Toggler');
  Foundation.plugin(Tooltip, 'Tooltip');

  $(context).foundation()

}

export const initTimeline = (context) => {
  if(!timelineInstance) {
    timelineInstance = new timeline();
    $('.photos-timeline', context).each(function(i, e) {
      timelineInstance.connect(e, context);
    });
  }

  return timelineInstance
}
export const initEventHandlers = (context) => {

  $(context).on('click', '.form--add-tag .link--icon', (e) => {
    let $form = $(e.currentTarget).closest('form')
    $form.addClass('expanded')
    $('input[type=text]', $form).focus()
  })

  $(context).on('click', (e) => {
    if (!$('.form--add-tag input').is(":focus")) {
        let $form = $('.form--add-tag input').closest('form')
        $form.removeClass('expanded')
        setTimeout(() => $('.form--add-tag input').val(''), 0)
    }
  })

  $(context).on('change keydown paste input', 'input', (e) => {
    if ($(e.currentTarget).closest('form')) {
      $(e.currentTarget).closest('form').find('[data-enable-on-modify]').removeAttr('disabled')
    }
  })

  $(context).on('on.zf.toggler', function(e) {
    if($(e.target).hasClass('gallery__popup')) {
      $('.gallery__popup.expanded:not(#' + $(e.target).attr('id') + ')').removeClass('expanded');
    }
  });

  $(context).on('submit', '#add-to-list-popup form', function(e) {
    // Check if logged in
    if ($('#login-btn').length) {
      $('#login-btn').trigger('click')
      showToast('You must login to continue')
    } else {
      showToast('Updated photo lists')
    }
  })

  $('#overlay').on('click', (e) => {
    $('#login').addClass('collapse')
    $('#hamburger-menu').addClass('collapse')
    $('#overlay').fadeOut()
  })

  $('#hamburger-menu').on('off.zf.toggler', (e) => {
    $('#login').addClass('collapse')
    $('#overlay').fadeIn()
  }).on('on.zf.toggler', (e) => {
    if ($('#login').hasClass('collapse')) {
      $('#overlay').fadeOut()
    }
  })

  $('#login').on('off.zf.toggler', (e) => {
    $('#hamburger-menu').addClass('collapse')
    $('#overlay').fadeIn()
  }).on('on.zf.toggler', (e) => {
    if ($('#hamburger-menu').hasClass('collapse')) {
      $('#overlay').fadeOut()
    }
  })

  // $(context).click(function(event) {
  //
  //   //~TESTING LINE
  //   //console.log(event.target.className)
  //
  //   var classOfThingClickedOn = event.target.className
  //
  //   //~TESTING LINE
  //   //console.log($('.search-form').find('*'))
  //
  //   //creates a jQuery collection of the components of the search menu EXCEPT for the menu itself
  //   var $descendantsOfSearchForm = $('.search-form').find('*')
  //
  //   //---creates an array of all components of the search menu dropdown---
  //   //adds the search menu itself to the array
  //   var componentsOfSearchMenuArray = ['search-form']
  //
  //   //adds the class of all the components of the search menu to the array
  //   $descendantsOfSearchForm.each(function(index) {
  //     //checks to make sure the class isn't already in the array
  //     if ($.inArray(this.className, componentsOfSearchMenuArray) == -1) {
  //       //adds the class to the array
  //       componentsOfSearchMenuArray.push(this.className)
  //     }
  //   })
  //
  //   //~TESTING LINES
  //   //console.log(componentsOfSearchMenuArray)
  //   //console.log('Class:'+'"'+classOfThingClickedOn+'"')
  //   //console.log(componentsOfSearchMenuArray.includes(classOfThingClickedOn))
  //
  //   //if the search menu is open and the user clicks on something outside of the menu, close the menu
  //   if ($(event.target).attr('id') != 'search-box' && $('.search-form').is(":visible") && (!(componentsOfSearchMenuArray.includes(classOfThingClickedOn)))) {
  //     collapseNavSearch()
  //   }
  //   //if the user clicks on the carrot or the small invisible box behind it, toggle the menu
  //   else if (classOfThingClickedOn == 'search-options' || classOfThingClickedOn == 'carrot') {
  //     // $('.search-form').toggle()
  //   }
  // })

  $(context).on('click', '#forward-zip', timelineZipForward)
  $(context).on('click', '#forward', timelineForward)
  $(context).on('mousedown', '#forward-zip', timelineCrawlForward)
  $(context).on('mouseup', '#forward-zip', timelineCrawlForwardRelease)
  $(context).on('click', '#backward-zip', timelineZipBackward)
  $(context).on('click', '#backward', timelineBackward)
  $(context).on('mousedown', '#backward-zip', timelineCrawlBackward)
  $(context).on('mouseup', '#backward-zip', timelineCrawlBackwardRelease)
  $(context).on('click', '#fi-arrow-right', timelineForward)
  $(context).on('click', '#fi-arrow-left', timelineBackward)
  $(context).on('click', '#fi-thumbnail-carousel-images li span', function(e) {
    let num = $('#fi-thumbnail-carousel-images li').length
    let delta = $(e.currentTarget).parent().index() - ((num - 1) / 2)
    gotoTimelinePosition(delta)
  })


  $(context).on('keydown', function(event) {
    var keyCode = event.which || event.keyCode;

    // Handle forward arrow key (Right Arrow or Down Arrow)
    if (keyCode === 39) {
      // Perform the action for the forward arrow key
      timelineForward()
    }

    // Handle back arrow key (Left Arrow or Up Arrow)
    if (keyCode === 37) {
      // Perform the action for the back arrow key
      timelineBackward()
    }
  });

  $(context).on('click', '#auto-play-image-control-button', (e) => {
    let $btn = $('#auto-play-image-control-button')
    $btn.toggleClass('active')
    if ($btn.hasClass('active')) {
      autoplayStart()
    } else {
      autoplayStop()
    }
  })

  $(context).on('click', '.image-control-button--toggle', (e) => {
    let $btn = $(e.currentTarget)
    $('img', $btn).toggleClass('hide')
  })

}
export const initClipboardJS = (context) => {
  $(context).on('click', '.copy-button', (e) => {
    let target = $(e.currentTarget).attr('data-clipboard-target')
    let text = $(target).val()
    ClipboardActionCopy(text)
    $(target).select()
    $(target)[0].setSelectionRange(0, 999999)
  })
}
export const initAutocomplete = () => {
  $('#tag-search').autocomplete({
    source: '/tags',
    minLength: 2,
  })
}
export const initDraggableThumbnails = () => {
  if (!$('#fi-thumbnail-carousel-images [data-origin]').length) {
    $('#fi-thumbnail-carousel-images [data-active]').attr('data-origin', '')
  }
  $('#fi-thumbnail-carousel-images').draggable({
    axis: 'x',
    drag: (event, ui) => {
      moveTimelineCoin(ui.position.left, true)
    },
    stop: (event, ui) => {
      dropTimelineCoin(ui.position.left)
    }
  })
}
export const initPopups = (context) => {
  if ($('#add-to-list-popup').length) {
    $('#app').foundation()
  }
}
export const collapseNavSearch = () => {
  $('#search-box-container').removeClass('expanded')
  $('.search-form').hide()
  $('#search-box').val('')
  $('.search-icon').css('filter', 'none')
  $('.carrot').css('filter', 'none')
  $('#search-box').removeClass('placeholder-light').css('color', '#333')
}

export const expandNavSearch = () => {
  $('#search-box-container').addClass('expanded')
  $('.search-form').show()
  $('.search-icon').css('filter', 'brightness(0) invert(1)')
  $('.carrot').css('filter', 'brightness(0) invert(1)')
  $('#search-box').addClass('placeholder-light').css('color', 'white')
}
export const initNavSearch = (context) => {

  $('.search-form__clear-btn').click((e) => {
    e.preventDefault();
    $('#search-box').val('')
    $('.search-form input[type=text]').val('')
    $('.search-form select').val('')
  })
  $('#search-box').click(expandNavSearch)
  $('#search-box').on('keydown', (e) => {
    if(e.which === 13) {
      e.preventDefault()
      $('#search-box').closest('form').submit()
    }
  })
  $('#search-box-container .close-icon').click(collapseNavSearch)
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
    htmx.trigger('#fi-arrow-right', 'click')
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
  $('#thumbnail-request-left').submit((e) => {
    e.preventDefault()
    $.ajax({
      url: e.currentTarget.action,
      type: 'post',
      dataType: 'application/json',
      data: $('#thumbnail-request-left').serialize(),
      success: (data) => {
        console.log(data)
      }
    })
  })

  return;
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
  htmx.trigger($('#fi-thumbnail-carousel-images li[data-active] span').get(0), 'manual')
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
    // htmx.trigger($nextLi.find('a').get(0), 'manual')
  }
  return false
}

export const timelineZipForward = () => {
  if(timelineCrawlForwardInterval == null) { // only zip if we're not already crawling
    let numToZip = Math.floor((getNumVisibleTimelineTiles() - 0.5))
    let $activeLi = $('#fi-thumbnail-carousel-images li[data-active]')
    let $nextLi = $activeLi.prevAll().eq(numToZip)
    //gotoTimelinePosition(numToZip)
    // htmx.trigger($nextLi.find('a').get(0), 'manual')
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

export const initGalleryNav = (context) => {
  let hideGalleryTimeout = null;
  // When the mouse moves
  context.addEventListener('mousemove', () => {
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
