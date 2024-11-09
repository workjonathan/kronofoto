"use strict"

import {trigger} from "./utils"
import timeline from "./timeline"
import $ from "jquery"
import ClipboardActionCopy from "clipboard/src/actions/copy"
import "jquery-ui-pack"
import Select2 from "select2"
//Select2.default(window, $)
import {Viewer} from "@photo-sphere-viewer/core"
import {MarkersPlugin} from "@photo-sphere-viewer/markers-plugin"
import {VirtualTourPlugin} from "@photo-sphere-viewer/virtual-tour-plugin"
import {ImagePlanePlugin, toRadians} from "./photosphere.js"
import AOS from "aos"


// Foundation
import {Foundation} from "./foundation-sites/js/foundation.core"
import * as CoreUtils from "./foundation-sites/js/foundation.core.utils"
import {Motion, Move} from "./foundation-sites/js/foundation.util.motion"
import {Touch} from "./foundation-sites/js/foundation.util.touch"
import {Toggler} from "./foundation-sites/js/foundation.toggler"
import {Tooltip} from "./foundation-sites/js/foundation.tooltip"
import {Box} from "./foundation-sites/js/foundation.util.box"
import {MediaQuery} from "./foundation-sites/js/foundation.util.mediaQuery"
import {Reveal} from "./foundation-sites/js/foundation.reveal"
import {Triggers} from "./foundation-sites/js/foundation.util.triggers"

class TimelineScroller {
    constructor({context}) {
        this.context = context
    }
    slideToId({target, fi}) {
        for (const targets of this.context.querySelectorAll(target)) {
            let destination,
                candidate = undefined
            for (const elem of targets.querySelectorAll(`:scope > [data-fi="${fi}"]`)) {
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
                this.gotoTimelinePosition(delta)
            }
        }
    }
    install({elem}) {
        this.initDraggableThumbnails(elem)
    }
    initDraggableThumbnails(newElems) {
        let elem = undefined
        let released = false
        const handler = (evt) => {
            if (
                !released ||
                !evt.detail.elt.parentElement.attributes.getNamedItem("data-active")
            ) {
                console.log("preventing", evt)
                evt.preventDefault()
            } else {
                console.log("allowing", evt)
                setTimeout(() => elem.removeEventListener("htmx:confirm", handler), 100)
            }
        }
        let carousel = newElems.querySelector("#fi-thumbnail-carousel-images")
        this.widthElement =
            (carousel ? carousel.getAttribute("data-width-element") : undefined) ||
            "#fi-image"
        $("#fi-thumbnail-carousel-images", newElems).draggable({
            axis: "x",
            drag: (event, ui) => {
                if (!elem) {
                    elem = event.target
                    console.log("installing htmx:confirm handler", elem)
                    elem.addEventListener("htmx:confirm", handler)
                }
                this.moveTimelineCoin(ui.position.left, true)
            },
            stop: (event, ui) => {
                this.dropTimelineCoin(ui.position.left)
                released = true
                for (const temp of this.context.querySelectorAll(
                    "#fi-thumbnail-carousel-images li[data-active] a",
                )) {
                    trigger("click", {}, temp, true)
                }
            },
        })
    }
    moveTimelineCoin(deltaX, drag = true) {
        if (drag) {
            $("#fi-thumbnail-carousel-images", this.context).addClass("dragging")
        } else {
            $("#fi-thumbnail-carousel-images", this.context).removeClass("dragging")
        }
        let widthOfThumbnail = $(
            "#fi-thumbnail-carousel-images li",
            this.context,
        ).outerWidth()
        let preItemNum = $(
            "#fi-thumbnail-carousel-images [data-origin]",
            this.context,
        ).index()
        let quantizedPositionX = Math.round(deltaX / widthOfThumbnail) * -1
        let currentPosition = preItemNum + quantizedPositionX + 1

        let numThumbnails = $("#fi-thumbnail-carousel-images li", this.context).length
        let scroller = undefined
        if (drag && numThumbnails - currentPosition < 20) {
            scroller = new ForwardScroller({context: this.context})
        } else if (drag && currentPosition < 20) {
            scroller = new BackwardScroller({context: this.context})
        }
        if (scroller !== undefined) {
            scroller.doThumbnailForm()
        }
        $("#fi-thumbnail-carousel-images li", this.context).removeAttr("data-active")
        $(
            "#fi-thumbnail-carousel-images li:nth-child(" + currentPosition + ")",
            this.context,
        ).attr("data-active", "")
    }
    gotoTimelinePosition(delta) {
        let width = $("#fi-thumbnail-carousel-images li", this.context).outerWidth()
        this.moveTimelineCoin(delta * -1 * width, false)
        this.dropTimelineCoin(delta * -1 * width)
    }
    dropTimelineCoin(deltaX) {
        let width = $("#fi-thumbnail-carousel-images li", this.context).outerWidth()
        let quantizedX = Math.round(deltaX / width)
        let itemNum = quantizedX
        $("#fi-thumbnail-carousel-images", this.context).css({
            left: itemNum * width,
        })
    }
    getNumVisibleTimelineTiles() {
        let widthOfTimeline = $(this.widthElement, this.context).width() // assumes the timeline is the same width as gallery image
        let $li = $("#fi-thumbnail-carousel-images li[data-active]", this.context)
        let widthOfTile = $li.outerWidth()
        return Math.floor(widthOfTimeline / widthOfTile)
    }
}

