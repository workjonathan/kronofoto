import { setAppState, removeAppState, getURLParams, trigger } from "./utils"
// import photoManager from "../../js/photo-manager"
export default class {
    get targets() {
        return [
            "slider",
            "selectedRange",
            "yearStart",
            "yearEnd",
            "yearIndicator",
            "yearIndicatorLabel",
            "sliderKnob",
            "sliderYear",
            "sliderYearLabel",
            "sliderYearCount",
            "ruler",
            "rulerIndicator",
        ]
    }

    connect(element) {
        this.range = 0

        // slider status
        this.sliderDragged = null
        this.sliderDragStartX = 0
        this.sliderDragStartYear = 0
        this.yearStart = 0
        this.yearEnd = 0

        this.timelineOver = false
        this.element = element

        // init targets
        this.initTargets()
        console.log(this)

        // init event handlers
        this.initEventHandlers()

        // init component
        this.resetSlider(null, false)
    }

    initEventHandlers() {

        $(this.yearStartTarget).on('click', (e) => { this.jumpToStart.call(this, e) })
        $(this.yearEndTarget).on('click', (e) => { this.jumpToEnd.call(this, e) })

        $(this.sliderTarget).on('mouseenter', (e) => { this.onTimelineOver.call(this, e) })
        $(document).on('mousemove', (e) => { this.onTimelineMove.call(this, e) })
        $(this.sliderTarget).on('mouseleave',  (e) => { this.onTimelineOut.call(this, e) })
        $(this.sliderTarget).on('click', (e) => { this.seek.call(this, e) })

        $(this.sliderKnobTarget).on('touchstart mousedown', (e) => { this.sliderStartDrag.call(this, e) })
        $(document).on('touchmove mousemove', (e) => { this.sliderMoved.call(this, e) })
        $(document).on('touchend mouseup', (e) => { this.sliderStopDrag.call(this, e) })

    }

    initTargets() {
        this.targets.forEach((target, index) => {
            let targets = [];
            $('[data-timeline-target]').each(function(i,e) {
                let items = $(e).attr('data-timeline-target');
                items = items.split(' ')
                for(let i in items) {
                    let item = items[i]
                    if(item == target) {
                        targets.push(e)
                        break
                    }
                }
            });
            this[target + 'Target'] = targets[0]
            this[target + 'Targets'] = targets
        }, this)
    }

    enable() {
        this.element.classList.remove("is-disabled")
        this.element.classList.add("is-visible")
    }

    disable() {
        this.element.classList.remove("is-visible")
        this.element.classList.add("is-disabled")
    }

    // TODO
    setSlider(e) {
        if (true) { //if (photoManager.hasData()) {
            this.yearStart = 1900 //photoManager.getFirstYearInContext().year
            this.yearEnd = 2000 //photoManager.getLastYearInContext().year
            this.year = 1980
            if (e && e.type === "photos:yearChanged" && e.detail && e.detail.year) {
                // when it is a listener for photos:yearChanged
                // where the parameter year should be passed
                this.year = parseInt(e.detail.year, 10)
            }
            /*
            else if (photoManager.getSelectedPhotoId()) {
                // if there is a selected photo (event listener for photoManager:photoSelected)
                this.year = parseInt(photoManager.getSelectedPhotoData().year, 10)
            } else {
                // this function is called even if there isn't any photo selected (as part of the reset chain),
                // in which case...
                this.year = this.yearStart
            }*/

            this.setRange()
            this.fixSlider()
            this.setTimelineLabels()
        }
    }

    setRange() {
        this.range = this.sliderTarget.offsetWidth - this.sliderYearTarget.offsetWidth
    }

    getRange() {
        return { from: this.yearStart, to: this.yearEnd }
    }

