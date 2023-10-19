"use strict";

import {enableMarkerDnD} from "./drag-drop.js"
import HTMX from "./htmx.js"
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

export class FortepanInstance {
  timelineInstance = null
  // HTMX = _HTMX
  htmx = null
  timelineCrawlForwardInterval = null
  timelineCrawlForwardTimeout = null
  timelineCrawlBackwardInterval = null
  timelineCrawlBackwardTimeout = null
  moreThumbnailsLoading = false
  gettingMoreThumbnailsLeft = false
  gettingMoreThumbnailsRight = false
  context = null
  root = null
  dragOffset = false
  lastActiveThumbnail = null
  stylesReady = false
  htmxLoaded = false

  constructor(context) {
    this.context = context;
    this.root = context.querySelector("#app")
  }

  init(options) {
    let self = this
    if(options && typeof options.embedded !== 'undefined' && options.embedded == true) {

    }
    else {
      self.stylesReady = true
      self.tryInitTimline()
      self.initHTMXListeners(self.context, self.root)
      self.initFoundation(self.context)
      self.initGalleryNav()
      self.initClipboardJS(self.context)
      self.initEventHandlers(self.context)
      self.installButtons(self.context)(self.root)
      self.initPopups()
      self.initShareThis()
      self.initDraggableThumbnails()
      self.initNavSearch()
      self.initAutocomplete()
    }
  }

  jquery(sel, _context) {
    var self = this
    _context = _context || self.context
    return $(sel, _context)
  }

  // initJQuery(context) {
  //
  //   let self = this
  //   var initjQuery = $.fn.init
  //   self.jQuery.fn.init = function (s, c, r) {
  //     c = c || context
  //     return new initjQuery(s, c, r)
  //   };
  //   $.fn.init = self.jQuery.fn.init
  // }

  tryInitTimline() {
    let self = this
    if(self.stylesReady && self.htmxLoaded && self.jquery('.photos-timeline').length && !self.jquery('.photos-timeline').hasClass('initialized')) {
      self.jquery('.photos-timeline').addClass('initialized')
      self.initTimeline()
    }
  }

  initShareThis() {
    let self = this
    setInterval(() => {
      if($('.sharethis-inline-share-buttons > div').length == 0 && window.__sharethis__ && typeof window.__sharethis__.initialize !== 'undefined') {
        window.__sharethis__.initialize()
      }
    }, 1000)
  }

  initHTMXListeners(context, root) {
    let self = this
    self.htmx = HTMX(context)
    self.htmx.process(self.root)
    self.context.htmx = self.htmx

    self.htmx.onLoad((e) => {

      // self.htmx.process(self.root)
      self.htmxLoaded = true
      self.context.onceInitHTMXListeners = false
      self.tryInitTimline()
      self.initPopups()
      self.initDraggableThumbnails()

      // self.tryInitTimline()
      self.initHTMXListeners(self.context, self.root)
      self.initFoundation(self.context)
      // self.initGalleryNav()
      self.initClipboardJS(self.context)
      self.initEventHandlers(self.context)
      self.installButtons(self.context)(self.root)
      // self.initPopups()
      self.initShareThis()
      // self.initDraggableThumbnails()
      self.initNavSearch()
      self.initAutocomplete()


      if (self.jquery('#fi-image-preload img').length && !self.jquery('#fi-image-preload img').data('loaded')) {
        self.jquery('#fi-image-preload img').data('loaded', true)
        let url = self.jquery('#fi-image-preload img').attr('src')
        const image = new Image();
        image.src = url;
        image.onload = () => {
          let html = self.jquery('#fi-image-preload').html()
          self.jquery('#fi-image').html(html)
          self.jquery('#fi-image-preload').empty()
        }
      }

    })

    return self.htmx

  }