class DirectionalScroller extends TimelineScroller {
    timelineZip() {
        if (this.getTimelineCrawlInterval() === undefined) {
            // only zip if we're not already crawling
            let numToZip = Math.floor(this.getNumVisibleTimelineTiles() - 0.5)
            let $activeLi = $(
                "#fi-thumbnail-carousel-images li[data-active]",
                this.context,
            )
            let $nextLi = this.nextElements({active: $activeLi}).eq(numToZip)
            trigger("click", {}, $nextLi.find("a").get(0), true)
        }
        return false
    }
    timelineCrawl() {
        const id = setTimeout(() => {
            let currentPosition = $(
                "#fi-thumbnail-carousel-images",
                this.context,
            ).position().left
            const intervalId = setInterval(() => {
                if (this.canCrawl()) {
                    currentPosition += this.getTimelineShiftPixels()
                    $("#fi-thumbnail-carousel-images", this.context).css(
                        "left",
                        currentPosition,
                    )
                    this.moveTimelineCoin(currentPosition, true)
                }
            }, 50)
            this.setTimelineCrawlInterval({id: intervalId})
        }, 500)
        this.setTimelineCrawlTimeout({id})
    }
    timelineCrawlRelease() {
        clearTimeout(this.getTimelineCrawlTimeout())
        this.setTimelineCrawlTimeout({id: undefined})
        if (this.getTimelineCrawlInterval()) {
            // only execute when we're crawling
            clearInterval(this.getTimelineCrawlInterval())
            this.dropTimelineCoin(
                $("#fi-thumbnail-carousel-images", this.context).position().left,
            )
            trigger(
                "click",
                {},
                $("#fi-thumbnail-carousel-images li[data-active] a", this.context).get(0),
                true,
            )
            setTimeout(() => {
                this.setTimelineCrawlInterval({id: undefined})
            }, 750)
        }
    }
    doThumbnailForm() {
        const form = $("#fi-thumbnail-carousel-images", this.context)
            .closest("form")
            .get(0)
        form.querySelector("[name='forward']").value = this.isForward()
        form.setAttribute("hx-swap", this.swapType())

        const child = form.querySelector(this.lastChildSelector())
        const lastFI = child.getAttribute("data-fi")
        const offset = $(child).position().left
        const width = $(child).outerWidth()

        form.querySelector("[name='offset']").value = Math.round(offset)
        form.querySelector("[name='width']").value = width

        form.querySelector("[name='id']").value = lastFI
        trigger(
            "kronofoto:loadThumbnails",
            {},
            $("#fi-thumbnail-carousel-images", this.context).get(0),
            true,
        )
    }
    canCrawl() {
        let length = this.nextElements({
            active: $("#fi-thumbnail-carousel-images [data-active]", this.context),
        }).length
        return length > 10
    }
    install({elem}) {
        for (const elem2 of querySelectorAll({
            node: elem,
            selector: this.elementSelector(),
        })) {
            elem2.addEventListener("click", this.timelineZip.bind(this))
            elem2.addEventListener("mousedown", this.timelineCrawl.bind(this))
            elem2.addEventListener("mouseup", this.timelineCrawlRelease.bind(this))
        }
    }
}

class BackwardScroller extends DirectionalScroller {
    elementSelector() {
        return "#backward-zip"
    }
    nextElements({active}) {
        return active.prevAll()
    }
    getTimelineCrawlInterval() {
        return this.timelineCrawlBackwardInterval
    }
    setTimelineCrawlInterval({id}) {
        this.timelineCrawlBackwardInterval = id
    }
    getTimelineShiftPixels() {
        return 20
    }
    getTimelineCrawlTimeout() {
        return this.timelineCrawlBackwardTimeout
    }
    setTimelineCrawlTimeout({id}) {
        this.timelineCrawlBackwardTimeout = id
    }
    isForward() {
        return false
    }
    lastChildSelector() {
        return "#fi-thumbnail-carousel-images li:first-child"
    }
    swapType() {
        return "afterbegin"
    }
}

