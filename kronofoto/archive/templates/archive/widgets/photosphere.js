
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
	const toRadians = degrees => 2*Math.PI*degrees/360
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
initMap()

