"use strict";

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

export const initHTMXListeners = (_htmx, context, {lateLoad=false} = {}) => {
  htmx = _htmx
 
  const addZoom = (container) => {
    let imgsrc = container.currentStyle || window.getComputedStyle(container, false);
    imgsrc = imgsrc.backgroundImage.slice(4, -1).replace(/"/g, "");

    let img = new Image();
    let zoomOpened = false
    let zoomed = false
    let galleryElem = context.querySelector('.gallery')[0]
    img.src = imgsrc;
    img.onload = () => {


      let ratio = img.naturalWidth / img.naturalHeight;

      Object.assign(container.style, {
        height: "calc(100vh)",
        width: "calc(100vw)",
        backgroundPosition: "top",
        backgroundSize: "contain",
        backgroundRepeat: "no-repeat"
      });

      let removeZoom = () => {
        Object.assign(container.style, {
          backgroundPosition: "top",
          backgroundSize: "contain"
        });
      }

      container.addEventListener('click', (e) => {
        zoomed = !zoomed;

        if(zoomed) {
          galleryElem.classList.add('zoomed')
        }
        else {
          galleryElem.classList.remove('zoomed')
          removeZoom()
        }
      })

      container.onmousemove = (e) => {
        if(zoomed) {
          let rect = e.target.getBoundingClientRect(),
              xPos = e.clientX - rect.left,
              yPos = e.clientY - rect.top,
              xPercent = ((xPos / container.clientWidth) * 100) + "%",
              yPercent = ((yPos / container.clientHeight) * 100) + "%";

          Object.assign(container.style, {
            backgroundPosition: xPercent + " " + yPercent,
            backgroundSize: (window.innerWidth * 1.5) + "px"
          });
        }
      };

      // container.onmouseleave = removeZoom

    }
  }
  const slideToId = ({target, fi}) => {
    for (const targets of context.querySelectorAll(target)) {
        let destination, candidate = undefined
        for (const elem of targets.querySelectorAll(`:scope [data-fi="${fi}"]`)) {
            candidate = elem
            for (const img of elem.querySelectorAll(":scope a img")) {
                if (!img.classList.contains("empty")) {
                    destination = candidate
                }
            }
        }
        if (!destination) {
            destination = candidate
        }
        const origin = targets.querySelector(`:scope [data-origin]`)
        if (destination && origin) {
            const children = [...targets.children]
            const delta = children.indexOf(destination) - children.indexOf(origin)
            gotoTimelinePosition(delta, false)
        }
    }
  }

  const onLoad = elem => {
    for (const elem2 of elem.querySelectorAll("#follow-zoom-timeline-version")) {
        addZoom(elem2)
    }
    for (const elem2 of elem.querySelectorAll("#backward-zip")) {
        elem2.addEventListener("click", timelineZipBackward)
        elem2.addEventListener("mousedown", timelineCrawlBackward)
        elem2.addEventListener("mouseup", timelineCrawlBackwardRelease)
    }
    if (elem.id == "backward-zip") {
        elem.addEventListener("click", timelineZipBackward)
        elem.addEventListener("mousedown", timelineCrawlBackward)
        elem.addEventListener("mouseup", timelineCrawlBackwardRelease)
    }
    for (const elem2 of elem.querySelectorAll("#forward-zip")) {
        elem2.addEventListener("click", timelineZipForward)
        elem2.addEventListener("mousedown", timelineCrawlForward)
        elem2.addEventListener("mouseup", timelineCrawlForwardRelease)
    }
    if (elem.id == "forward-zip") {
        elem.addEventListener("click", timelineZipForward)
        elem.addEventListener("mousedown", timelineCrawlForward)
        elem.addEventListener("mouseup", timelineCrawlForwardRelease)
    }
    if (elem.querySelectorAll(".photos-timeline").length) {
        timelineInstance = undefined
        initTimeline(context)
    }
    for (const thumbs of elem.querySelectorAll("#fi-thumbnail-carousel-images")) {
        initDraggableThumbnails(thumbs)
    }
    initAutocomplete()
    initNavSearch(elem)
    initPopups(elem)
    if (window.st && elem.querySelectorAll('.sharethis-inline-share-buttons').length) {
        st.initialize()
    }
    initEventHandlers(elem)
    initGalleryNav(elem)
    /*

  */
    // Init gallery thumbnails

    if (elem.id == 'fi-preload-zone') {
      slideToId({
        fi: elem.getAttribute("data-slide-id"),
        target: "[data-fi-thumbnail-carousel-images]",
      })
      setTimeout(() => {
          let html = $('#fi-preload-zone').html()
          // let firstId = $(html).find('li:first-child span').attr('hx-get')
          $('#fi-thumbnail-carousel-images').html(html)
          // let $after = $('#fi-thumbnail-carousel-images li span[hx-get="'+firstId+'"]').nextAll()
          // $('#fi-thumbnail-carousel-images').append($after)
          $('#fi-thumbnail-carousel-images').addClass('dragging')
          $('#fi-thumbnail-carousel-images').css('left', '0px')
          setTimeout(() => {
            $('#fi-thumbnail-carousel-images').removeClass('dragging')
          }, 100)

          htmx.process($('#fi-thumbnail-carousel-images').get(0))
          $('#fi-preload-zone').empty()
      }, 250)
    }

/*  disabled until different solution is tried (set attributes without replacing tag)

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
*/
  }
  if (lateLoad) {
    onLoad(context)
  }
  htmx.onLoad(onLoad)
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


  $('#auto-play-image-control-button').on('click', (e) => {
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
export const initDraggableThumbnails = context => {
  let elem = undefined
  let released = false
  const handler = evt => {
    if (!released || !evt.detail.elt.parentElement.attributes.getNamedItem("data-active")) {
        console.log("preventing", evt)
        evt.preventDefault()
    } else {
        console.log("allowing", evt)
        setTimeout(() => elem.removeEventListener("htmx:confirm", handler), 100)
    }
  }
  $('#fi-thumbnail-carousel-images').draggable({
    axis: 'x',
    drag: (event, ui) => {
      if (!elem) {
          elem = event.target
          console.log("installing htmx:confirm handler", elem)
          elem.addEventListener("htmx:confirm", handler)
      }
      moveTimelineCoin(ui.position.left, true)
    },
    stop: (event, ui) => {
      dropTimelineCoin(ui.position.left)
      released = true
      htmx.trigger('#fi-thumbnail-carousel-images li[data-active] a', "click")
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
  //console.log({numThumbnails, currentPosition, preItemNum})

  if(drag && numThumbnails - currentPosition < 20) {
    const form = $('#fi-thumbnail-carousel-images').closest("form").get(0)
    form.querySelector("[name='forward']").value = 1
    form.setAttribute("hx-swap", "beforeend")

    const child = form.querySelector("#fi-thumbnail-carousel-images li:last-child")
    const lastFI = child.getAttribute("data-fi")
    const offset = $(child).position().left
    const width = $(child).outerWidth()

    form.querySelector("[name='offset']").value = offset
    form.querySelector("[name='width']").value = width

    form.querySelector("[name='id']").value = lastFI
    htmx.trigger("#fi-thumbnail-carousel-images", "kronofoto:loadThumbnails")
  }
  else if(drag && currentPosition < 20) {
    /* copy/pasted code */
    const form = $('#fi-thumbnail-carousel-images').closest("form").get(0)
    form.setAttribute("hx-swap", "afterbegin")
    form.querySelector("[name='forward']").value = ""
    const child = form.querySelector("#fi-thumbnail-carousel-images li:first-child")
    const lastFI = child.getAttribute("data-fi")
    const offset = $(child).position().left
    const width = $(child).outerWidth()

    form.querySelector("[name='offset']").value = offset
    form.querySelector("[name='width']").value = width
    form.querySelector("[name='id']").value = lastFI
    htmx.trigger("#fi-thumbnail-carousel-images", "kronofoto:loadThumbnails")
  }

  $('#fi-thumbnail-carousel-images li').removeAttr('data-active')
  $('#fi-thumbnail-carousel-images li:nth-child('+ currentPosition +')').attr('data-active', '')
}

let moreThumbnailsLoading = false


export const dropTimelineCoin = (deltaX) => {
  let width = $('#fi-thumbnail-carousel-images li').outerWidth()
  let quantizedX = (Math.round(deltaX / width))
  let itemNum = quantizedX
  $('#fi-thumbnail-carousel-images').css({left: itemNum * width})
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
    let $nextLi = $activeLi.prevAll().eq(numToZip)
    htmx.trigger($nextLi.find('a').get(0), 'click')
  }
  return false
}

export const timelineZipForward = () => {
  if(timelineCrawlForwardInterval == null) { // only zip if we're not already crawling
    let numToZip = Math.floor((getNumVisibleTimelineTiles() - 0.5))
    let $activeLi = $('#fi-thumbnail-carousel-images li[data-active]')
    let $nextLi = $activeLi.nextAll().eq(numToZip)
    //gotoTimelinePosition(numToZip)
    htmx.trigger($nextLi.find('a').get(0), 'click')
  }
  return false
}

export const timelineForward = () => {
  gotoTimelinePosition(1)
}

export const timelineBackward = () => {
  gotoTimelinePosition(-1)
}

export const timelineCrawlForward = evt => {
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
    htmx.trigger('#fi-thumbnail-carousel-images li[data-active] a', "click")
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
    htmx.trigger('#fi-thumbnail-carousel-images li[data-active] a', "click")
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