class ForwardScroller extends DirectionalScroller {
    elementSelector() {
        return "#forward-zip"
    }
    nextElements({active}) {
        return active.nextAll()
    }
    getTimelineCrawlInterval() {
        return this.timelineCrawlForwardInterval
    }
    setTimelineCrawlInterval({id}) {
        this.timelineCrawlForwardInterval = id
    }
    getTimelineShiftPixels() {
        return -20
    }
    getTimelineCrawlTimeout() {
        return this.timelineCrawlForwardTimeout
    }
    setTimelineCrawlTimeout({id}) {
        this.timelineCrawlForwardTimeout = id
    }
    isForward() {
        return true
    }
    lastChildSelector() {
        return "#fi-thumbnail-carousel-images li:last-child"
    }
    swapType() {
        return "beforeend"
    }
}
class ImageLoader {
    constructor({img, file, reader = FileReader}) {
        this.img = img
        this.file = file
        this.reader = reader
    }
    loadImage() {
        const reader = new this.reader()
        reader.onload = this.setImage.bind(this)
        reader.readAsDataURL(this.file)
    }
    setImage(evt) {
        this.img.src = evt.target.result
    }
}
class NullLoader {
    loadImage() {}
}

class CopyLink {
    constructor({context}) {
        this.context = context
    }
    install({elem}) {
        for (const elem2 of elem.querySelectorAll("[data-clipboard-copy]")) {
            elem2.addEventListener("click", this.copyLink.bind(this))
        }
    }
    copyLink(evt) {
        evt.preventDefault()
        navigator.clipboard.writeText(evt.target.getAttribute("href")).then(
            () => {
                showToast("The link has been copied to the clipboard.")
            },
            () => {
                showToast(
                    "ERROR: The collection link has not been copied to the clipboard.",
                )
            },
        )
    }
}

class PageEditor {
    constructor({context}) {
        this.context = context
    }
    install({elem}) {
        for (const modal of this.context.querySelectorAll("#add-image-modal")) {
            this.context.addEventListener("kronofoto:modal:reveal", (evt) => {
                $(modal).foundation("open")
            })
        }
        for (const img of elem.querySelectorAll("[data-photo-target]")) {
            img.addEventListener("click", (evt) => {
                const id = img.getAttribute("data-photo-target")
                $("#add-image-modal", this.context).foundation("close")
                const target = this.context.querySelector(`#${id}`)
                target.value = img.getAttribute("data-id")
                target.dispatchEvent(
                    new Event("change", {
                        bubbles: false,
                    }),
                )
            })
        }
        for (const btn of elem.querySelectorAll(".component-menu--off-canvas .up")) {
            btn.addEventListener("click", this.moveComponentUp.bind(this))
        }
        for (const btn of elem.querySelectorAll(".component-menu--off-canvas .down")) {
            btn.addEventListener("click", this.moveComponentDown.bind(this))
        }
        for (const btn of elem.querySelectorAll(".component-menu--off-canvas .delete")) {
            btn.addEventListener("click", this.deleteComponent.bind(this))
        }
        for (const elem2 of elem.querySelectorAll("[data-target]")) {
            elem2.addEventListener("input", (event) => {
                const id = elem2.getAttribute("data-target")
                const target = this.context.querySelector(`#${id}`)
                target.value = elem2.innerText
            })
        }
        for (const elem2 of elem.querySelectorAll("[data-copy-source]")) {
            const handleSourceChange = (event) => {
                if (!this.context.contains(elem2)) {
                    this.context.removeEventListener("input", handleSourceChange)
                    return
                }
                if (event.target.id == elem2.getAttribute("data-copy-source")) {
                    elem2.innerText = event.target.innerText
                }
            }
            this.context.addEventListener("input", handleSourceChange)
        }
        for (const elem2 of elem.querySelectorAll("[data-on-check-target]")) {
            const target = elem2.getAttribute("data-on-check-target")
            const add = elem2.getAttribute("data-on-check-add")
            const remove = elem2.getAttribute("data-on-check-remove")
            elem2.addEventListener("change", (evt) => {
                const targetElem = evt.target.closest(target)
                targetElem.classList.remove(remove)
                targetElem.classList.add(add)
            })
        }
    }

    moveComponentUp(event) {
        const button = event.target
        const card = button.closest(".card")
        let previous = card
        while ((previous = previous.previousElementSibling)) {
            if (previous.classList.contains("card")) {
                break
            }
        }
        if (previous !== card) {
            previous.insertAdjacentElement("beforebegin", card)
            previous.style["z-index"]--
            card.style["z-index"]++
            AOS.refreshHard()
        }
    }

    moveComponentDown(event) {
        const button = event.target
        const card = button.closest(".card")
        let next = card
        while ((next = next.nextElementSibling)) {
            if (next.classList.contains("card")) {
                break
            }
        }
        if (next !== card) {
            next.insertAdjacentElement("afterend", card)
            card.style["z-index"]--
            next.style["z-index"]++
            AOS.refreshHard()
        }
    }

    deleteComponent(event) {
        const button = event.target
        const card = button.closest(".card")
        card.remove()
    }