  initFoundation(context) {
    let self = this
    window.kfCurrentContext = self.context
    Foundation.addToJquery($);
    Foundation.Box = Box;
    Foundation.MediaQuery = MediaQuery;
    Foundation.Motion = Motion;
    Foundation.Move = Move;
    Triggers.Initializers.addToggleListener(self.jquery(context));

    Foundation.plugin(Toggler, 'Toggler');
    Foundation.plugin(Tooltip, 'Tooltip');

    self.jquery(context).foundation()

  }

  initTimeline() {
    let self = this
    self.timelineInstance = new timeline();
    self.jquery('.photos-timeline').each( (i, e) => {
      self.timelineInstance.connect(e, self.context, self.jquery);
    });
    return self.timelineInstance
  }

  initEventHandlers(context) {
    let self = this

    self.context.addEventListener('htmx:pushedIntoHistory', (e) => self.initPopups(e))

    self.context.addEventListener('htmx:pushedIntoHistory', (e) => self.initNavSearch(e))

    self.jquery(context).on('click', '.form--add-tag .link--icon', (e) =>{
      let $form = self.jquery(e.currentTarget).closest('form')
      $form.addClass('expanded')
      self.jquery('input[type=text]', $form).focus()
    })

    self.jquery(context).on('click', (e) => {
      if (!self.jquery('.form--add-tag input').is(":focus")) {
        let $form = self.jquery('.form--add-tag input').closest('form')
        $form.removeClass('expanded')
        setTimeout(() => { self.jquery('.form--add-tag input').val('') }, 0)
      }
    })

    self.jquery(context).on('change keydown paste input', 'input', (e) => {
      if (self.jquery(e.currentTarget).closest('form')) {
        self.jquery(e.currentTarget).closest('form').find('[data-enable-on-modify]').removeAttr('disabled')
      }
    })

    self.jquery(context).on('on.zf.toggler', (e) => {
      if (self.jquery(e.target).hasClass('gallery__popup')) {
        self.jquery('.gallery__popup.expanded:not(#' + self.jquery(e.target).attr('id') + ')').removeClass('expanded');
      }
    });

    self.jquery(context).on('submit', '#add-to-list-popup form', (e)=> {
      let self = this
      // Check if logged in
      if (self.jquery('#login-btn').length) {
        self.jquery('#login-btn').trigger('click')
        self.showToast('You must login to continue')
      } else {
        self.showToast('Updated photo lists')
      }
    })

    self.jquery('#overlay').on('click', (e) => {
      self.jquery('#login').addClass('collapse')
      self.jquery('#hamburger-menu').addClass('collapse')
      self.jquery('#overlay').fadeOut()
    })

    self.jquery('#hamburger-menu').on('off.zf.toggler', (e) => {
      self.jquery('#login').addClass('collapse')
      self.jquery('#overlay').fadeIn()
    }).on('on.zf.toggler', (e) => {
      if (self.jquery('#login').hasClass('collapse')) {
        self.jquery('#overlay').fadeOut()
      }
    })

    self.jquery('#login').on('off.zf.toggler', (e) => {
      self.jquery('#hamburger-menu').addClass('collapse')
      self.jquery('#overlay').fadeIn()
    }).on('on.zf.toggler', (e) => {
      if (self.jquery('#hamburger-menu').hasClass('collapse')) {
        self.jquery('#overlay').fadeOut()
      }
    })

    // self.jquery(context).click(function(event) {
    //
    //   //~TESTING LINE
    //   //console.log(event.target.className)
    //
    //   var classOfThingClickedOn = event.target.className
    //
    //   //~TESTING LINE
    //   //console.log(self.jquery('.search-form').find('*'))
    //
    //   //creates a jQuery collection of the components of the search menu EXCEPT for the menu itself
    //   var $descendantsOfSearchForm = self.jquery('.search-form').find('*')
    //
    //   //---creates an array of all components of the search menu dropdown---
    //   //adds the search menu itself to the array
    //   var componentsOfSearchMenuArray = ['search-form']
    //
    //   //adds the class of all the components of the search menu to the array
    //   $descendantsOfSearchForm.each(function(index) {
    //     //checks to make sure the class isn't already in the array
    //     if ($.inArray(self.className, componentsOfSearchMenuArray) == -1) {
    //       //adds the class to the array
    //       componentsOfSearchMenuArray.push(self.className)
    //     }
    //   })
    //
    //   //~TESTING LINES
    //   //console.log(componentsOfSearchMenuArray)
    //   //console.log('Class:'+'"'+classOfThingClickedOn+'"')
    //   //console.log(componentsOfSearchMenuArray.includes(classOfThingClickedOn))
    //
    //   //if the search menu is open and the user clicks on something outside of the menu, close the menu
    //   if (self.jquery(event.target).attr('id') != 'search-box' && self.jquery('.search-form').is(":visible") && (!(componentsOfSearchMenuArray.includes(classOfThingClickedOn)))) {
    //     collapseNavSearch()
    //   }
    //   //if the user clicks on the carrot or the small invisible box behind it, toggle the menu
    //   else if (classOfThingClickedOn == 'search-options' || classOfThingClickedOn == 'carrot') {
    //     // self.jquery('.search-form').toggle()
    //   }
    // })

    self.jquery(context).on('click', '#forward-zip', (e) => self.timelineZipForward(e))
    self.jquery(context).on('click', '#forward', (e) => self.timelineForward(e))
    self.jquery(context).on('mousedown', '#forward-zip', (e) => self.timelineCrawlForward(e))
    self.jquery(context).on('mouseup', '#forward-zip', (e) => self.timelineCrawlForwardRelease(e))
    self.jquery(context).on('click', '#backward-zip', (e) => self.timelineZipBackward(e))
    self.jquery(context).on('click', '#backward', (e) => self.timelineBackward(e))
    self.jquery(context).on('mousedown', '#backward-zip', (e) => self.timelineCrawlBackward(e))
    self.jquery(context).on('mouseup', '#backward-zip', (e) => self.timelineCrawlBackwardRelease(e))
    self.jquery(context).on('click', '#fi-arrow-right', (e) => self.timelineForward(e))
    self.jquery(context).on('click', '#fi-arrow-left', (e) => self.timelineBackward(e))
    self.jquery(context).on('click', '#fi-thumbnail-carousel-images li span', (e)=> {
      let currentIndex = self.jquery('#fi-thumbnail-carousel-images [data-active]').index()
      let clickedIndex = self.jquery(e.currentTarget).parent().index()
      let delta = clickedIndex - currentIndex
      self.gotoTimelinePosition(delta)
    })


    self.jquery(context).on('keydown', (event)=> {
      var keyCode = event.which || event.keyCode;

      // Handle forward arrow key (Right Arrow or Down Arrow)
      if (keyCode === 39) {
        // Perform the action for the forward arrow key
        self.timelineForward()
      }

      // Handle back arrow key (Left Arrow or Up Arrow)
      if (keyCode === 37) {
        // Perform the action for the back arrow key
        self.timelineBackward()
      }
    });

    self.jquery(context).on('click', '#auto-play-image-control-button', (e) => {
      let $btn = self.jquery('#auto-play-image-control-button')
      $btn.toggleClass('active')
      if ($btn.hasClass('active')) {
        self.autoplayStart()
      } else {
        self.autoplayStop()
      }
    })

    self.jquery(context).on('click', '.image-control-button--toggle', (e) => {
      let $btn = self.jquery(e.currentTarget)
      self.jquery('img', $btn).toggleClass('hide')
    })

  }

