/*Attempting to isolate timeline slider functionality form fortepan.hu*/
      

        5703: function(e, t, r) {
            "use strict";
            r.r(t);
            var n = r(7931)
              , i = r(3658)
              , s = r(2107)
              , o = r(1418);
            t.default = class extends n.Qr {
                static get targets() {
                    return ["slider", "selectedRange", "yearStart", "yearEnd", "yearIndicator", "yearIndicatorLabel", "sliderKnob", "sliderYear", "sliderYearLabel", "sliderYearCount", "ruler", "rulerIndicator"]
                }
                connect() {
                    this.range = 0,
                    this.sliderDragged = null,
                    this.sliderDragStartX = 0,
                    this.sliderDragStartYear = 0,
                    this.yearStart = 0,
                    this.yearEnd = 0,
                    this.timelineOver = !1,
                    this.resetSlider(null, !1)
                }
                enable() {
                    this.element.classList.remove("is-disabled"),
                    this.element.classList.add("is-visible")
                }
                disable() {
                    this.element.classList.remove("is-visible"),
                    this.element.classList.add("is-disabled")
                }
                setSlider(e) {
                    o.Z.hasData() && (this.yearStart = o.Z.getFirstYearInContext().year,
                    this.yearEnd = o.Z.getLastYearInContext().year,
                    e && "photos:yearChanged" === e.type && e.detail && e.detail.year ? this.year = parseInt(e.detail.year, 10) : o.Z.getSelectedPhotoId() ? this.year = parseInt(o.Z.getSelectedPhotoData().year, 10) : this.year = this.yearStart,
                    this.setRange(),
                    this.fixSlider(),
                    this.setTimelineLabels())
                }
                setRange() {
                    this.range = this.sliderTarget.offsetWidth - this.sliderYearTarget.offsetWidth
                }
                getRange() {
                    return {
                        from: this.yearStart,
                        to: this.yearEnd
                    }
                }
                setTimelineLabels() {
                    this.sliderYearLabelTarget.textContent = this.year,
                    o.Z.getYearsInContext().find((e=>e.year === this.year)) ? (this.sliderYearTarget.classList.remove("is-empty"),
                    this.sliderYearCountTarget.textContent = o.Z.getYearsInContext().find((e=>e.year === this.year)).count) : (this.sliderYearTarget.classList.add("is-empty"),
                    this.sliderYearCountTarget.textContent = 0),
                    this.yearStartTarget.textContent = this.yearStart,
                    this.yearEndTarget.textContent = this.yearEnd
                }
                fixSlider() {
                    if (this.year > 0) {
                        const e = Math.floor(this.sliderYearTarget.offsetWidth / 2)
                          , t = Math.max(e, e + Math.min(Math.round((this.year - this.yearStart) / (this.yearEnd - this.yearStart) * this.range), this.range));
                        this.sliderYearTarget.style.left = t - e + "px",
                        this.selectedRangeTarget.style.left = "0px",
                        this.selectedRangeTarget.style.width = `${t + 2}px`;
                        const r = this.yearEnd - this.yearStart;
                        for (; this.rulerIndicatorTargets.length <= Math.floor(r / 10); ) {
                            const e = this.element.querySelectorAll(".photos-timeline__ruler-indicator")[0].cloneNode(!0);
                            this.rulerTarget.appendChild(e)
                        }
                        let n = this.yearStart;
                        const i = {};
                        for (; n < this.yearEnd; ) {
                            if (n % 10 == 0) {
                                i.left = e + Math.round(this.range / r * (n - this.yearStart)),
                                i.year = n;
                                break
                            }
                            n += 1
                        }
                        this.rulerIndicatorTargets.forEach(((e,t)=>{
                            t <= Math.floor(r / 10) && i.year + 10 * t <= this.yearEnd ? (e.style.left = `${i.left + Math.round(this.range / r * t * 10)}px`,
                            e.classList.add("visible")) : e.classList.remove("visible")
                        }
                        ))
                    }
                }
                resetSlider(e, t=!0) {
                    this.setSlider(),
                    t && this.enable()
                }
                calcYear() {
                    return this.year = this.yearStart + Math.round(this.sliderYearTarget.offsetLeft / this.range * (this.yearEnd - this.yearStart)),
                    this.year
                }
                setYear(e) {
                    if (this.year = e || this.calcYear(),
                    !o.Z.getYearsInContext().find((e=>e.year === this.year))) {
                        let e = -1;
                        o.Z.getYearsInContext().forEach((t=>{
                            Math.abs(this.year - t.year) < Math.abs(this.year - e) && (e = t.year)
                        }
                        )),
                        this.year = e > -1 ? e : this.sliderDragStartYear
                    }
                    this.fixSlider(),
                    this.setTimelineLabels(),
                    (this.sliderDragged && this.year !== this.sliderDragStartYear || !this.sliderDragged) && ((0,
                    i.Qb)().year > 0 || (0,
                    i.Qb)().id > 0 ? (0,
                    i.X$)("photos:historyPushState", {
                        url: "?q=",
                        resetPhotosGrid: !0,
                        jumpToYearAfter: this.year
                    }) : (0,
                    i.X$)("timeline:yearSelected", {
                        year: this.year
                    }))
                }
                sliderStartDrag(e) {
                    e.currentTarget.classList.add("is-active");
                    const t = e.touches ? e.touches[0].pageX : e.pageX;
                    this.sliderDragStartX = t - e.currentTarget.offsetLeft,
                    this.sliderDragStartYear = this.year,
                    this.element.classList.add("is-used"),
                    (0,
                    s.setAppState)("disable--selection"),
                    this.sliderDragged = e.currentTarget,
                    (0,
                    i.X$)("timeline:startDrag", {
                        year: this.year
                    })
                }
                sliderStopDrag() {
                    this.sliderDragged && (this.sliderKnobTargets.forEach((e=>{
                        e.classList.remove("is-active", "is-empty")
                    }
                    )),
                    this.element.classList.remove("is-used"),
                    (0,
                    s.removeAppState)("disable--selection"),
                    this.setYear(),
                    this.sliderDragged = null,
                    (0,
                    i.X$)("timeline:stopDrag", {
                        year: this.year
                    }))
                }
                sliderMoved(e) {
                    if (this.sliderDragged === this.sliderYearTarget && this.sliderYearTarget.offsetLeft >= 0) {
                        const t = e.touches ? e.touches[0].pageX : e.pageX
                          , r = Math.min(Math.max(t - this.sliderDragStartX, 0), this.sliderTarget.offsetWidth - this.sliderYearTarget.offsetWidth);
                        this.sliderYearTarget.style.left = `${r}px`,
                        this.selectedRangeTarget.style.left = "0px",
                        this.selectedRangeTarget.style.width = `${r + 2}px`,
                        this.calcYear(),
                        this.setTimelineLabels()
                    }
                }
                seek(e) {
                    if (e && this.timelineOver) {
                        const t = e.touches ? e.touches[0].pageX : e.pageX
                          , r = this.sliderYearTarget.getBoundingClientRect();
                        (t < r.left || t > r.right) && (this.yearIndicatorTarget.classList.remove("is-hover"),
                        this.setYear(this.calcIndicatorYear(t)))
                    }
                }
                jumpToStart() {
                    this.setYear(this.yearStart)
                }
                jumpToEnd() {
                    this.setYear(this.yearEnd)
                }
                onTimelineOver() {
                    this.yearIndicatorTarget.classList.add("is-hover"),
                    this.timelineOver = !0
                }
                onTimelineOut() {
                    this.timelineOver && (this.yearIndicatorTarget.classList.remove("is-hover"),
                    this.timelineOver = !1)
                }
                onTimelineMove(e) {
                    if (e && this.timelineOver) {
                        const t = e.touches ? e.touches[0].pageX : e.pageX
                          , r = this.sliderYearTarget.getBoundingClientRect();
                        if (t < r.left || t > r.right) {
                            this.yearIndicatorTarget.classList.add("is-hover");
                            const e = Math.min(Math.max(t - this.sliderTarget.getBoundingClientRect().left, 0), this.sliderTarget.offsetWidth);
                            this.yearIndicatorTarget.style.left = `${e}px`;
                            const r = this.calcIndicatorYear(t);
                            this.setIndicatorLabel(r)
                        } else
                            this.yearIndicatorTarget.classList.remove("is-hover")
                    }
                }
                calcIndicatorYear() {
                    const e = this.sliderYearTarget.getBoundingClientRect()
                      , t = this.yearIndicatorTarget.offsetLeft - Math.floor(e.width / 2);
                    return Math.max(this.yearStart, Math.min(this.yearEnd, this.yearStart + Math.round(t / this.range * (this.yearEnd - this.yearStart))))
                }
                setIndicatorLabel(e) {
                    o.Z.getYearsInContext().find((t=>t.year === e)) ? (this.yearIndicatorTarget.classList.remove("is-empty"),
                    this.yearIndicatorLabelTarget.innerHTML = `${e}`) : (this.yearIndicatorTarget.classList.add("is-empty"),
                    this.yearIndicatorLabelTarget.innerHTML = `${e}`)
                }
                onResize() {
                    this.calcYear(),
                    this.setRange(),
                    this.fixSlider(),
                    this.setTimelineLabels()
                }
                toggleShadow(e) {
                    e && "photosThumbnail:select" === e.type && this.element.classList.add("has-shadow"),
                    e && "photosCarousel:hide" === e.type && this.element.classList.remove("has-shadow")
                }
            }
        }