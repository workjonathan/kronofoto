import HTMX from "./htmx.js"
import timeline from "./timeline.js"
import {
  installButtons,
  toggleMenu,
  markerDnD,
  toggleLogin,
  initGalleryNav,
  autoplayStart,
  autoplayStop,
  timelineForward,
  timelineBackward,
  timelineZipForward,
  timelineZipBackward,
  timelineCrawlForward,
  timelineCrawlForwardRelease,
  timelineCrawlBackward,
  timelineCrawlBackwardRelease,
  moveTimelineCoin,
  dropTimelineCoin }
  from "./lib.js"

window.toggleLogin = toggleLogin

const htmx = HTMX(document)
window.htmx = htmx
const _timeline = new timeline();

document.addEventListener("DOMContentLoaded", function () {
  const preloadImages = document.querySelectorAll("img[preload]");
  for (const img of preloadImages) {
    const image = new Image();
    image.src = img.src;
  }
});

function showImagesBeforeSwap(target) {
  const images = target.querySelectorAll('img');

  images.forEach((img) => {
    if (!img.complete) {
      // When the image is not yet loaded, set an event listener to show it when loaded
      img.addEventListener('load', function () {
        img.style.opacity = 1; /* or use visibility: visible; */
      });
    } else {
      img.style.opacity = 1; /* or use visibility: visible; */
    }
  });
}

// Attach the function to HTMX beforeSwap events
document.addEventListener('htmx:beforeSwap', function (event) {
  // showImagesBeforeSwap(event.detail.target);
  if($(event.srcElement).attr('id') == 'fi-image-tag') {
    let res = event.detail.serverResponse
    let images = $(res).find('#fi-thumbnail-carousel-images img')
    // images.each((i,e) => {
    //   let url = $(e).attr('src')
    //   $('#fi-thumbnail-carousel-images li:nth-child('+i+') img').attr('src', url)
    // })
    // $('#fi-thumbnail-carousel-images').css({left: 0})

    return false;
  }
  return false;
});

htmx.onLoad(() => {
  installButtons(document)
  initDraggableThumbnails()
  $('#fi-thumbnail-carousel-images').css({left: 0})
})

initGalleryNav()

document.addEventListener('htmx:afterSwap', (event) => {
  let newYear = $('[data-timeline-target=sliderYearLabel]').html()
  _timeline.setYear(newYear, false)
})
//
// window.checkDrag = (event) => {
//   console.log(event)
//   if (event.originalEvent && event.originalEvent.type === 'drag') {
//     return false; // Prevent the hx-get request after a drag event
//   }
//   return true;
// }

window.setTimeout(() => { htmx.onLoad(markerDnD(document)) }, 100)
//htmx.logAll()

const initDraggableThumbnails = () => {
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


const init = () => {

    document.querySelector('.hamburger').addEventListener("click", toggleMenu)

    // initDraggableThumbnails()

    $(document).click(function(event)
    {

        //~TESTING LINE
        //console.log(event.target.className)

        var classOfThingClickedOn = event.target.className

        //~TESTING LINE
        //console.log($('.search-form').find('*'))

        //creates a jQuery collection of the components of the search menu EXCEPT for the menu itself
        var $descendantsOfSearchForm = $('.search-form').find('*')

        //---creates an array of all components of the search menu dropdown---
        //adds the search menu itself to the array
        var componentsOfSearchMenuArray = ['search-form']

        //adds the class of all the components of the search menu to the array
        $descendantsOfSearchForm.each(function(index)
        {
            //checks to make sure the class isn't already in the array
            if($.inArray(this.className, componentsOfSearchMenuArray) == -1)
            {
                //adds the class to the array
                componentsOfSearchMenuArray.push(this.className)
            }
        })

        //~TESTING LINES
        //console.log(componentsOfSearchMenuArray)
        //console.log('Class:'+'"'+classOfThingClickedOn+'"')
        //console.log(componentsOfSearchMenuArray.includes(classOfThingClickedOn))

        //if the search menu is open and the user clicks on something outside of the menu, close the menu
        if($('.search-form').is(":visible") && (!(componentsOfSearchMenuArray.includes(classOfThingClickedOn))))
        {
            $('.search-form').toggle()
        }
        //if the user clicks on the carrot or the small invisible box behind it, toggle the menu
        else if(classOfThingClickedOn == 'search-options' || classOfThingClickedOn == 'carrot')
        {
            $('.search-form').toggle()
        }
    })

    $('#tag-search').autocomplete({
        source: '/tags',
        minLength: 2,
    })

    $(document).on('click', '#forward', timelineZipForward)
    $(document).on('mousedown', '#forward', timelineCrawlForward)
    $(document).on('mouseup', '#forward', timelineCrawlForwardRelease)
    $(document).on('click', '#backward', timelineZipBackward)
    $(document).on('mousedown', '#backward', timelineCrawlBackward)
    $(document).on('mouseup', '#backward', timelineCrawlBackwardRelease)

    $(document).on('keydown', function(event) {
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

    $(document).on('click', '#auto-play-image-control-button', (e) => {
      let $btn = $('#auto-play-image-control-button')
      $btn.toggleClass('active')
      $('img', $btn).toggleClass('hide')
      if($btn.hasClass('active')) {
        autoplayStart()
      }
      else {
        autoplayStop()
      }
    })

    //
    // $('.overlay, .close-btn').click(() => {
    //     $('.gridden').removeClass('gridden').addClass('hidden')
    //     $('.overlay').css('display', 'none')
    // })

    $('.photos-timeline').each(function(i,e) {
      _timeline.connect(e);
    });

    $('#login-btn').click(() => {
        if($('#login').hasClass('gridden')) {
            $('.overlay').css('display', 'block')
        } else {
            $('.overlay').css('display', 'none')
        }
    })

    $('#search-box').focus(function() {
        $('#search-box-container').css('background','var(--fp-main-blue)')
        $('.search-icon').css('filter', 'brightness(0) invert(1)')
        $('.carrot').css('filter', 'brightness(0) invert(1)')
        $('#search-box').addClass('placeholder-light').css('color', 'white')

    }).blur(function() {
        $('#search-box-container').css('background','var(--fp-light-grey)')
        $('.search-icon').css('filter', 'none')
        $('.carrot').css('filter', 'none')
        $('#search-box').removeClass('placeholder-light').css('color', '#333')
        //('#search-box').css('color', 'var(--fp-light-grey)')
    });

}

const ready = fn => {
    if (document.readyState !== "loading") {
        fn()
    } else {
        document.addEventListener("DOMContentLoaded", fn)
    }
}

ready(init)