  initClipboardJS() {
    let self = this
    self.jquery(self.root).on('click', '.copy-button', (e) => {
      let target = self.jquery(e.currentTarget).attr('data-clipboard-target')
      let text = self.jquery(target).val()
      ClipboardActionCopy(text)
      self.jquery(target).select()
      self.jquery(target)[0].setSelectionRange(0, 999999)
    })
  }

  initAutocomplete() {
    let self = this
    self.jquery('#tag-search').autocomplete({
      source: '/tags',
      minLength: 2,
    })
  }

  initDraggableThumbnails() {
    let self = this
    window.$ = self.jquery
    if (!self.jquery('#fi-thumbnail-carousel-images [data-origin]').length) {
      self.jquery('#fi-thumbnail-carousel-images [data-active]').attr('data-origin', '')
    }
    self.jquery('#fi-thumbnail-carousel-images').draggable({
      axis: 'x',
      start: (event, ui) => {
        self.lastActiveThumbnail = self.jquery('#fi-thumbnail-carousel-images [data-active]')
        self.dragOffset = self.jquery('#fi-thumbnail-carousel-images').position().left
      },
      drag: (event, ui) => {
        let offset = parseInt(self.jquery('#fi-thumbnail-carousel-images').attr('data-offset')) || 0
        if(offset) {
          self.jquery('#fi-thumbnail-carousel-images').attr('data-offset', 0)
        }
        ui.position.left = ui.position.left - offset
        self.moveTimelineCoin(ui.position.left)
      },
      stop: (event, ui) => {
        self.dragOffset = false
        self.lastActiveThumbnail = null
        let offset = parseInt(self.jquery('#fi-thumbnail-carousel-images').attr('data-offset')) || 0
        if(offset > 0) {
          self.jquery('#fi-thumbnail-carousel-images').attr('data-offset', 0)
        }
        ui.position.left = ui.position.left - offset
        // self.htmx.trigger(self.jquery('#fi-thumbnail-carousel-images li[data-active] span').get(0), 'manual')
        self.dropTimelineCoin(ui.position.left)
      }
    })
    setTimeout(() => {
      self.jquery('#fi-thumbnail-carousel-images').removeClass('dragging')
      if (!self.jquery('#fi-thumbnail-carousel-images [data-origin]').length) {
        self.jquery('#fi-thumbnail-carousel-images [data-active]').attr('data-origin', '')
      }
    }, 100)
  }

