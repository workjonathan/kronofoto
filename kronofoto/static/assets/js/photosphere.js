import GUI from "./lil-gui.esm.min.js"
import {AbstractPlugin, events} from "@photo-sphere-viewer/core"
import * as THREE from "three"

export const toRadians = (degrees) => (2 * Math.PI * degrees) / 360

export class ImagePlanePlugin extends AbstractPlugin {
    static id = "image-plane-plugin"
    constructor(viewer, config) {
        super(viewer)
        this.config = config
        this.meshes = []
    }
    init() {
        this.viewer.addEventListener(events.PanoramaLoadedEvent.type, this, {
            once: true,
        })
    }
    destroy() {
        this.viewer.removeEventListener(events.PanoramaLoadedEvent.type, this)
        super.destroy()
    }
    setPhotos(photos) {
        for (const mesh of this.meshes) {
            this.viewer.renderer.removeObject(mesh)
        }
        this.meshes = []
        for (const photo of photos) {
            this.azimuth = photo.azimuth
            this.inclination = photo.inclination
            this.distance = photo.distance
            this.azimuth_el = photo.azimuth_el
            this.inclination_el = photo.inclination_el
            this.distance_el = photo.distance_el
            new THREE.TextureLoader().load(photo.url, (texture) => {
                this.geometry = new THREE.PlaneGeometry(
                    photo.width / 2000,
                    photo.height / 2000,
                )
                this.material = new THREE.MeshBasicMaterial({
                    transparent: true,
                    map: texture,
                })
                this.material.opacity = 1
                this.mesh = new THREE.Mesh(this.geometry, this.material)
                this.meshes.push(this.mesh)
                this.updatePosition()
                this.viewer.renderer.addObject(this.mesh)
                this.viewer.needsUpdate()
                if (photo.container) {
                    const gui = new GUI({container: photo.container, width: 400})
                    gui.domElement.addEventListener("mousedown", (evt) =>
                        evt.stopPropagation(),
                    )
                    gui.add(this.material, "opacity", 0, 1).onChange(
                        this.viewer.needsUpdate.bind(this.viewer),
                    )
                    const posFolder = gui.addFolder("Position")
                    posFolder
                        .add(this, "azimuth", -180, 180)
                        .onChange(this.updatePosition.bind(this))
                    posFolder
                        .add(this, "inclination", -90, 90)
                        .onChange(this.updatePosition.bind(this))
                    posFolder
                        .add(this, "distance", 10, 2000)
                        .onChange(this.updatePosition.bind(this))
                }
            })
        }
    }
    handleEvent(e) {
        if (e instanceof events.PanoramaLoadedEvent) {
            this.setPhotos(this.config.photos)
        }
    }
    updatePosition() {
        const distance = this.distance / 2000
        const theta = toRadians(this.inclination - 90)
        const phi = toRadians(this.azimuth + 90)
        const z = Math.cos(phi) * Math.sin(theta) * distance
        const x = Math.sin(phi) * Math.sin(theta) * distance
        const y = Math.cos(theta) * distance
        this.mesh.position.set(x, y, z)
        this.mesh.lookAt(0, 0, 0)
        if (this.azimuth_el) {
            this.azimuth_el.setAttribute("value", this.azimuth)
        }
        if (this.inclination_el) {
            this.inclination_el.setAttribute("value", this.inclination)
        }
        if (this.distance_el) {
            this.distance_el.setAttribute("value", this.distance)
        }
        this.viewer.needsUpdate()
    }
}
/*export default class PhotoSphere {
    constructor({element, sphere, input=undefined, azimuth_el=undefined, inclination_el=undefined, distance_el=undefined}) {
        this.azimuth_el = input || azimuth_el
        this.inclination_el = inclination_el
        this.distance_el = distance_el
        this.panorama = new PANOLENS.ImagePanorama(sphere)
        this.viewer = new PANOLENS.Viewer({container: element, output: 'console'})
        this.viewer.add(this.panorama)
    }

    addHeadingSphere({color=0xff9999, azimuth=0, container} = {}) {
        this.azimuth = azimuth
        this.inclination = 0
        this.distance = 500
        this.geometry = new THREE.SphereGeometry(10, 32, 16)
        this.material = new THREE.MeshBasicMaterial({color})
        this.mesh = new THREE.Mesh(this.geometry, this.material)
        this.updatePosition()
        this.viewer.add(this.mesh)
        const gui = new GUI({container})
        gui.domElement.addEventListener('mousedown', evt => evt.stopPropagation())
        gui.add(this, "azimuth", -180, 180).onChange(this.updatePosition.bind(this))
    }

    addPhoto({url, width, height, azimuth=0, inclination=0, distance=500, container=undefined}) {
        this.azimuth = azimuth
        this.inclination = inclination
        this.distance = distance
        const texture = new THREE.TextureLoader().load(url)
        this.geometry = new THREE.PlaneGeometry(width, height)
        this.material = new THREE.MeshBasicMaterial({transparent: true, map: texture})
        this.material.opacity = 1
        this.mesh = new THREE.Mesh(this.geometry, this.material)
        this.updatePosition()
        this.viewer.add(this.mesh)
        if (container) {
            const gui = new GUI({container, width: 400})
            gui.domElement.addEventListener('mousedown', evt => evt.stopPropagation())
            gui.add(this.material, "opacity", 0, 1)
            const posFolder = gui.addFolder("Position")
            posFolder.add(this, "azimuth", -180, 180).onChange(this.updatePosition.bind(this))
            posFolder.add(this, "inclination", -180, 180).onChange(this.updatePosition.bind(this))
            posFolder.add(this, "distance", 10, 2000).onChange(this.updatePosition.bind(this))
        }
    }

    updatePosition() {
        const theta = toRadians(this.inclination - 90)
        const phi = toRadians(this.azimuth)
        const z = Math.cos(phi) * Math.sin(theta) * this.distance
        const x = Math.sin(phi) * Math.sin(theta) * this.distance
        const y = Math.cos(theta) * this.distance
        this.mesh.position.set(x, y, z)
		this.mesh.lookAt(0,0,0)
        if (this.azimuth_el) {
            this.azimuth_el.setAttribute("value", this.azimuth)
        }
        if (this.inclination_el) {
            this.inclination_el.setAttribute("value", this.inclination)
        }
        if (this.distance_el) {
            this.distance_el.setAttribute("value", this.distance)
        }
    }
}
*/