    updateHiddenField(event) {
        if (event.target.getAttribute("contenteditable") !== null) {
            const contentEditable = event.target
            const targetName = contentEditable.getAttribute("data-target")
            if (targetName) {
                const $field = $(`#${targetName}`, this)

                if ($field.length) {
                    $field.val(contentEditable.innerText)
                }
            }
        }
    }
}
class ImagePreviewInput {
    constructor({context}) {
        this.context = context
    }
    install({elem}) {
        for (const elem2 of elem.querySelectorAll("[data-image-input]")) {
            elem2.addEventListener("change", this.imageChange.bind(this))
        }
    }
    imageChange(evt) {
        const img = this.getPrevious({elem: evt.target, tagName: "IMG"})
        this.selectLoader({img, input: evt.target}).loadImage()
    }
    getPrevious({elem, tagName}) {
        while (elem.tagName !== tagName && elem) {
            elem = elem.previousElementSibling
        }
        return elem
    }
    selectLoader({img, input}) {
        if (img && input.files && input.files[0]) {
            return new ImageLoader({img, file: input.files[0]})
        } else {
            return new NullLoader()
        }
    }
}
//$.fn.extend({
//    trigger: function triggerHack(eventType, extraParameters) {
//        trigger(eventType, extraParameters, this.get(0), true)
//    },
//})

//const toggleListener = context => {
//    function toggleListenerImpl() {
//        let ids = $(this).data('toggle')
//        console.log(ids)
//        if (ids) {
//            ids.split(" ").forEach(id => {
//                const element = $(`#${id}`, context)
//                console.log(element, context)
//                trigger("toggle.zf.trigger", [$(this)], element.get(0), true)
//            })
//        } else {
//            trigger("toggle.zf.trigger", {}, this, true)
//        }
//    }
//    return toggleListenerImpl
//}
// const addToggleListener = context => {
//     context.off("click.zf.trigger", toggleListener(context))
//     context.on("click.zf.trigger", '[data-toggle]', toggleListener(context))
// }

function* querySelectorAll({node, selector}) {
    // This generator is like querySelectorAll except that it can also match the current node.
    // It is tempting to stick this into Document and HTMLElement prototypes under some weird name.
    if ("matches" in node && node.matches(selector)) {
        yield node
    }
    for (const match of node.querySelectorAll(selector)) {
        yield match
    }
}
class Gallery {
    constructor({context}) {
        this.context = context
    }
    install({elem}) {
        this.initGalleryNav(elem)
    }
    initGalleryNav(elem) {
        // When the mouse moves
        for (const gallery of querySelectorAll({
            node: elem,
            selector: ".control",
        })) {
            let hideGalleryTimeout = null
            gallery.addEventListener("mousemove", () => {
                this.showGalleryNav()
                if (hideGalleryTimeout) clearTimeout(hideGalleryTimeout)
                hideGalleryTimeout = setTimeout(this.hideGalleryNav.bind(this), 5000)
            })
        }
    }
    showGalleryNav() {
        $(".gallery", this.context).removeClass("hide-nav")
    }
    hideGalleryNav() {
        $(".gallery", this.context).addClass("hide-nav")
    }
}
class ExhibitPlugin {
    constructor({context, rootSelector, exhibit_mode}) {
        this.context = context
        this.rootSelector = rootSelector
        this.exhibit_mode = exhibit_mode
    }
    install({elem}) {
        const scrollEventOptions = this.rootSelector === "#kfroot" ? {capture: true} : undefined
        for (const btn of elem.querySelectorAll("[data-form-target]")) {
            btn.addEventListener("click", (evt) => {
                btn.closest("form").setAttribute(
                    "target",
                    btn.getAttribute("data-form-target"),
                )
            })
        }
        for (const siteWrapper of elem.querySelectorAll(".site-wrapper")) {
            // Function to update the --vh custom property
            const updateVH = () => {
                //console.log(updateVH)
                if (!elem.contains(siteWrapper)) {
                    window.removeEventListener("resize", updateVH)
                    return
                }
                if (siteWrapper) {
                    let vh = window.innerHeight / 100
                    siteWrapper.style.setProperty("--vh", `${vh}px`)
                }
            }

            // Scroll event handler for dynamically fading content
            const updateScrollOpacity = () => {
                //console.log('updateScrollOpacity')
                if (!this.context.contains(siteWrapper)) {
                    document.removeEventListener("scroll", updateScrollOpacity, scrollEventOptions)
                    return
                }

                let elements = elem.querySelectorAll(".scroll-opacity, .two-column__content")
                elements.forEach((element) => {
                    const viewportHeight = window.innerHeight
                    const elementTop = element.getBoundingClientRect().top
                    const distanceFromBottom = viewportHeight - elementTop
                    const percentageFromBottom =
                        (distanceFromBottom / viewportHeight) * 100
                    const start = 30
                    const end = 50
                    const opacity = (percentageFromBottom - start) * (100 / (end - start))
                    //console.log("two-column", {element, opacity, percentageFromBottom, start, end, elementTop, distanceFromBottom})
                    element.style.opacity = opacity / 100
                })

                elements = elem.querySelectorAll(".hero__title")
                elements.forEach((element) => {
                    const viewportHeight = window.innerHeight
                    const elementTop = element.getBoundingClientRect().top
                    const distanceFromBottom = viewportHeight - elementTop
                    const percentageFromBottom =
                        (distanceFromBottom / viewportHeight) * 100
                    const start = 80
                    const end = 100
                    const opacity =
                        100 - (percentageFromBottom - start) * (100 / (end - start))
                    //console.log("title", {element, opacity, percentageFromBottom, start, end, elementTop, distanceFromBottom})
                    element.style.opacity = opacity / 100
                })

                elements = elem.querySelectorAll(".hero__content")
                elements.forEach((element) => {
                    const viewportHeight = window.innerHeight
                    const elementTop = element.getBoundingClientRect().top
                    const distanceFromBottom = viewportHeight - elementTop
                    const percentageFromBottom =
                        (distanceFromBottom / viewportHeight) * 100
                    const start = 50
                    const end = 80
                    const opacity =
                        100 - (percentageFromBottom - start) * (100 / (end - start))
                    //console.log("hero__content", {element, opacity, percentageFromBottom, start, end, elementTop, distanceFromBottom})
                    element.style.opacity = opacity / 100
                })
            }

            AOS.init({
                disable: this.exhibit_mode === "light",
                once: true,
                rootNode: this.context,
                rootSelector: this.rootSelector,
                scrollEventOptions,
            })

            // Add event listeners
            document.addEventListener("scroll", updateScrollOpacity, scrollEventOptions)
            window.addEventListener("resize", updateVH)
        }
    }
}