  moveTimelineCoinAbsolute(pos, drag) {
    let self = this

    self.moveTimelineCoin(deltaX, drag)
  }

  initPopups() {
    let self = this
    let popups = ['add-to-list-popup', 'download-popup', 'share-popup']
    popups.forEach((e,i) => {
      if(self.jquery('#' + e).find('.photo-menu-popup__wrapper').length && self.jquery('#' + e).find('.photo-menu-popup__wrapper > div').length == 0) {
        let photoId = self.jquery('#' + e + '[data-photo-id]').data('photo-id')
        let loadedPhotoId = self.jquery('#' + e + ' [data-photo-id]').data('photo-id')
        if(photoId != loadedPhotoId) {
          let $placeholder = self.jquery('<div/>').attr('data-photo-id', photoId)
          self.jquery('#' + e + ' .photo-menu-popup__wrapper').append($placeholder)
          self.htmx.trigger(self.jquery('#' + e + ' .photo-menu-popup__wrapper').get(0), 'manual')
        }
      }
    })

    self.jquery('#app').foundation()
  }

  collapseNavSearch() {
    let self = this
    self.jquery('#search-box-container').removeClass('expanded')
    self.jquery('.search-form').hide()
    self.jquery('#search-box').val('')
    self.jquery('.search-icon').css('filter', 'none')
    self.jquery('.carrot').css('filter', 'none')
    self.jquery('#search-box').removeClass('placeholder-light').css('color', '#333')
  }

  expandNavSearch() {
    // let $ = self.jQuery
    let self = this
    self.jquery('#search-box-container').addClass('expanded')
    self.jquery('.search-form').show()
    self.jquery('.search-icon').css('filter', 'brightness(0) invert(1)')
    self.jquery('.carrot').css('filter', 'brightness(0) invert(1)')
    self.jquery('#search-box').addClass('placeholder-light').css('color', 'white')
  }

