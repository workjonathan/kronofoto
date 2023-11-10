"use strict";

import {trigger} from "./utils"
import timeline from "./timeline";
import $ from "jquery"
import ClipboardActionCopy from 'clipboard/src/actions/copy'
import 'jquery-ui-pack'

// Foundation
import { Foundation } from 'foundation-sites/js/foundation.core';
import * as CoreUtils from 'foundation-sites/js/foundation.core.utils';
import { Motion, Move } from 'foundation-sites/js/foundation.util.motion';
import { Touch } from 'foundation-sites/js/foundation.util.touch';
import { Toggler } from 'foundation-sites/js/foundation.toggler';
import { Tooltip } from 'foundation-sites/js/foundation.tooltip';
import { Box } from 'foundation-sites/js/foundation.util.box';
import { MediaQuery } from 'foundation-sites/js/foundation.util.mediaQuery';


let timelineCrawlForwardInterval = null
let timelineCrawlForwardTimeout = null
let timelineCrawlBackwardInterval = null
let timelineCrawlBackwardTimeout = null
var timelineInstance = null

$.fn.extend({
    trigger: function triggerHack(eventType, extraParameters) {
        trigger(eventType, extraParameters, this.get(0), true)
    }
})

const toggleListener = context => {
    function toggleListenerImpl() {
        let ids = $(this).data('toggle')
        console.log(ids)
        if (ids) {
            ids.split(" ").forEach(id => {
                const element = $(`#${id}`, context)
                trigger("toggle.zf.trigger", [$(this)], element.get(0), true)
            })
        } else {
            trigger("toggle.zf.trigger", {}, this, true)
        }
    }
    return toggleListenerImpl
}
const addToggleListener = context => {
    context.off("click.zf.trigger", toggleListener(context))
    context.on("click.zf.trigger", '[data-toggle]', toggleListener(context))
}
export const initHTMXListeners = (_htmx, context, {lateLoad=false} = {}) => {
 
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
            gotoTimelinePosition(delta, {context})
        }
    }
  }
  // context here means our root element
  // necessary?
  $(context).on('click', (e) => {
    if (!$('.form--add-tag input').is(":focus")) {
        let $form = $('.form--add-tag input').closest('form')
        $form.removeClass('expanded')
    }
  })

  // context here means our root element and this would probably be simpler with server side templates.
  $(context).on('on.zf.toggler', function(e) {
    if($(e.target).hasClass('gallery__popup')) {
      $('.gallery__popup.expanded:not(#' + $(e.target).attr('id') + ')').removeClass('expanded');
    }
  });


  const onLoad = elem => {
    $(elem).find(".form--add-tag .link--icon").on('click', (e) => {
        let $form = $(e.currentTarget).closest('form')
        $form.addClass('expanded')
        $('input[type=text]', $form).focus()
    })
    // this logic should not be client side
    $(elem).find('[data-save-list]').on('submit', function(e) {
        // Check if logged in
        if ($('#login-btn', context).length) {
            $('#login-btn', context).trigger('click')
            showToast('You must login to continue')
        } else {
            showToast('Updated photo lists')
        }
    })
    // the next three have some broken state.
    $('#overlay', elem).on('click', (e) => {
        htmx.trigger("#hamburger-button", "click")
        $('#overlay', context).fadeOut()
    })
    $('#hamburger-menu', elem).on('off.zf.toggler', (e) => {
        $('#login', context).addClass('collapse')
        $('#overlay', context).fadeIn()
    }).on('on.zf.toggler', (e) => {
        if ($('#login', context).hasClass('collapse')) {
            $('#overlay', context).fadeOut()
        }
    })
    $('#login', elem).on('off.zf.toggler', (e) => {
        $('#hamburger-menu', context).addClass('collapse')
        $('#overlay', context).fadeIn()
    }).on('on.zf.toggler', (e) => {
        if ($('#hamburger-menu', context).hasClass('collapse')) {
            $('#overlay', context).fadeOut()
        }
    })
    $('#auto-play-image-control-button', elem).on('click', (e) => {
        let $btn = e.currentTarget
        $btn.classList.toggle('active')
        if ($btn.classList.contains('active')) {
            autoplayStart($btn)
        } else {
            autoplayStop()
        }
    })
    $(elem).find(".image-control-button--toggle").on('click', (e) => {
        let $btn = $(e.currentTarget)
        $('img', $btn).toggleClass('hide')
    })
    for (const elem2 of elem.querySelectorAll("#follow-zoom-timeline-version")) {
        addZoom(elem2)
    }
    for (const elem2 of elem.querySelectorAll("#backward-zip")) {
        elem2.addEventListener("click", timelineZipBackward(context))
        elem2.addEventListener("mousedown", timelineCrawlBackward(context))
        elem2.addEventListener("mouseup", timelineCrawlBackwardRelease(context))
    }
    if (elem.id == "backward-zip") {
        elem.addEventListener("click", timelineZipBackward(context))
        elem.addEventListener("mousedown", timelineCrawlBackward(context))
        elem.addEventListener("mouseup", timelineCrawlBackwardRelease(context))
    }
    for (const elem2 of elem.querySelectorAll("#forward-zip")) {
        elem2.addEventListener("click", timelineZipForward(context))
        elem2.addEventListener("mousedown", timelineCrawlForward(context))
        elem2.addEventListener("mouseup", timelineCrawlForwardRelease(context))
    }
    if (elem.id == "forward-zip") {
        elem.addEventListener("click", timelineZipForward(context))
        elem.addEventListener("mousedown", timelineCrawlForward(context))
        elem.addEventListener("mouseup", timelineCrawlForwardRelease(context))
    }
    if (elem.querySelectorAll(".photos-timeline").length) {
        timelineInstance = undefined
        initTimeline(context)
    }
    initDraggableThumbnails(context, elem)
    initAutocomplete()
    initNavSearch(elem)
    initPopups(elem)
    if (window.st && elem.querySelectorAll('.sharethis-inline-share-buttons').length) {
        st.initialize()
    }
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
          let html = elem.innerHTML
          // let firstId = $(html).find('li:first-child span').attr('hx-get')
          const carouselImages = elem.parentNode.querySelector('#fi-thumbnail-carousel-images')
          carouselImages.innerHTML = html
          carouselImages.classList.add("dragging")
          carouselImages.style.left = "0px"
          setTimeout(() => {
            carouselImages.classList.remove('dragging')
          }, 100)

          _htmx.process(carouselImages)
          elem.replaceChildren()
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
  _htmx.onLoad(onLoad)
}
export const initFoundation = (context) => {

  Foundation.addToJquery($);
  Foundation.Box = Box;
  Foundation.MediaQuery = MediaQuery;
  Foundation.Motion = Motion;
  Foundation.Move = Move;
  addToggleListener($(context));

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
export const initDraggableThumbnails = (context, newElems) => {
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
  $('#fi-thumbnail-carousel-images', newElems).draggable({
    axis: 'x',
    drag: (event, ui) => {
      if (!elem) {
          elem = event.target
          console.log("installing htmx:confirm handler", elem)
          elem.addEventListener("htmx:confirm", handler)
      }
      moveTimelineCoin(ui.position.left, true, {context})
    },
    stop: (event, ui) => {
      dropTimelineCoin(ui.position.left, {context})
      released = true
      for (const temp of context.querySelectorAll('#fi-thumbnail-carousel-images li[data-active] a')) {
        trigger("click", {}, temp, true)
      }
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

export const autoplayStart = (elem) => {
  window.autoplayTimer = setInterval(elem => {
    if (elem.isConnected) {
        htmx.trigger('#fi-arrow-right', 'click')
    } else {
        clearInterval(window.autoplayTimer)
    }
  }, 5000, elem)
}

export const autoplayStop = () => {
  clearInterval(window.autoplayTimer)
}

export const moveTimelineCoin = (deltaX, drag = true, {context=document} = {}) => {
  if(drag) {
    $('#fi-thumbnail-carousel-images', context).addClass('dragging')
  }
  else {
    $('#fi-thumbnail-carousel-images', context).removeClass('dragging')
  }
  let widthOfThumbnail = $('#fi-thumbnail-carousel-images li', context).outerWidth()
  let preItemNum = $('#fi-thumbnail-carousel-images [data-origin]', context).index()
  let quantizedPositionX = (Math.round(deltaX / widthOfThumbnail) * -1)
  console.log({widthOfThumbnail, preItemNum, quantizedPositionX})
  let currentPosition = preItemNum + quantizedPositionX + 1

  let numThumbnails= $('#fi-thumbnail-carousel-images li', context).length
  //console.log({numThumbnails, currentPosition, preItemNum})

  if(drag && numThumbnails - currentPosition < 20) {
    const form = $('#fi-thumbnail-carousel-images', context).closest("form").get(0)
    form.querySelector("[name='forward']").value = 1
    form.setAttribute("hx-swap", "beforeend")

    const child = form.querySelector("#fi-thumbnail-carousel-images li:last-child")
    const lastFI = child.getAttribute("data-fi")
    const offset = $(child).position().left
    const width = $(child).outerWidth()

    form.querySelector("[name='offset']").value = offset
    form.querySelector("[name='width']").value = width

    form.querySelector("[name='id']").value = lastFI
    trigger("kronofoto:loadThumbnails", {}, $("#fi-thumbnail-carousel-images", context).get(0), true)
  }
  else if(drag && currentPosition < 20) {
    /* copy/pasted code */
    const form = $('#fi-thumbnail-carousel-images', context).closest("form").get(0)
    form.setAttribute("hx-swap", "afterbegin")
    form.querySelector("[name='forward']").value = ""
    const child = form.querySelector("#fi-thumbnail-carousel-images li:first-child")
    const lastFI = child.getAttribute("data-fi")
    const offset = $(child).position().left
    const width = $(child).outerWidth()

    form.querySelector("[name='offset']").value = offset
    form.querySelector("[name='width']").value = width
    form.querySelector("[name='id']").value = lastFI
    trigger("kronofoto:loadThumbnails", {}, $("#fi-thumbnail-carousel-images", context).get(0), true)
  }

  $('#fi-thumbnail-carousel-images li', context).removeAttr('data-active')
  console.log({currentPosition, context})
  $('#fi-thumbnail-carousel-images li:nth-child('+ currentPosition +')', context).attr('data-active', '')
}

let moreThumbnailsLoading = false


export const dropTimelineCoin = (deltaX, {context=document}={}) => {
  let width = $('#fi-thumbnail-carousel-images li', context).outerWidth()
  let quantizedX = (Math.round(deltaX / width))
  let itemNum = quantizedX
  $('#fi-thumbnail-carousel-images', context).css({left: itemNum * width})
}

export const gotoTimelinePosition = (delta, {context=document} = {}) => {
  let width = $('#fi-thumbnail-carousel-images li', context).outerWidth()
  moveTimelineCoin(delta * -1 * width, false, {context})
  dropTimelineCoin(delta * -1 * width, {context})
}
export const timelineZipBackward = context => () => {
  if(timelineCrawlBackwardInterval == null) { // only zip if we're not already crawling
    let numToZip = Math.floor((getNumVisibleTimelineTiles({context}) - 0.5))
    let $activeLi = $('#fi-thumbnail-carousel-images li[data-active]', context)
    let $nextLi = $activeLi.prevAll().eq(numToZip)
    trigger("click", {}, $nextLi.find('a').get(0), true)
  }
  return false
}

export const timelineZipForward = context => () => {
  if(timelineCrawlForwardInterval == null) { // only zip if we're not already crawling
    let numToZip = Math.floor((getNumVisibleTimelineTiles({context}) - 0.5))
    let $activeLi = $('#fi-thumbnail-carousel-images li[data-active]', context)
    let $nextLi = $activeLi.nextAll().eq(numToZip)
    //gotoTimelinePosition(numToZip)
    trigger("click", {}, $nextLi.find('a').get(0), true)
  }
  return false
}

export const timelineCrawlForward = context => evt => {
  timelineCrawlForwardTimeout = setTimeout(() => {
    let currentPosition = $('#fi-thumbnail-carousel-images', context).position().left
    timelineCrawlForwardInterval = setInterval(() => {
      if(canCrawlForward({context})) {
        currentPosition -= 20
        $('#fi-thumbnail-carousel-images', context).css('left', currentPosition)
        moveTimelineCoin(currentPosition, true, {context})
      }
    }, 50)
  }, 500)
}

const canCrawlForward = ({context=document} = {}) => {
  let length = $('#fi-thumbnail-carousel-images [data-active]', context).nextAll().length
  return length > 10
}

export const timelineCrawlForwardRelease = context => () => {
  clearTimeout(timelineCrawlForwardTimeout)
  timelineCrawlForwardTimeout = null
  if(timelineCrawlForwardInterval) { // only execute when we're crawling
    clearInterval(timelineCrawlForwardInterval)
    dropTimelineCoin($('#fi-thumbnail-carousel-images', context).position().left)
    trigger("click", {}, $('#fi-thumbnail-carousel-images li[data-active] a', context).get(0), true)
    setTimeout(() => {
      timelineCrawlForwardInterval = null
    }, 750)
  }
}

export const timelineCrawlBackward = context => () => {
  timelineCrawlBackwardTimeout = setTimeout(() => {
    let currentPosition = $('#fi-thumbnail-carousel-images', context).position().left
    timelineCrawlBackwardInterval = setInterval(() => {
      if(canCrawlBackward({context})) {
        currentPosition += 20
        $('#fi-thumbnail-carousel-images', context).css('left', currentPosition)
        moveTimelineCoin(currentPosition, true, {context})
      }
    }, 50)
  }, 500)
}

const canCrawlBackward = ({context=document}={}) => {
  let length = $('#fi-thumbnail-carousel-images [data-active]', context).prevAll().length
  return length > 10
}

export const timelineCrawlBackwardRelease = context => () => {
  clearTimeout(timelineCrawlBackwardTimeout)
  timelineCrawlBackwardTimeout = null
  if(timelineCrawlBackwardInterval) { // only execute when we're crawling
    clearInterval(timelineCrawlBackwardInterval)
    dropTimelineCoin($('#fi-thumbnail-carousel-images', context).position().left)
    trigger("click", {}, $('#fi-thumbnail-carousel-images li[data-active] a', context).get(0), true)
    setTimeout(() => {
      timelineCrawlBackwardInterval = null
    }, 750)
  }
}

const getNumVisibleTimelineTiles = ({context=document}={}) => {
  let widthOfTimeline = $('#fi-image', context).width() // assumes the timeline is the same width as gallery image
  let $li = $('#fi-thumbnail-carousel-images li[data-active]', context)
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