// somehow this plugin was copied across branches and modified in both.
// These two map plugins work slightly differently.
class MapPlugin2 {
    constructor({context}) {
        this.context = context
    }
    install({elem}) {
        for (const map_elem of querySelectorAll({node: elem, selector: "[data-map2]"})) {
            const map = L.map(map_elem)
            const x = map_elem.getAttribute("data-x")
            const y = map_elem.getAttribute("data-y")
            const OpenStreetMap_Mapnik = L.tileLayer(
                "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                {
                    maxZoom: 19,
                    attribution:
                        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                },
            ).addTo(map)
            const position = [y, x]
            let marker = L.marker(position).addTo(map)
            map.setView(position, 20)
            this.context.addEventListener("kronofoto:map:marker:change", (evt) => {
                const position = [evt.detail.y, evt.detail.x]
                marker.setLatLng(position)
                map.setView(position, 20)
            })
        }
    }
}

class MapPlugin {
    constructor({context}) {
        this.context = context
    }
    install({elem}) {
        for (const mapelem of elem.querySelectorAll("[data-map]")) {
            const bounds = L.latLngBounds(
                L.latLng(
                    mapelem.getAttribute("data-south"),
                    mapelem.getAttribute("data-west"),
                ),
                L.latLng(
                    mapelem.getAttribute("data-north"),
                    mapelem.getAttribute("data-east"),
                ),
            )
            const map = L.map(document.querySelector("[data-map]"))
            var OpenStreetMap_Mapnik = L.tileLayer(
                "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                {
                    maxZoom: 19,
                    attribution:
                        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                },
            ).addTo(map)
            map.fitBounds(bounds)
            map.on("moveend", (evt) => {
                const bounds = evt.target.getBounds()
                const w = bounds.getWest()
                const e = bounds.getEast()
                const n = bounds.getNorth()
                const s = bounds.getSouth()
                const form = mapelem.closest("form")
                form.querySelector("[name='bounds:west']").value = w
                form.querySelector("[name='bounds:east']").value = e
                form.querySelector("[name='bounds:north']").value = n
                form.querySelector("[name='bounds:south']").value = s
                mapelem.dispatchEvent(
                    new Event("kronofoto:bounds_changed", {
                        bubbles: true,
                    }),
                )
            })
        }
    }
}

