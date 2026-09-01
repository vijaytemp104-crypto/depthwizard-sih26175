import React, { useCallback, useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js'
import { heightMeasurement, measurementUnits, prepareTerrainGrid, slopeMeasurement } from '../analysis.js'

const CAMERA_POSITION = new THREE.Vector3(5.8, 4.4, 6.2)
const TARGET_POSITION = new THREE.Vector3(0, 0, 0)
const VERTICAL_EXAGGERATION = 1.8

function validateTerrain(terrain) {
  return prepareTerrainGrid(terrain)
}

function ViewerCanvas({ terrain, textureUrl, navigationMode, measurementMode, onPoint, onViewerError }) {
  const containerRef = useRef(null)
  const resetRef = useRef(null)
  const flyRef = useRef(null)
  useEffect(() => {
    const container = containerRef.current
    const validation = validateTerrain(terrain)
    if (!container || !validation.valid) return undefined
    let renderer
    let frameId
    let terrainTexture = null
    let disposed = false
    const keys = new Set()
    let previousTime = performance.now()
    try {
      const scene = new THREE.Scene()
      scene.background = new THREE.Color(0x081522)
      scene.fog = new THREE.Fog(0x081522, 11, 22)
      const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100)
      camera.position.copy(CAMERA_POSITION)
      renderer = new THREE.WebGLRenderer({ antialias: true })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      renderer.outputColorSpace = THREE.SRGBColorSpace
      renderer.shadowMap.enabled = true
      container.appendChild(renderer.domElement)
      const orbit = new OrbitControls(camera, renderer.domElement)
      orbit.enableDamping = true
      orbit.enablePan = true
      orbit.minDistance = 3.5
      orbit.maxDistance = 18
      orbit.maxPolarAngle = Math.PI * 0.48
      orbit.target.copy(TARGET_POSITION)
      orbit.enabled = navigationMode === 'orbit'
      const fly = new PointerLockControls(camera, renderer.domElement)
      flyRef.current = () => fly.lock()

      const width = 6
      const depth = width * ((terrain.height - 1) / (terrain.width - 1))
      const geometry = new THREE.PlaneGeometry(width, depth, terrain.width - 1, terrain.height - 1)
      geometry.rotateX(-Math.PI / 2)
      const minimum = Math.min(...validation.values)
      const range = Math.max(...validation.values) - minimum || 1
      const positions = geometry.attributes.position
      validation.values.forEach((value, index) => positions.setY(index, ((value - minimum) / range - 0.5) * VERTICAL_EXAGGERATION))
      positions.needsUpdate = true
      geometry.computeVertexNormals()
      const material = new THREE.MeshStandardMaterial({ color: 0x2a7b89, roughness: 0.76, side: THREE.DoubleSide })
      const mesh = new THREE.Mesh(geometry, material)
      scene.add(mesh)
      const wireGeometry = new THREE.WireframeGeometry(geometry)
      const wireMaterial = new THREE.LineBasicMaterial({ color: 0x80dce5, transparent: true, opacity: 0.32 })
      mesh.add(new THREE.LineSegments(wireGeometry, wireMaterial))
      const markerGeometry = new THREE.SphereGeometry(0.075, 12, 8)
      const markerMaterials = [new THREE.MeshBasicMaterial({ color: 0xffbd55 }), new THREE.MeshBasicMaterial({ color: 0xff6f91 })]
      const markers = []
      const raycaster = new THREE.Raycaster()
      const pointer = new THREE.Vector2()
      const pick = (event) => {
        if (measurementMode === 'none' || navigationMode === 'fly' || fly.isLocked) return
        const bounds = renderer.domElement.getBoundingClientRect()
        pointer.set(((event.clientX - bounds.left) / bounds.width) * 2 - 1, -((event.clientY - bounds.top) / bounds.height) * 2 + 1)
        raycaster.setFromCamera(pointer, camera)
        const hit = raycaster.intersectObject(mesh, false)[0]
        if (!hit) return
        const local = mesh.worldToLocal(hit.point.clone())
        const column = Math.max(0, Math.min(terrain.width - 1, Math.round((local.x / width + 0.5) * (terrain.width - 1))))
        const row = Math.max(0, Math.min(terrain.height - 1, Math.round((local.z / depth + 0.5) * (terrain.height - 1))))
        const index = row * terrain.width + column
        if (!validation.validMask[index]) {
          onViewerError('That displayed sample is nodata and cannot be used for measurement.')
          return
        }
        if (markers.length === 2) markers.splice(0).forEach((marker) => scene.remove(marker))
        const marker = new THREE.Mesh(markerGeometry, markerMaterials[markers.length])
        marker.position.set(positions.getX(index), positions.getY(index) + 0.08, positions.getZ(index))
        scene.add(marker)
        markers.push(marker)
        onPoint({ row, column, elevation: terrain.heights[row][column] })
      }
      renderer.domElement.addEventListener('click', pick)
      if (textureUrl) new THREE.TextureLoader().load(textureUrl, (loaded) => {
        if (disposed) return loaded.dispose()
        terrainTexture = loaded
        loaded.colorSpace = THREE.SRGBColorSpace
        material.map = loaded
        material.color.set(0xffffff)
        material.needsUpdate = true
      }, undefined, () => !disposed && onViewerError('Input texture unavailable; neutral terrain shading is shown.'))
      scene.add(new THREE.HemisphereLight(0xbdebf2, 0x132332, 2.2))
      const light = new THREE.DirectionalLight(0xffffff, 2.5)
      light.position.set(4, 8, 3)
      scene.add(light)
      const grid = new THREE.GridHelper(9, 12, 0x2b6470, 0x183744)
      grid.position.y = -1.05
      scene.add(grid)
      resetRef.current = () => { fly.unlock(); camera.position.copy(CAMERA_POSITION); orbit.target.copy(TARGET_POSITION); orbit.update() }
      const keyDown = (event) => keys.add(event.code)
      const keyUp = (event) => keys.delete(event.code)
      window.addEventListener('keydown', keyDown)
      window.addEventListener('keyup', keyUp)
      const resize = () => { const w = Math.max(container.clientWidth, 1); const h = Math.max(container.clientHeight, 1); renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix() }
      const observer = new ResizeObserver(resize)
      observer.observe(container)
      resize()
      const render = (time = performance.now()) => {
        const delta = Math.min((time - previousTime) / 1000, 0.05)
        previousTime = time
        if (navigationMode === 'fly' && fly.isLocked) {
          const speed = (keys.has('ShiftLeft') || keys.has('ShiftRight') ? 6 : 2.5) * delta
          if (keys.has('KeyW')) fly.moveForward(speed)
          if (keys.has('KeyS')) fly.moveForward(-speed)
          if (keys.has('KeyA')) fly.moveRight(-speed)
          if (keys.has('KeyD')) fly.moveRight(speed)
          if (keys.has('Space') || keys.has('KeyE')) camera.position.y += speed
          if (keys.has('ControlLeft') || keys.has('KeyQ')) camera.position.y -= speed
        } else orbit.update()
        renderer.render(scene, camera)
        frameId = requestAnimationFrame(render)
      }
      render()
      return () => {
        disposed = true
        cancelAnimationFrame(frameId)
        observer.disconnect()
        window.removeEventListener('keydown', keyDown)
        window.removeEventListener('keyup', keyUp)
        renderer.domElement.removeEventListener('click', pick)
        fly.unlock(); fly.disconnect(); orbit.dispose(); terrainTexture?.dispose()
        markerGeometry.dispose(); markerMaterials.forEach((item) => item.dispose())
        wireGeometry.dispose(); wireMaterial.dispose(); geometry.dispose(); material.dispose(); renderer.dispose(); renderer.domElement.remove()
        resetRef.current = null; flyRef.current = null
      }
    } catch {
      renderer?.dispose()
      onViewerError('WebGL could not initialize for MissionView on this device.')
      return undefined
    }
  }, [terrain, textureUrl, navigationMode, measurementMode, onPoint, onViewerError])
  return <div className="mission-canvas-wrap">
    <div ref={containerRef} className="mission-canvas" aria-label="Interactive terrain viewer" />
    <div className="viewer-actions">{navigationMode === 'fly' && <button className="viewer-reset" type="button" onClick={() => flyRef.current?.()}>Enter fly view</button>}<button className="viewer-reset" type="button" onClick={() => resetRef.current?.()}>Reset view</button></div>
    <div className="viewer-hint">{navigationMode === 'fly' ? 'Enter fly view · WASD move · mouse look · Space/E up · Ctrl/Q down · Shift faster · Esc exit' : measurementMode === 'none' ? 'Drag to orbit · Scroll to zoom · Right-drag to pan' : 'Click two displayed terrain samples to measure'}</div>
  </div>
}

