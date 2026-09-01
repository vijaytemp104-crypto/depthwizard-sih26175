import React, { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const CAMERA_POSITION = new THREE.Vector3(5.8, 4.4, 6.2)
const TARGET_POSITION = new THREE.Vector3(0, 0, 0)
const DEMO_VERTICAL_EXAGGERATION = 1.8

function validateTerrain(terrain) {
  if (!terrain) return { valid: false, message: 'Terrain data has not arrived yet.' }
  const { width, height, heights } = terrain
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 2 || height < 2) {
    return { valid: false, message: 'Terrain grid dimensions must be at least 2 × 2.' }
  }
  if (!Array.isArray(heights) || heights.length !== height) {
    return { valid: false, message: 'Terrain rows do not match the declared height.' }
  }
  const values = []
  for (const row of heights) {
    if (!Array.isArray(row) || row.length !== width) {
      return { valid: false, message: 'Terrain columns do not match the declared width.' }
    }
    for (const value of row) {
      if (!Number.isFinite(value)) return { valid: false, message: 'Terrain contains a non-numeric height value.' }
      values.push(value)
    }
  }
  return { valid: true, values }
}

function ViewerCanvas({ terrain, textureUrl, onViewerError }) {
  const containerRef = useRef(null)
  const resetRef = useRef(null)

  useEffect(() => {
    const container = containerRef.current
    const validation = validateTerrain(terrain)
    if (!container || !validation.valid) return undefined

    let renderer
    let frameId
    let disposed = false
    let terrainTexture = null
    try {
      const scene = new THREE.Scene()
      scene.background = new THREE.Color(0x081522)
      scene.fog = new THREE.Fog(0x081522, 11, 22)

      const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100)
      camera.position.copy(CAMERA_POSITION)

      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      renderer.outputColorSpace = THREE.SRGBColorSpace
      renderer.shadowMap.enabled = true
      container.appendChild(renderer.domElement)

      const controls = new OrbitControls(camera, renderer.domElement)
      controls.enableDamping = true
      controls.dampingFactor = 0.07
      controls.enablePan = true
      controls.minDistance = 3.5
      controls.maxDistance = 18
      controls.maxPolarAngle = Math.PI * 0.48
      controls.target.copy(TARGET_POSITION)

      const horizontalSize = 6
      const depthSize = horizontalSize * ((terrain.height - 1) / (terrain.width - 1))
      const geometry = new THREE.PlaneGeometry(horizontalSize, depthSize, terrain.width - 1, terrain.height - 1)
      geometry.rotateX(-Math.PI / 2)

      const minimum = Math.min(...validation.values)
      const maximum = Math.max(...validation.values)
      const range = maximum - minimum || 1
      const positions = geometry.attributes.position
      validation.values.forEach((value, index) => {
        const normalized = (value - minimum) / range
        positions.setY(index, (normalized - 0.5) * DEMO_VERTICAL_EXAGGERATION)
      })
      positions.needsUpdate = true
      geometry.computeVertexNormals()

      const material = new THREE.MeshStandardMaterial({
        color: 0x2a7b89,
        roughness: 0.76,
        metalness: 0.03,
        side: THREE.DoubleSide,
      })
      const terrainMesh = new THREE.Mesh(geometry, material)
      terrainMesh.castShadow = true
      terrainMesh.receiveShadow = true
      scene.add(terrainMesh)

      const wireGeometry = new THREE.WireframeGeometry(geometry)
      const wireMaterial = new THREE.LineBasicMaterial({ color: 0x80dce5, transparent: true, opacity: 0.32 })
      const wireframe = new THREE.LineSegments(wireGeometry, wireMaterial)
      terrainMesh.add(wireframe)

      if (textureUrl) {
        new THREE.TextureLoader().load(
          textureUrl,
          (loadedTexture) => {
            if (disposed) {
              loadedTexture.dispose()
              return
            }
            terrainTexture = loadedTexture
            terrainTexture.colorSpace = THREE.SRGBColorSpace
            terrainTexture.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 8)
            material.map = terrainTexture
            material.color.set(0xffffff)
            material.needsUpdate = true
          },
          undefined,
          () => {
            if (!disposed) onViewerError('The selected image could not be used as a texture; neutral terrain shading is shown.')
          },
        )
      }

      scene.add(new THREE.HemisphereLight(0xbdebf2, 0x132332, 2.2))
      const keyLight = new THREE.DirectionalLight(0xffffff, 2.5)
      keyLight.position.set(4, 8, 3)
      keyLight.castShadow = true
      scene.add(keyLight)

      const grid = new THREE.GridHelper(9, 12, 0x2b6470, 0x183744)
      grid.position.y = -1.05
      scene.add(grid)

      const resetCamera = () => {
        camera.position.copy(CAMERA_POSITION)
        controls.target.copy(TARGET_POSITION)
        controls.update()
      }
      resetRef.current = resetCamera

      const resize = () => {
        const width = Math.max(container.clientWidth, 1)
        const height = Math.max(container.clientHeight, 1)
        renderer.setSize(width, height, false)
        camera.aspect = width / height
        camera.updateProjectionMatrix()
      }
      const resizeObserver = new ResizeObserver(resize)
      resizeObserver.observe(container)
      resize()

      const render = () => {
        controls.update()
        renderer.render(scene, camera)
        frameId = window.requestAnimationFrame(render)
      }
      render()

      return () => {
        disposed = true
        window.cancelAnimationFrame(frameId)
        resizeObserver.disconnect()
        controls.dispose()
        terrainTexture?.dispose()
        wireGeometry.dispose()
        wireMaterial.dispose()
        geometry.dispose()
        material.dispose()
        renderer.dispose()
        renderer.domElement.remove()
        resetRef.current = null
      }
    } catch {
      renderer?.dispose()
      onViewerError('WebGL could not initialize for MissionView on this device.')
      return undefined
    }
  }, [terrain, textureUrl, onViewerError])

  return (
    <div className="mission-canvas-wrap">
      <div ref={containerRef} className="mission-canvas" aria-label="Interactive terrain viewer" />
      <button className="viewer-reset" type="button" onClick={() => resetRef.current?.()}>Reset view</button>
      <div className="viewer-hint">Drag to orbit · Scroll to zoom · Right-drag to pan</div>
    </div>
  )
}