class PhotoSpherePlugin {
    constructor({context}) {
        this.context = context
    }
    install({elem}) {
        for (const elem2 of elem.querySelectorAll("[data-photosphere-data]")) {
            const api_url = elem2.getAttribute("data-node-href")
            const map_elem = elem.querySelector(elem2.getAttribute("data-map"))
            const param_name = elem2.getAttribute("data-node-param")
            const startNodeId = elem2.getAttribute("data-node-start")

            const viewer = new Viewer({
                container: elem2,
                plugins: [
                    [ImagePlanePlugin, {photos: []}],
                    MarkersPlugin,
                    [
                        VirtualTourPlugin,
                        {
                            dataMode: "server",
                            positionMode: "gps",
                            startNodeId,
                            getNode: async (nodeId) => {
                                const url = new URL(api_url)
                                url.searchParams.append(param_name, nodeId)
                                const resp = await fetch(url.toString())
                                return resp.json()
                            },
                            preload: true,
                            transitionOptions: (toNode, fromNode, fromLink) => ({
                                showLoader: true,
                                speed: "10rpm",
                                fadeIn: true,
                                rotation: true,
                                rotateTo: {
                                    yaw: `${90-toNode.data.photos[0].azimuth}deg`,
                                    pitch: `${toNode.data.photos[0].inclination}deg`,
                                },
                            }),
                        },
                    ],
                ],
            })
            const markersPlugin = viewer.getPlugin(MarkersPlugin)
            markersPlugin.addEventListener("select-marker", ({marker}) => {
                elem2.dispatchEvent(new CustomEvent("kronofoto-select-photosphere-marker", {detail: marker.data, bubbles: true}))
            })
            viewer
                .getPlugin(VirtualTourPlugin)
                .addEventListener("node-changed", ({node, data}) => {
                    //const slideScroller = new TimelineScroller({context: this.context})
                    //slideScroller.slideToId({
                    //    fi: node.data.photos[0].id,
                    //    target: "[data-fi-thumbnail-carousel-images]",
                    //})
                    const markersPlugin = viewer.getPlugin(MarkersPlugin)
                    markersPlugin.clearMarkers()
                    for (const infobox of node.data.infoboxes) {
                        markersPlugin.addMarker({
                            id: `marker-${infobox.id}`,
                            data: {id: infobox.id},
                            image: infobox.image,
                            position: {yaw: infobox.yaw, pitch: infobox.pitch},
                            size: {width: 32, height: 32},
                        })
                    }
                    viewer.getPlugin(ImagePlanePlugin).setPhotos(node.data.photos)
                    /*
                    const animate = Math.random() > 0.5
                    if (animate) {
                        viewer.animate({
                            yaw: `${90-node.data.photos[0].azimuth}deg`,
                            pitch: `${node.data.photos[0].inclination}deg`,
                            speed: "120rpm",
                        })
                        
                    } else {
                        viewer.rotate({
                            yaw: `${90-node.data.photos[0].azimuth}deg`,
                            pitch: `${node.data.photos[0].inclination}deg`,
                        })
                    }
                    */
                    if (data.fromNode && node.id != data.fromNode.id) {
                        const form = elem2.closest("form")
                        const input = form.querySelector("[name='id']")
                        input.value = node.id
                        elem2.dispatchEvent(
                            new Event("node-changed", {
                                bubbles: true,
                            }),
                        )
                    }
                })
        }
    }
}

class Zoom {
    constructor({context}) {
        this.context = context
    }

