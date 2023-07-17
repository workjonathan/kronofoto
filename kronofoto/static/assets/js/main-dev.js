import HTMX from "./htmx.js"
import timeline from "./timeline.js"
import {installButtons, toggleMenu, markerDnD, toggleLogin} from "./lib.js"
window.toggleLogin = toggleLogin

const htmx = HTMX(document)

htmx.onLoad(installButtons(document))
window.setTimeout(() => { htmx.onLoad(markerDnD(document)) }, 100)
//htmx.logAll()
htmx.onLoad(elt => {
    for (let child of elt.querySelectorAll("#thumbnail-request")) {
        child.addEventListener('kronofoto:onThumbnails', evt => {
            console.log(evt.detail.object_list)
        })
    }
}
)
const init = () => {

    document.querySelector('.hamburger').addEventListener("click", toggleMenu)

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

    $('.photos-timeline').each(function(i,e) {
       var _timeline = new timeline();
       _timeline.connect(e);
    });

    $('#tag-search').autocomplete({
        source: '/tags',
        minLength: 2,
    })

    //
    // $('.overlay, .close-btn').click(() => {
    //     $('.gridden').removeClass('gridden').addClass('hidden')
    //     $('.overlay').css('display', 'none')
    // })


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