function MissionView({ terrain, textureUrl, mock = false, state = 'empty', errorMessage = '' }) {
  const [viewerError, setViewerError] = useState('')
  const validation = validateTerrain(terrain)
  const isReady = state === 'succeeded' && validation.valid

  let fallback = 'Run the demo pipeline to create synthetic terrain.'
  if (state === 'pending' || state === 'running' || state === 'loading') fallback = 'Terrain is waiting for the demo pipeline to finish.'
  if (state === 'failed' || state === 'error') fallback = errorMessage || 'The synthetic terrain could not be prepared.'
  if (state === 'succeeded' && !validation.valid) fallback = validation.message

  return (
    <article className="stage-card mission-view-card">
      <div className="mission-view-header">
        <div><p className="micro-label">05 · Spatial inspection</p><h3>3D MissionView</h3></div>
        <div className="mission-badges">{mock
          ? <><span>DEMO</span><span>SYNTHETIC TERRAIN</span><span>NOT METRIC</span></>
          : <><span>CALIBRATED DSM</span><span>METRIC TERRAIN</span><span>GEOREFERENCED</span></>}</div>
      </div>
      {isReady ? (
        <>
          <ViewerCanvas terrain={terrain} textureUrl={textureUrl} onViewerError={setViewerError} />
          <div className="mission-meta">
            <span>{terrain.width} × {terrain.height} row-major grid</span>
            <span>{terrain.height_units || 'units unavailable'}</span>
            <span>{terrain.coordinate_mode || 'coordinate mode unavailable'}</span>
            <span>{textureUrl ? 'Local input texture' : 'Neutral material'}</span>
          </div>
          <p className="mission-note">Row 0 maps to the far edge of the plane. Vertical exaggeration is visual only ({DEMO_VERTICAL_EXAGGERATION} scene units across the normalized demo range).</p>
          {viewerError && <p className="mission-warning" role="status">{viewerError}</p>}
        </>
      ) : (
        <div className="mission-fallback"><span aria-hidden="true">05</span><strong>{state === 'running' ? 'Preparing demo terrain' : 'MissionView unavailable'}</strong><p>{fallback}</p></div>
      )}
      {!mock && isReady && <p className="mission-warning">Metric terrain is calibration output. Independent validation is not integrated yet.</p>}
    </article>
  )
}

export default MissionView