    setTimelineLabels() {
        this.sliderYearLabelTarget.textContent = this.year

        // check if selected year (this.year) has photos at all (not already loaded)
        // and if not, grey out the slider
        // if (photoManager.getYearsInContext().find(item => item.year === this.year)) {
        //     this.sliderYearTarget.classList.remove("is-empty")
        //     this.sliderYearCountTarget.textContent = photoManager
        //         .getYearsInContext()
        //         .find(item => item.year === this.year).count
        // } else {
        //     this.sliderYearTarget.classList.add("is-empty")
        //     this.sliderYearCountTarget.textContent = 0
        // }

        this.yearStartTarget.textContent = this.yearStart
        this.yearEndTarget.textContent = this.yearEnd
    }

    fixSlider() {
        if (this.year > 0) {
            const left = Math.floor(this.sliderYearTarget.offsetWidth / 2)
            const start = Math.max(
                left,
                left +
                Math.min(
                    Math.round(((this.year - this.yearStart) / (this.yearEnd - this.yearStart)) * this.range),
                    this.range
                )
            )

            this.sliderYearTarget.style.left = `${start - left}px`
            this.selectedRangeTarget.style.left = `0px`
            this.selectedRangeTarget.style.width = `${start + 2}px`

            // setting the ruler indicators (for every 10 years)

            const yearsCount = this.yearEnd - this.yearStart

            // creating the ruler indicators if they're not created yet
            while (this.rulerIndicatorTargets.length <= Math.floor(yearsCount / 10)) {
                // clone template
                const indicator = document.querySelectorAll(".photos-timeline__ruler-indicator")[0].cloneNode(true)
                this.rulerTarget.appendChild(indicator)
                this.initTargets()
            }

            // calculate the x position of the first decade marker
            let counter = this.yearStart
            const firstDecade = {}

            while (counter < this.yearEnd) {
                if (counter % 10 === 0) {
                    firstDecade.left = left + Math.round((this.range / yearsCount) * (counter - this.yearStart))
                    firstDecade.year = counter
                    break
                }
                counter += 1
            }

            this.rulerIndicatorTargets.forEach((item, index) => {
                if (index <= Math.floor(yearsCount / 10) && firstDecade.year + index * 10 <= this.yearEnd) {
                    item.style.left = `${firstDecade.left + Math.round((this.range / yearsCount) * index * 10)}px`
                    item.classList.add("visible")
                } else {
                    item.classList.remove("visible")
                }
            })
        }
    }

    resetSlider(e, enable = true) {
        this.setSlider()
        if (enable) this.enable()
    }

    calcYear() {
        this.year =
            this.yearStart + Math.round((this.sliderYearTarget.offsetLeft / this.range) * (this.yearEnd - this.yearStart))

        return this.year
    }

    // TODO
    setYear(year) {
        this.year = year || this.calcYear()

        // // check if selected year (this.year) has photos at all (not already loaded)
        // // and if not, jump to the closest year that has
        // if (!photoManager.getYearsInContext().find(item => item.year === this.year)) {
        //     let closestMatch = -1
        //     photoManager.getYearsInContext().forEach(item => {
        //         if (Math.abs(this.year - item.year) < Math.abs(this.year - closestMatch)) {
        //             closestMatch = item.year
        //         }
        //     })
        //
        //     if (closestMatch > -1) {
        //         this.year = closestMatch
        //     } else {
        //         // if for some reason the above fails fall back to the last stored year
        //         this.year = this.sliderDragStartYear
        //     }
        // }

        this.fixSlider()
        this.setTimelineLabels()

        if ((this.sliderDragged && this.year !== this.sliderDragStartYear) || !this.sliderDragged) {
            // if we are in a year context, let's clear the context
            if (getURLParams().year > 0 || getURLParams().id > 0) {
                trigger("photos:historyPushState", { url: "?q=", resetPhotosGrid: true, jumpToYearAfter: this.year })
            } else {
                trigger("timeline:yearSelected", { year: this.year })
            }
        }
    }

    sliderStartDrag(e) {
        e.currentTarget.classList.add("is-active")
        const px = e.touches ? e.touches[0].pageX : e.pageX
        this.sliderDragStartX = px - e.currentTarget.offsetLeft

        this.sliderDragStartYear = this.year

        this.element.classList.add("is-used")
        setAppState("disable--selection") // TODO
        this.sliderDragged = e.currentTarget

        trigger("timeline:startDrag", { year: this.year })
    }