    install({elem}) {
        for (const elem2 of querySelectorAll({
            selector: "#follow-zoom-timeline-version",
            node: elem,
        })) {
            this.addZoom(elem2)
        }
    }
    addZoom(container) {
        let imgsrc = container.currentStyle || window.getComputedStyle(container, false)
        imgsrc = imgsrc.backgroundImage.slice(4, -1).replace(/"/g, "")
        const fullsize = container.getAttribute("data-fullsize")

        let img = new Image()
        let zoomOpened = false
        let zoomed = false
        let galleryElem = this.context.querySelector(".gallery")
        img.src = imgsrc
        img.onload = () => {
            let ratio = img.naturalWidth / img.naturalHeight

            Object.assign(container.style, {
                height: "calc(100vh)",
                width: "calc(100vw)",
                backgroundPosition: "top",
                backgroundSize: "contain",
                backgroundRepeat: "no-repeat",
            })

            let removeZoom = () => {
                Object.assign(container.style, {
                    backgroundPosition: "top",
                    backgroundSize: "contain",
                })
            }

            container.addEventListener("click", (e) => {
                zoomed = !zoomed

                if (zoomed) {
                    galleryElem.classList.add("zoomed")
                    const img2 = new Image()
                    img2.src = imgsrc
                    img2.onload = () => {
                        Object.assign(container.style, {
                            backgroundImage: `url("${fullsize}")`,
                        })
                    }
                    container.onmousemove(e)
                } else {
                    galleryElem.classList.remove("zoomed")
                    removeZoom()
                }
            })

            container.onmousemove = (e) => {
                if (zoomed) {
                    let rect = e.target.getBoundingClientRect(),
                        xPos = e.clientX - rect.left,
                        yPos = e.clientY - rect.top,
                        xPercent = (xPos / container.clientWidth) * 100 + "%",
                        yPercent = (yPos / container.clientHeight) * 100 + "%"

                    Object.assign(container.style, {
                        backgroundPosition: xPercent + " " + yPercent,
                        backgroundSize: window.innerWidth * 1.5 + "px",
                    })
                }
            }

            // container.onmouseleave = removeZoom
        }
    }
}

class KronofotoContext {
    constructor({htmx, context, rootSelector, exhibit_mode}) {
        this.htmx = htmx
        this.context = context
        this.rootSelector = rootSelector
        this.exhibit_mode = exhibit_mode
        this.context.addEventListener("htmx:configRequest", (evt) => {
            if (evt.target.hasAttribute("data-textcontent-name")) {
                evt.detail.parameters[evt.target.getAttribute("data-textcontent-name")] =
                    evt.target.textContent
            }
        })
    }
    onLoad(elem) {
        $("[data-autocomplete-url]", elem).each((_, input) => {
            const $input = $(input)
            $input.autocomplete({
                source: $input.data("autocomplete-url"),
                minLength: $input.data("autocomplete-min-length"),
            })
        })
        $("[data-select2-url]", elem).each((_, input) => {
            const $input = $(input)
            $input.select2({
                width: "300px",
                allowClear: true,
                minimumInputLength: 2,
                placeholder: $input.attr("placeholder"),
                ajax: {
                    delay: 250,
                    url: $input.data("select2-url"),
                    dataType: "json",
                },
            })
        })
        $(elem)
            .find(".form--add-tag .link--icon")
            .on("click", (e) => {
                let $form = $(e.currentTarget).closest("form")
                $form.addClass("expanded")
                $("input[type=text]", $form).get(0).focus()
            })
        // this logic should not be client side
        $(elem)
            .find("[data-save-list]")
            .on("submit", (e) => {
                // Check if logged in
                if ($("#login-btn", this.context).length) {
                    $("#login-btn", this.context).trigger("click")
                    showToast("You must login to continue")
                } else {
                    showToast("Updated photo lists")
                }
            })
        // the next three have some broken state.
        $("#overlay", elem).on("click", (e) => {
            this.htmx.trigger("#hamburger-button", "click")
            $("#overlay", this.context).fadeOut()
        })
        $("#hamburger-menu", elem)
            .on("off.zf.toggler", (e) => {
                $("#login", this.context).addClass("collapse")
                $("#overlay", this.context).fadeIn()
            })
            .on("on.zf.toggler", (e) => {
                if ($("#login", this.context).hasClass("collapse")) {
                    $("#overlay", this.context).fadeOut()
                }
            })

        // Close all dropdowns when clicking outside of a dropdown
        $(elem).on("click", (e) => {
            // Get the closest dropdown menu, if it exists
            var $parentDropdownMenu = $(e.target, elem).closest(".collection__item-menu")
            $(".collection__item-menu.expanded", elem).each((i, f) => {
                if (
                    !$parentDropdownMenu.length ||
                    $parentDropdownMenu.attr("id") != $(f).attr("id")
                ) {
                    $(f).foundation("toggle")
                }
            })
        })

        $("#login", elem)
            .on("off.zf.toggler", (e) => {
                $("#hamburger-menu", this.context).addClass("collapse")
                $("#overlay", this.context).fadeIn()
            })
            .on("on.zf.toggler", (e) => {
                if ($("#hamburger-menu", this.context).hasClass("collapse")) {
                    $("#overlay", this.context).fadeOut()
                }
            })
        $("#auto-play-image-control-button", elem).on("click", (e) => {
            let $btn = e.currentTarget
            $btn.classList.toggle("active")
            if ($btn.classList.contains("active")) {
                this.autoplayStart($btn)
            } else {
                this.autoplayStop()
            }
        })
        $(elem)
            .find(".image-control-button--toggle")
            .on("click", (e) => {
                let $btn = $(e.currentTarget)
                $("img", $btn).toggleClass("hide")
            })
        const plugins = [
            BackwardScroller,
            ForwardScroller,
            timeline,
            TimelineScroller,
            Zoom,
            Gallery,
            ImagePreviewInput,
            PhotoSpherePlugin,
            CopyLink,
            PageEditor,
            ExhibitPlugin,
            MapPlugin,
            MapPlugin2,
        ]
        for (const cls of plugins) {
            const plugin = new cls({context: this.context, rootSelector: this.rootSelector, exhibit_mode: this.exhibit_mode})
            plugin.install({elem})
        }

        initNavSearch(elem)
        // modified this foundation function to attach a "rootNode" variable to all plugin objects.
        // The foundation function already accepts one optional argument, so undefined is passed to preserve
        // the old behavior.
        $(elem).foundation(undefined, this.context)
        if (
            window.st &&
            elem.querySelectorAll(".sharethis-inline-share-buttons").length
        ) {
            st.initialize()
        }

        // Init gallery thumbnails
        if (elem.id == "fi-preload-zone") {
            const slideScroller = new TimelineScroller({context: this.context})
            slideScroller.slideToId({
                fi: elem.getAttribute("data-slide-id"),
                target: "[data-fi-thumbnail-carousel-images]",
            })
            setTimeout(() => {
                let html = elem.innerHTML
                // let firstId = $(html).find('li:first-child span').attr('hx-get')
                const carouselImages = elem.parentNode.querySelector(
                    "#fi-thumbnail-carousel-images",
                )
                carouselImages.innerHTML = html
                carouselImages.classList.add("dragging")
                carouselImages.style.left = "0px"
                setTimeout(() => {
                    carouselImages.classList.remove("dragging")
                }, 100)

                this.htmx.process(carouselImages)
                elem.replaceChildren()
            }, 250)
        }
        $("#fi-image", elem).on("click", () => console.log("clicked"))

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
    initTimeline(elem) {
        $(".photos-timeline", elem).each((i, e) => {
            const timelineInstance = new timeline()
            timelineInstance.connect(e, this.context)
        })
    }
    autoplayStart(elem) {
        // should change `window` to `this`
        window.autoplayTimer = setInterval(
            (elem) => {
                if (elem.isConnected) {
                    this.htmx.trigger("#fi-arrow-right", "click")
                } else {
                    clearInterval(window.autoplayTimer)
                }
            },
            5000,
            elem,
        )
    }
    autoplayStop() {
        clearInterval(window.autoplayTimer)
    }
}
export const initHTMXListeners = (_htmx, context, {lateLoad = false, rootSelector = "body", exhibit_mode=""} = {}) => {
    // context here means our root element
    // necessary?
    $(context).on("click", (e) => {
        if (!$(".form--add-tag input", context).is(":focus")) {
            let $form = $(".form--add-tag input", context).closest("form")
            $form.removeClass("expanded")
        }
    })

    // context here means our root element and this would probably be simpler with server side templates.
    $(context).on("on.zf.toggler", function (e) {
        if ($(e.target).hasClass("gallery__popup")) {
            $(
                ".gallery__popup.expanded:not(#" + $(e.target).attr("id") + ")",
            ).removeClass("expanded")
        }
    })

    const instance = new KronofotoContext({htmx: _htmx, context, rootSelector, exhibit_mode})
    if (lateLoad) {
        instance.onLoad(context)
    }
    _htmx.onLoad(instance.onLoad.bind(instance))
    _htmx.onLoad(() => {
        if (window["AOS"]) {
            AOS.refreshHard()
        }
    })
}
export function initFoundation(context) {
    Foundation.addToJquery($)
    Foundation.Box = Box
    Foundation.MediaQuery = MediaQuery
    Foundation.Motion = Motion
    Foundation.Move = Move

    Triggers.init($, Foundation, context)
    Foundation.plugin(Toggler, "Toggler")
    Foundation.plugin(Tooltip, "Tooltip")
    Foundation.plugin(Reveal, "Reveal")
}

export function initClipboardJS(context) {
    $(context).on("click", ".copy-button", (e) => {
        let target = $(e.currentTarget).attr("data-clipboard-target")
        let text = $(target).val()
        ClipboardActionCopy(text)
        showToast("The link has been copied to the clipboard.")
        $(target).select()
        $(target)[0].setSelectionRange(0, 999999)
    })
}
export function collapseNavSearch(elem) {
    return () => {
        $("#search-box-container", elem).removeClass("expanded")
        $(".search-form", elem).hide()
        $("#search-box", elem).val("")
        $(".search-icon", elem).css("filter", "none")
        $(".carrot", elem).css("filter", "none")
        $("#search-box", elem).removeClass("placeholder-light").css("color", "#333")
    }
}

export function expandNavSearch(elem) {
    return () => {
        $("#search-box-container", elem).addClass("expanded")
        $(".search-form", elem).show()
        $(".search-icon", elem).css("filter", "brightness(0) invert(1)")
        $(".carrot", elem).css("filter", "brightness(0) invert(1)")
        $("#search-box", elem).addClass("placeholder-light").css("color", "white")
    }
}
export function initNavSearch(elem) {
    $(".search-form__clear-btn", elem).click((e) => {
        e.preventDefault()
        $("#search-box", elem).val("")
        $(".search-form input[type=text]", elem).val("")
        $(".search-form select", elem).val("")
    })
    $("#search-box", elem).click(expandNavSearch(elem))
    $("#search-box-container .close-icon", elem).click(collapseNavSearch(elem))
}

export function showToast(message) {
    let content = $("#toast-template").html()
    let $message = $(content)
    $message.prepend("<p>" + message + "</p>")
    $("#messages").append($message)
    setTimeout(() => {
        $message.fadeOut(() => {
            $message.remove()
        })
    }, 5000)
}

let moreThumbnailsLoading = false

export function toggleLogin(evt) {
    const el = document.querySelector("#login")
    toggleElement(el)
}
export function toggleMenu(evt) {
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

function toggleElement(el) {
    if (!el.classList.replace("hidden", "gridden")) {
        el.classList.replace("gridden", "hidden")
    }
}

export const installButtons = (root) => (content) => {
    const elems = Array.from(content.querySelectorAll("[data-popup-target]"))

    if (content.hasAttribute("data-popup-target")) {
        elems.push(content)
    }

    for (const elem of elems) {
        const datatarget = elem.getAttribute("data-popup-target")
        elem.addEventListener("click", (evt) => {
            for (const target of root.querySelectorAll("[data-popup]")) {
                if (target.hasAttribute(datatarget)) {
                    target.classList.remove("hidden")
                } else {
                    target.classList.add("hidden")
                }
            }
            elem.dispatchEvent(
                new Event(datatarget, {
                    bubbles: true,
                }),
            )
        })
    }
}
