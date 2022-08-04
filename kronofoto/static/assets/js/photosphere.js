import GUI from "./lil-gui.esm.min.js"

const toRadians = degrees => 2*Math.PI*degrees/360


export default class PhotoSphere {
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

