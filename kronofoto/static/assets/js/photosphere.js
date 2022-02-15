import GUI from "./lil-gui.esm.min.js"

const toRadians = degrees => 2*Math.PI*degrees/360


export default class PhotoSphere {
    constructor({element, sphere, input=undefined, azimuth_el=undefined, inclination_el=undefined, distance_el=undefined}) {
        console.log({azimuth_el})
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

    addPhoto({url, width, height, azimuth=0, inclination=0, distance=500, container} = {}) {
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
        const gui = new GUI({container, width: 400})
        gui.domElement.addEventListener('mousedown', evt => evt.stopPropagation())
        gui.add(this.material, "opacity", 0, 1)
        const posFolder = gui.addFolder("Position")
        posFolder.add(this, "azimuth", -180, 180).onChange(this.updatePosition.bind(this))
        posFolder.add(this, "inclination", -180, 180).onChange(this.updatePosition.bind(this))
        posFolder.add(this, "distance", 10, 2000).onChange(this.updatePosition.bind(this))
    }

    updatePosition() {
        const theta = toRadians(this.inclination - 90)
        const phi = toRadians(this.azimuth)
        const z = Math.cos(phi) * Math.sin(theta) * this.distance
        const x = Math.sin(phi) * Math.sin(theta) * this.distance
        const y = Math.cos(theta) * this.distance
        this.mesh.position.set(x, y, z)
		this.mesh.lookAt(0,0,0)
        this.azimuth_el.setAttribute("value", this.azimuth)
        if (this.inclination_el) {
            this.inclination_el.setAttribute("value", this.inclination)
        }
        if (this.distance_el) {
            this.distance_el.setAttribute("value", this.distance)
        }
    }
}

function initMap() {
	let mesh
	const container = document.querySelector( '#{{ id }}_sphere' )
	const panorama = new PANOLENS.ImagePanorama( 'StudyingCamponile_360.jpg' )
	let viewer = undefined
	const texture = new THREE.TextureLoader().load('StudyingCamponile_Historical.jpg')
	const geometry = new THREE.PlaneGeometry(502, 833)
	const material = new THREE.MeshBasicMaterial({transparent: true, map: texture})
	material.opacity = 1
	mesh = new THREE.Mesh(geometry, material)
	const position = {
		azimuth: 0,
		inclination: 0,
		distance: 500,
	}
	const rotation = {
		x: 0,
		y: 0,
		z: 0,
	}
	function updatePosition() {
		const theta = toRadians(position.inclination - 90)
		const phi = toRadians(position.azimuth)
		const z = Math.cos(phi) * Math.sin(theta) * position.distance
		const x = Math.sin(phi) * Math.sin(theta) * position.distance
		const y = Math.cos(theta) * position.distance
		mesh.position.set(x, y, z)
		mesh.lookAt(0,0,0)
		mesh.rotation.set(mesh.rotation.x + toRadians(rotation.x), mesh.rotation.y + toRadians(rotation.y), mesh.rotation.z + toRadians(rotation.z), "XYZ")
	}
	updatePosition()
	const gui = new GUI({ width: 800 })
	gui.add(material, "opacity", 0, 1)
	const posFolder = gui.addFolder("Position")
	posFolder.add(position, "azimuth", -180, 180).onChange(updatePosition)
	posFolder.add(position, "inclination", -90, 90).onChange(updatePosition)
	posFolder.add(position, "distance", 10, 2000).onChange(updatePosition)
	
	const rotFolder = gui.addFolder("Rotation")
	rotFolder.add(rotation, "x", -180, 180).onChange(updatePosition)
	rotFolder.add(rotation, "y", -180, 180).onChange(updatePosition)
	rotFolder.add(rotation, "z", -180, 180).onChange(updatePosition)

	viewer = new PANOLENS.Viewer( { container: container, output: 'console' } )


	viewer.add(panorama)
	viewer.add(mesh)
}