  initNavSearch(context) {
    let self = this
    self.jquery('.search-form__clear-btn').click((e) => {
      e.preventDefault();
      self.jquery('#search-box').val('')
      self.jquery('.search-form input[type=text]').val('')
      self.jquery('.search-form select').val('')
    })
    self.jquery('#search-box').click((e) => self.expandNavSearch(e))
    self.jquery('#search-box').on('keydown', (e) => {
      if (e.which === 13) {
        e.preventDefault()
        self.jquery('#search-box').closest('form').submit()
      }
    })
    self.jquery('#search-box-container .close-icon').click((e) => self.collapseNavSearch(e))
  }

  showToast(message) {
    let self = this
    let content = self.jquery('#toast-template').html()
    let $message = self.jquery(content)
    $message.prepend('<p>' + message + '</p>')
    self.jquery('#messages').append($message)
    setTimeout(() => {
      $message.fadeOut(() => {
        $message.remove()
      })
    }, 5000)
  }

  autoplayStart() {
    let self = this
    window.autoplayTimer = setInterval(() => {
      self.htmx.trigger('#fi-arrow-right', 'click')
    }, 5000)
  }

  autoplayStop() {
    let self = this
    clearInterval(window.autoplayTimer)
  }

  moveTimelineCoin(deltaX) {
    let self = this
    if (self.dragOffset !== false) {
      self.jquery('#fi-thumbnail-carousel-images').addClass('dragging')
    } else {
      self.jquery('#fi-thumbnail-carousel-images').removeClass('dragging')
    }

    let thumbnailWidth = self.jquery('#fi-thumbnail-carousel-images li').outerWidth()
    let index = self.jquery('#fi-thumbnail-carousel-images [data-active]').index()
    let newIndex = Math.round(index - (deltaX / thumbnailWidth) + 1)
    if(self.dragOffset !== false) {
      let dragOffsetIndex = self.jquery(self.lastActiveThumbnail).index()
      self.jquery('.header-text').text(dragOffsetIndex + ((self.dragOffset - deltaX) != 0 ? Math.round((self.dragOffset - deltaX) / thumbnailWidth) : 0) + 1)
      self.jquery('.collection-name').text(self.dragOffset)
      newIndex = dragOffsetIndex + ((self.dragOffset - deltaX) != 0 ? Math.round((self.dragOffset - deltaX) / thumbnailWidth) : 0) + 1 //dragOffsetIndex - Math.round((self.dragOffset + deltaX) / thumbnailWidth) + 1
    }
    let newItem = self.jquery('#fi-thumbnail-carousel-images li:nth-child('+newIndex+')')
    let contextWidth = self.root.offsetWidth

    let numPrev = self.jquery(newItem).prevAll().length
    let desiredThumbBuffer = 0.75 * contextWidth / thumbnailWidth
    let numNext = self.jquery(newItem).nextAll().length
    if (numPrev < desiredThumbBuffer) {
      self.getMoreThumbnailsLeft()
    } else if (numNext < desiredThumbBuffer) {
      self.getMoreThumbnailsRight()
    }

    self.jquery('#fi-thumbnail-carousel-images li').removeAttr('data-active')
    self.jquery(newItem).attr('data-active', '')
  }

  getMoreThumbnailsRight() {
    let self = this
    if(!self.gettingMoreThumbnailsRight) {
      self.gettingMoreThumbnailsRight = true
      let form = self.jquery('#thumbnail-request').get(0)
      let formData = new FormData(form)
      let targetId = self.jquery('#fi-thumbnail-carousel-images li:last-child span').attr('hx-get')
      targetId = parseInt(targetId.split('/')[targetId.split('/').length-1].replace(/[^0-9]/g, ''))
      formData.set('id', targetId)
      formData.set('forward', 'True')
      var headers = {
        'Hx-Request': true,
        'Hx-Target': 'thumbnail-request',
        'Hx-Trigger': 'thumbnail-request'
      }
      let action = form.getAttribute('hx-get') + '?' + (new URLSearchParams(formData))
      fetch(action, {
        method: 'GET',
        headers: headers,
      })
        .then(response => response.text())
        .then(data => {
          // Request was successful, handle the response here
          self.gettingMoreThumbnailsRight = false
          self.jquery('#fi-thumbnail-carousel-images').append(data)
          self.htmx.process(self.jquery('#fi-thumbnail-carousel-images').get(0))
        })
        .catch(error => {
          // Handle any errors that occurred during the fetch
          console.error('Error:', error)
        });
    }
  }