    sliderStopDrag() {
        if (this.sliderDragged) {
            this.sliderKnobTargets.forEach(knob => {
                knob.classList.remove("is-active", "is-empty")
            })

            this.element.classList.remove("is-used")
            removeAppState("disable--selection") // TODO

            this.setYear()
            this.sliderDragged = null

            trigger("timeline:stopDrag", { year: this.year })
        }
    }

    sliderMoved(e) {
        if (this.sliderDragged === this.sliderYearTarget && this.sliderYearTarget.offsetLeft >= 0) {
            const px = e.touches ? e.touches[0].pageX : e.pageX
            const x = Math.min(
                Math.max(px - this.sliderDragStartX, 0),
                this.sliderTarget.offsetWidth - this.sliderYearTarget.offsetWidth
            )

            this.sliderYearTarget.style.left = `${x}px`
            this.selectedRangeTarget.style.left = `0px`
            this.selectedRangeTarget.style.width = `${x + 2}px`

            this.calcYear()
            this.setTimelineLabels()
        }
    }

    seek(e) {
        if (e && this.timelineOver) {
            const px = e.touches ? e.touches[0].pageX : e.pageX
            const knobBounds = this.sliderYearTarget.getBoundingClientRect()

            if (px < knobBounds.left || px > knobBounds.right) {
                this.yearIndicatorTarget.classList.remove("is-hover")
                this.setYear(this.calcIndicatorYear(px))
            }
        }
    }

    jumpToStart() {
        this.setYear(this.yearStart)
    }

    jumpToEnd() {
        this.setYear(this.yearEnd)
    }

    onTimelineOver() {
        this.yearIndicatorTarget.classList.add("is-hover")
        this.timelineOver = true
    }

    onTimelineOut() {
        if (this.timelineOver) {
            this.yearIndicatorTarget.classList.remove("is-hover")
            this.timelineOver = false
        }
    }

    onTimelineMove(e) {
        if (e && this.timelineOver) {
            const px = e.touches ? e.touches[0].pageX : e.pageX
            const knobBounds = this.sliderYearTarget.getBoundingClientRect()

            if (px < knobBounds.left || px > knobBounds.right) {
                // if the cursor is not over the slider knob
                this.yearIndicatorTarget.classList.add("is-hover")

                const x = Math.min(
                    Math.max(px - this.sliderTarget.getBoundingClientRect().left, 0),
                    this.sliderTarget.offsetWidth
                )

                this.yearIndicatorTarget.style.left = `${x}px`

                const year = this.calcIndicatorYear(px)
                this.setIndicatorLabel(year)
            } else {
                // mouse is over the slider knob's area
                this.yearIndicatorTarget.classList.remove("is-hover")
            }
        }
    }

    calcIndicatorYear() {
        const knobBounds = this.sliderYearTarget.getBoundingClientRect()
        const targetX = this.yearIndicatorTarget.offsetLeft - Math.floor(knobBounds.width / 2)

        return Math.max(
            this.yearStart,
            Math.min(this.yearEnd, this.yearStart + Math.round((targetX / this.range) * (this.yearEnd - this.yearStart)))
        )
    }

    // TODO
    setIndicatorLabel(year) {
        // check if selected year has photos at all (not already loaded)
        // and if not, grey out the slider
        // if (photoManager.getYearsInContext().find(item => item.year === year)) {
            this.yearIndicatorTarget.classList.remove("is-empty")
            this.yearIndicatorLabelTarget.innerHTML = `${year}`
        // } else {
        //     this.yearIndicatorTarget.classList.add("is-empty")
        //     this.yearIndicatorLabelTarget.innerHTML = `${year}`
        // }
    }

    onResize() {
        this.calcYear()
        this.setRange()
        this.fixSlider()
        this.setTimelineLabels()
    }

    toggleShadow(e) {
        if (e && e.type === "photosThumbnail:select") {
            this.element.classList.add("has-shadow")
        }

        if (e && e.type === "photosCarousel:hide") {
            this.element.classList.remove("has-shadow")
        }
    }
}