const format = (value) => Number.isFinite(value) ? value.toFixed(3) : '—'

function MissionViewAnalysis({ terrain, textureUrl, mock = false, state = 'empty', errorMessage = '' }) {
  const [viewerError, setViewerError] = useState('')
  const [navigationMode, setNavigationMode] = useState('orbit')
  const [measurementMode, setMeasurementMode] = useState('none')
  const [points, setPoints] = useState([])
  const validation = validateTerrain(terrain)
  const ready = state === 'succeeded' && validation.valid
  const addPoint = useCallback((point) => setPoints((current) => current.length >= 2 ? [point] : [...current, point]), [])
  const selectMeasurement = (mode) => { setMeasurementMode(mode); setPoints([]); if (mode !== 'none') setNavigationMode('orbit') }
  const result = points.length === 2 ? measurementMode === 'height' ? heightMeasurement(points[0], points[1], terrain) : slopeMeasurement(points[0], points[1], terrain) : null
  const units = measurementUnits(terrain)
  let fallback = 'Run the pipeline to prepare terrain.'
  if (['pending', 'running', 'loading'].includes(state)) fallback = 'Terrain is waiting for the pipeline to finish.'
  if (['failed', 'error'].includes(state)) fallback = errorMessage || 'Terrain could not be prepared.'
  if (state === 'succeeded' && !validation.valid) fallback = validation.message
  return <article className="stage-card mission-view-card">
    <div className="mission-view-header"><div><p className="micro-label">05 · Spatial inspection</p><h3>3D MissionView</h3></div><div className="mission-badges">{mock ? <><span>DEMO</span><span>SYNTHETIC TERRAIN</span><span>NOT METRIC</span></> : <><span>CALIBRATED DSM</span><span>METRIC TERRAIN</span><span>GEOREFERENCED</span></>}</div></div>
    {ready ? <>
      <div className="navigation-toolbar"><strong>Navigation</strong><button className={navigationMode === 'orbit' ? 'active' : ''} type="button" onClick={() => setNavigationMode('orbit')}>ORBIT MODE</button><button className={navigationMode === 'fly' ? 'active' : ''} type="button" onClick={() => { setNavigationMode('fly'); setMeasurementMode('none'); setPoints([]) }}>FLY MODE</button></div>
      <ViewerCanvas terrain={terrain} textureUrl={textureUrl} navigationMode={navigationMode} measurementMode={measurementMode} onPoint={addPoint} onViewerError={setViewerError} />
      <section className="analysis-panel" aria-label="Terrain analysis">
        <div className="analysis-toolbar"><strong>Measurement Mode: {measurementMode.toUpperCase()}</strong>{['none', 'height', 'slope'].map((mode) => <button key={mode} className={measurementMode === mode ? 'active' : ''} type="button" onClick={() => selectMeasurement(mode)}>{mode.toUpperCase()}</button>)}<button type="button" onClick={() => setPoints([])}>Clear Measurement</button></div>
        {measurementMode === 'none' ? <p>Select HEIGHT or SLOPE, then pick two displayed terrain samples.</p> : <dl className="analysis-results">
          <div><dt>Point A elevation</dt><dd>{points[0] ? `${format(points[0].elevation)} ${units.elevation}` : 'Select first point'}</dd></div>
          <div><dt>Point B elevation</dt><dd>{points[1] ? `${format(points[1].elevation)} ${units.elevation}` : 'Select second point'}</dd></div>
          {measurementMode === 'height' ? <div><dt>Height difference</dt><dd>{result ? `${format(result.heightDifference)} ${units.elevation}` : '—'}</dd></div> : <>
            <div><dt>Horizontal distance</dt><dd>{result ? `${format(result.horizontalDistance)} ${units.horizontal}` : '—'}</dd></div><div><dt>Vertical difference</dt><dd>{result ? `${format(result.verticalDifference)} ${units.elevation}` : '—'}</dd></div><div><dt>Slope ratio</dt><dd>{result?.slopeRatio == null ? '—' : format(result.slopeRatio)}</dd></div><div><dt>Slope %</dt><dd>{result?.slopePercent == null ? '—' : `${format(result.slopePercent)}%`}</dd></div><div><dt>Slope degrees</dt><dd>{result?.slopeDegrees == null ? '—' : `${format(result.slopeDegrees)}°`}</dd></div>
          </>}
        </dl>}
        {result?.reason && <p className="mission-warning">{result.reason}</p>}
        <p className="mission-note">Measurements snap to the displayed {terrain.width} × {terrain.height} viewer-sampled grid; no sub-pixel precision is claimed.</p>
      </section>
      <div className="mission-meta"><span>{terrain.width} × {terrain.height} grid</span><span>{terrain.height_units || 'units unavailable'}</span><span>{terrain.coordinate_mode || 'coordinate mode unavailable'}</span></div>
      <p className="mission-note">Vertical exaggeration is visual only; measurements use source elevation samples.</p>{viewerError && <p className="mission-warning" role="status">{viewerError}</p>}
      {validation.nodataCount > 0 && <p className="mission-warning">{validation.nodataCount} nodata sample(s) use nearest valid elevation only for continuous rendering and cannot be measured.</p>}
    </> : <div className="mission-fallback"><span aria-hidden="true">05</span><strong>MissionView unavailable</strong><p>{fallback}</p></div>}
    {!mock && ready && <p className="mission-warning">Metric terrain is calibration output. Accuracy claims require the separate Independent Validation stage.</p>}
  </article>
}

export default MissionViewAnalysis