  getMoreThumbnailsLeft() {
    let self = this
    if(!self.gettingMoreThumbnailsLeft) {
      self.gettingMoreThumbnailsLeft = true
      let form = self.jquery('#thumbnail-request').get(0)
      let formData = new FormData(form)
      let targetId = self.jquery('#fi-thumbnail-carousel-images li:first-child span').attr('hx-get')
      targetId = parseInt(targetId.split('/')[targetId.split('/').length-1].replace(/[^0-9]/g, ''))
      formData.set('id', targetId)
      formData.set('forward', 'False')
      var headers = {
        'Hx-Request': true,
        'Hx-Target': 'thumbnail-request',
        'Hx-Trigger': 'thumbnail-request'
      }
      let action = form.getAttribute('hx-get') + '?' + (new URLSearchParams(formData))
      fetch(action, {
        method: 'GET',
        headers: headers,
      })
          .then(response => response.text())
          .then(data => {
            self.gettingMoreThumbnailsLeft = false
            let width = self.jquery('#fi-thumbnail-carousel-images li').outerWidth()

            let currentPosition = self.jquery('#fi-thumbnail-carousel-images').position().left
            self.jquery('#fi-thumbnail-carousel-images').addClass('block-transition')
            setTimeout(() => {
              self.jquery('#fi-thumbnail-carousel-images').prepend(data)

              let dragging = false
              if(self.jquery('#fi-thumbnail-carousel-images').hasClass('dragging')) {
                dragging = true
              }

              if(dragging) {
                self.jquery('#fi-thumbnail-carousel-images').trigger('mouseup.draggable')
              }

              self.jquery('#fi-thumbnail-carousel-images').css({left: currentPosition - (40 * width)})

              // Let jquery draggable plugin know we've moved stuff so that it can apply an offset mid-drag
              if(self.jquery('#fi-thumbnail-carousel-images').hasClass('dragging')) {
                self.dragOffset = self.dragOffset - (40*width) //self.jquery('#fi-thumbnail-carousel-images').position().left
              }

              setTimeout(() => {
                self.jquery('#fi-thumbnail-carousel-images').removeClass('block-transition')
              }, 0)
            }, 0)


            self.htmx.process(self.jquery('#fi-thumbnail-carousel-images').get(0))
          })
          .catch(error => {
            // Handle any errors that occurred during the fetch
            console.error('Error:', error)
          });
    }
  }

  dropTimelineCoin(deltaX) {
    let self = this
    let coin = self.jquery('#fi-thumbnail-carousel-images [data-active]')

    let contextWidth = self.root.offsetWidth
    let contextWidthHalf = self.root.offsetWidth / 2
    let thumbnailWidth = self.jquery('#fi-thumbnail-carousel-images li').outerWidth()
    let quantizedX = (Math.round(deltaX / thumbnailWidth))
    let coinPosition = coin.get(0).getBoundingClientRect().left + (thumbnailWidth/2);
    let coinOffset = contextWidthHalf - coinPosition
    // let offset = parseInt(self.jquery('#fi-thumbnail-carousel-images').attr('data-offset')) || 0
    // if(offset) {
    //   self.jquery('#fi-thumbnail-carousel-images').attr('data-offset', 0)
    // }
    let currentPosition = self.jquery('#fi-thumbnail-carousel-images').position().left
    // let newPosition = offset + (itemNum * width) + currentPosition
    let newPosition = coinOffset + currentPosition
    self.jquery('#fi-thumbnail-carousel-images').css({left: newPosition})
    self.htmx.trigger(self.jquery('#fi-thumbnail-carousel-images li[data-active] span').get(0), 'manual')
  }

  // refreshThumbnails() {
  //   let self = this
  //
  //   // Do we need thumbnails?
  //   // Which direction do we need more thumbnails?
  //
  //   if (self.jquery('#fi-preload-zone li').length) {
  //     let html = self.jquery('#fi-preload-zone').html()
  //     let firstId = self.jquery(html).find('li:first-child span').attr('hx-get')
  //     self.jquery('#fi-thumbnail-carousel-images').html(html)
  //     let $after = self.jquery('#fi-thumbnail-carousel-images li span[hx-get="' + firstId + '"]').nextAll()
  //     self.jquery('#fi-thumbnail-carousel-images').append($after)
  //     //   self.jquery('#fi-thumbnail-carousel-images').addClass('dragging')
  //     //   self.jquery('#fi-thumbnail-carousel-images').css('left', '0px')
  //     //   setTimeout(() => {
  //     //     self.jquery('#fi-thumbnail-carousel-images').removeClass('dragging')
  //     //   }, 100)
  //     self.htmx.process(self.jquery('#fi-thumbnail-carousel-images').get(0))
  //     self.jquery('#fi-preload-zone').empty()
  //   }
  // }

  gotoTimelinePosition(delta) {
    let self = this
    let index = self.jquery('#fi-thumbnail-carousel-images [data-active]').index()
    let targetIndex = index + delta
    if(self.jquery('#fi-thumbnail-carousel-images li:nth-child('+targetIndex+')').length) {
      let width = self.jquery('#fi-thumbnail-carousel-images li').outerWidth()
      self.moveTimelineCoin(delta * -1 * width, false)
      self.dropTimelineCoin(delta * -1 * width)
    }
  }

  timelineZipBackward() {
    let self = this
    if (self.timelineCrawlBackwardInterval == null) { // only zip if we're not already crawling
      let numToZip = Math.floor((self.getNumVisibleTimelineTiles() - 0.5))
      // let $activeLi = self.jquery('#fi-thumbnail-carousel-images li[data-active]')
      // let $nextLi = $activeLi.nextAll().eq(numToZip)
      self.gotoTimelinePosition(numToZip * -1)
      // htmx.trigger($nextLi.find('a').get(0), 'manual')
    }
    return false
  }

  timelineZipForward() {
    let self = this
    if (self.timelineCrawlForwardInterval == null) { // only zip if we're not already crawling
      let numToZip = Math.floor((self.getNumVisibleTimelineTiles() - 0.5))
      let $activeLi = self.jquery('#fi-thumbnail-carousel-images li[data-active]')
      let $nextLi = $activeLi.prevAll().eq(numToZip)
      self.gotoTimelinePosition(numToZip)
      // htmx.trigger($nextLi.find('a').get(0), 'manual')
    }
    return false
  }

  timelineForward() {
    let self = this
    self.gotoTimelinePosition(1)
  }

  timelineBackward() {
    let self = this
    self.gotoTimelinePosition(-1)
  }

  timelineCrawlForward() {
    let self = this
    self.timelineCrawlForwardTimeout = setTimeout(() => {
      let currentPosition = self.jquery('#fi-thumbnail-carousel-images').position().left
      self.timelineCrawlForwardInterval = setInterval(() => {
        if (self.canCrawlForward()) {
          currentPosition -= 20
          self.jquery('#fi-thumbnail-carousel-images').css('left', currentPosition)
          self.moveTimelineCoin(currentPosition)
        }
      }, 50)
    }, 500)
  }

  canCrawlForward() {
    let self = this
    let length = self.jquery('#fi-thumbnail-carousel-images [data-active]').nextAll().length
    return length > 10
  }

  timelineCrawlForwardRelease() {
    let self = this
    clearTimeout(self.timelineCrawlForwardTimeout)
    self.timelineCrawlForwardTimeout = null
    if (self.timelineCrawlForwardInterval) { // only execute when we're crawling
      clearInterval(self.timelineCrawlForwardInterval)
      self.dropTimelineCoin(self.jquery('#fi-thumbnail-carousel-images').position().left)
      setTimeout(() => {
        self.timelineCrawlForwardInterval = null
      }, 750)
    }
  }

  timelineCrawlBackward() {
    let self = this
    self.timelineCrawlBackwardTimeout = setTimeout(() => {
      let currentPosition = self.jquery('#fi-thumbnail-carousel-images').position().left
      self.timelineCrawlBackwardInterval = setInterval(() => {
        if (self.canCrawlBackward()) {
          currentPosition += 20
          self.jquery('#fi-thumbnail-carousel-images').css('left', currentPosition)
          self.moveTimelineCoin(currentPosition)
        }
      }, 50)
    }, 500)
  }

  canCrawlBackward() {
    let self = this
    let length = self.jquery('#fi-thumbnail-carousel-images [data-active]').prevAll().length
    return length > 10
  }

  timelineCrawlBackwardRelease() {
    let self = this
    clearTimeout(self.timelineCrawlBackwardTimeout)
    self.timelineCrawlBackwardTimeout = null
    if (self.timelineCrawlBackwardInterval) { // only execute when we're crawling
      clearInterval(self.timelineCrawlBackwardInterval)
      self.dropTimelineCoin(self.jquery('#fi-thumbnail-carousel-images').position().left)
      setTimeout(() => {
        self.timelineCrawlBackwardInterval = null
      }, 750)
    }
  }

  getNumVisibleTimelineTiles() {
    let self = this
    // let $ = self.jQuery
    let widthOfTimeline = self.jquery('#fi-image').width() // assumes the timeline is the same width as gallery image
    let $li = self.jquery('#fi-thumbnail-carousel-images li[data-active]')
    let widthOfTile = $li.outerWidth()
    return Math.floor(widthOfTimeline / widthOfTile)
  }

  initGalleryNav() {
    let self = this
    let hideGalleryTimeout = null;
    // When the mouse moves
    self.context.addEventListener('mousemove', () => {
      self.showGalleryNav()
      if (hideGalleryTimeout)
        clearTimeout(hideGalleryTimeout)
      hideGalleryTimeout = setTimeout(() => { self.hideGalleryNav() }, 5000)
    })
  }

  hideGalleryNav() {
    let self = this
    self.jquery('.gallery').addClass('hide-nav')
  }

  showGalleryNav() {
    let self = this
    self.jquery('.gallery').removeClass('hide-nav')
  }

  toggleLogin(evt) {
    let self = this
    const el = document.querySelector('#login');
    self.toggleElement(el);
  }

  toggleMenu(evt) {
    let self = this
    // if(!self.jquery('.hamburger').hasClass('is-active')) {
    //   self.jquery('.hamburger').addClass('is-active')
    //   self.jquery('.hamburger-menu').removeClass('collapse')
    //   self.jquery('body').addClass('menu-expanded')
    //   self.jquery('.overlay').fadeIn()
    // }
    // else {
    //   self.jquery('.hamburger').removeClass('is-active')
    //   self.jquery('.hamburger-menu').addClass('collapse')
    //   self.jquery('body').removeClass('menu-expanded')
    //   self.jquery('.overlay').fadeOut()
    // }
  }

  toggleElement(el) {
    let self = this
    if (!el.classList.replace('hidden', 'gridden')) {
      el.classList.replace('gridden', 'hidden')
    }
  }

  moveMarker(root, marker) {
    let self = this
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

  markerDnD(root) {
    let self = this
    return (content) => {
      if (content.id == 'active-year-marker') {
        self.moveMarker(root, content)
        self.enableMarkerDnD(root)
      }
      for (const marker of content.querySelectorAll('.active-year-marker')) {
        self.moveMarker(root, marker)
        self.enableMarkerDnD(root)
      }
    }
  }

  installButtons(root) {
    let self = this
    return (content) => {
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
          elem.dispatchEvent(new Event(datatarget, {bubbles: true}))
        })
      }
    }
  }
}
