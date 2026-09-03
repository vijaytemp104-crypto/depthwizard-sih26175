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

function ViewerCanvas({
  terrain,
  textureUrl,
  navigationMode,
  measurementMode,
  onPoint,
  onViewerError,
  resetTriggerRef,
  enterFlyRef,
}) {
  const containerRef = useRef(null)

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
      scene.fog = new THREE.Fog(0x081522, 11, 24)

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
      orbit.maxDistance = 22
      orbit.maxPolarAngle = Math.PI * 0.48
      orbit.target.copy(TARGET_POSITION)
      orbit.enabled = navigationMode === 'orbit'

      const fly = new PointerLockControls(camera, renderer.domElement)
      if (enterFlyRef) {
        enterFlyRef.current = () => fly.lock()
      }

      const width = 6
      const depth = width * ((terrain.height - 1) / (terrain.width - 1))
      const geometry = new THREE.PlaneGeometry(width, depth, terrain.width - 1, terrain.height - 1)
      geometry.rotateX(-Math.PI / 2)

      const minimum = Math.min(...validation.values)
      const range = Math.max(...validation.values) - minimum || 1
      const positions = geometry.attributes.position
      validation.values.forEach((value, index) =>
        positions.setY(index, ((value - minimum) / range - 0.5) * VERTICAL_EXAGGERATION)
      )
      positions.needsUpdate = true
      geometry.computeVertexNormals()

      const material = new THREE.MeshStandardMaterial({
        color: 0x297373,
        roughness: 0.76,
        side: THREE.DoubleSide,
      })
      const mesh = new THREE.Mesh(geometry, material)
      scene.add(mesh)

      const wireGeometry = new THREE.WireframeGeometry(geometry)
      const wireMaterial = new THREE.LineBasicMaterial({
        color: 0x80dce5,
        transparent: true,
        opacity: 0.28,
      })
      mesh.add(new THREE.LineSegments(wireGeometry, wireMaterial))

      const markerGeometry = new THREE.SphereGeometry(0.075, 12, 8)
      const markerMaterials = [
        new THREE.MeshBasicMaterial({ color: 0x297373 }),
        new THREE.MeshBasicMaterial({ color: 0xff8552 }),
      ]
      const markers = []
      const raycaster = new THREE.Raycaster()
      const pointer = new THREE.Vector2()

      const pick = (event) => {
        if (measurementMode === 'none' || navigationMode === 'fly' || fly.isLocked) return
        const bounds = renderer.domElement.getBoundingClientRect()
        pointer.set(
          ((event.clientX - bounds.left) / bounds.width) * 2 - 1,
          -((event.clientY - bounds.top) / bounds.height) * 2 + 1
        )
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

        if (markers.length === 2) {
          markers.splice(0).forEach((marker) => scene.remove(marker))
        }

        const marker = new THREE.Mesh(markerGeometry, markerMaterials[markers.length])
        marker.position.set(positions.getX(index), positions.getY(index) + 0.08, positions.getZ(index))
        scene.add(marker)
        markers.push(marker)
        onPoint({ row, column, elevation: terrain.heights[row][column] })
      }

      renderer.domElement.addEventListener('click', pick)

      if (textureUrl) {
        new THREE.TextureLoader().load(
          textureUrl,
          (loaded) => {
            if (disposed) return loaded.dispose()
            terrainTexture = loaded
            loaded.colorSpace = THREE.SRGBColorSpace
            material.map = loaded
            material.color.set(0xffffff)
            material.needsUpdate = true
          },
          undefined,
          () => !disposed && onViewerError('Input texture unavailable; neutral terrain shading is shown.')
        )
      }

      scene.add(new THREE.HemisphereLight(0xbdebf2, 0x132332, 2.2))
      const light = new THREE.DirectionalLight(0xffffff, 2.5)
      light.position.set(4, 8, 3)
      scene.add(light)

      const grid = new THREE.GridHelper(9, 12, 0x2b6470, 0x183744)
      grid.position.y = -1.05
      scene.add(grid)

      if (resetTriggerRef) {
        resetTriggerRef.current = () => {
          fly.unlock()
          camera.position.copy(CAMERA_POSITION)
          orbit.target.copy(TARGET_POSITION)
          orbit.update()
        }
      }

      const keyDown = (event) => keys.add(event.code)
      const keyUp = (event) => keys.delete(event.code)
      window.addEventListener('keydown', keyDown)
      window.addEventListener('keyup', keyUp)

      const resize = () => {
        const w = Math.max(container.clientWidth, 1)
        const h = Math.max(container.clientHeight, 1)
        renderer.setSize(w, h, false)
        camera.aspect = w / h
        camera.updateProjectionMatrix()
      }

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
        } else {
          orbit.update()
        }

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
        fly.unlock()
        fly.disconnect()
        orbit.dispose()
        terrainTexture?.dispose()
        markerGeometry.dispose()
        markerMaterials.forEach((item) => item.dispose())
        wireGeometry.dispose()
        wireMaterial.dispose()
        geometry.dispose()
        material.dispose()
        renderer.dispose()
        renderer.domElement.remove()
        if (resetTriggerRef) resetTriggerRef.current = null
        if (enterFlyRef) enterFlyRef.current = null
      }
    } catch {
      renderer?.dispose()
      onViewerError('WebGL could not initialize for MissionView on this device.')
      return undefined
    }
  }, [terrain, textureUrl, navigationMode, measurementMode, onPoint, onViewerError, resetTriggerRef, enterFlyRef])

  return <div ref={containerRef} className="mission-canvas h-full w-full" aria-label="Interactive terrain viewer" />
}

const format = (value) => (Number.isFinite(value) ? value.toFixed(2) : '—')

export default function MissionViewAnalysis({
  terrain,
  textureUrl,
  mock = false,
  state = 'empty',
  errorMessage = '',
}) {
  const [viewerError, setViewerError] = useState('')
  const [navigationMode, setNavigationMode] = useState('orbit')
  const [measurementMode, setMeasurementMode] = useState('none')
  const [points, setPoints] = useState([])

  const resetTriggerRef = useRef(null)
  const enterFlyRef = useRef(null)

  const validation = validateTerrain(terrain)
  const ready = state === 'succeeded' && validation.valid

  const addPoint = useCallback((point) => {
    setPoints((current) => (current.length >= 2 ? [point] : [...current, point]))
  }, [])

  const selectMeasurement = (mode) => {
    setMeasurementMode(mode)
    setPoints([])
    if (mode !== 'none') setNavigationMode('orbit')
  }

  const measurementResult =
    points.length === 2
      ? measurementMode === 'height'
        ? heightMeasurement(points[0], points[1], terrain)
        : slopeMeasurement(points[0], points[1], terrain)
      : null

  const units = measurementUnits(terrain)

  let fallback = 'Run the pipeline to prepare terrain.'
  if (['pending', 'running', 'loading'].includes(state)) fallback = 'Terrain is waiting for the pipeline to finish.'
  if (['failed', 'error'].includes(state)) fallback = errorMessage || 'Terrain could not be prepared.'
  if (state === 'succeeded' && !validation.valid) fallback = validation.message

  return (
    <div className="h-full w-full relative overflow-hidden flex flex-col justify-between" id="missionview-container">
      {ready ? (
        <>
          {/* Main 3D Canvas */}
          <div className="absolute inset-0 z-0">
            <ViewerCanvas
              terrain={terrain}
              textureUrl={textureUrl}
              navigationMode={navigationMode}
              measurementMode={measurementMode}
              onPoint={addPoint}
              onViewerError={setViewerError}
              resetTriggerRef={resetTriggerRef}
              enterFlyRef={enterFlyRef}
            />
          </div>

          {/* TOP FLOATING HUD */}
          <div className="relative z-10 flex items-start justify-between gap-2 p-3 pointer-events-none">
            {/* Left: Scientific Mode Status & Disaster Tags */}
            <div className="flex flex-col gap-1.5 pointer-events-auto">
              <div className="flex items-center gap-2 bg-white/95 backdrop-blur border border-line px-3 py-1.5 rounded shadow-xs">
                <span className={`w-2.5 h-2.5 rounded-full ${mock ? 'bg-amber-500' : 'bg-pine'} animate-pulse`} />
                <span className={`font-mono text-[10.5px] font-bold ${mock ? 'text-amber-700' : 'text-pine'}`}>
                  {mock ? 'RELATIVE DEPTH · NOT METRIC' : 'CALIBRATED · METRIC DSM'}
                </span>
                <span className="text-graphite-muted text-[10px]">|</span>
                <span className="font-mono text-[10px] text-graphite font-medium">
                  {terrain.coordinate_mode || 'EGM2008 / UTM'}
                </span>
              </div>
              <div className="flex items-center gap-1 flex-wrap">
                <span className="px-2 py-0.5 bg-white/90 border border-line text-graphite font-mono text-[9px] font-semibold rounded">
                  LANDSLIDE TERRAIN ASSESSMENT
                </span>
                <span className="px-2 py-0.5 bg-white/90 border border-line text-graphite font-mono text-[9px] font-semibold rounded">
                  SLOPE STABILITY REVIEW
                </span>
                <span className="px-2 py-0.5 bg-straw-subtle border border-straw text-graphite font-mono text-[9px] font-bold rounded">
                  NON-PREDICTIVE ADVISORY
                </span>
              </div>
            </div>

            {/* Center: Camera Control Modes Bar */}
            <div className="flex items-center gap-1 bg-white/95 backdrop-blur border border-line p-1 rounded shadow-xs pointer-events-auto">
              <button
                type="button"
                className={`px-3 py-1 font-mono text-[10.5px] font-bold rounded shadow-xs transition-colors ${
                  navigationMode === 'orbit' ? 'bg-pine text-white' : 'text-graphite hover:bg-alabaster'
                }`}
                onClick={() => setNavigationMode('orbit')}
              >
                ORBIT
              </button>
              <button
                type="button"
                className={`px-3 py-1 font-mono text-[10.5px] font-bold rounded shadow-xs transition-colors ${
                  navigationMode === 'fly' ? 'bg-pine text-white' : 'text-graphite hover:bg-alabaster'
                }`}
                onClick={() => {
                  setNavigationMode('fly')
                  setMeasurementMode('none')
                  setPoints([])
                  enterFlyRef.current?.()
                }}
              >
                FLY
              </button>
              <div className="h-4 w-px bg-line mx-0.5" />
              <button
                type="button"
                className="px-2 py-1 text-graphite hover:bg-alabaster font-mono text-[10.5px] font-medium rounded transition-colors"
                onClick={() => resetTriggerRef.current?.()}
                title="Reset Camera Position"
              >
                RESET
              </button>
            </div>

            {/* Right: Tools & Active Measurement Readout Card */}
            <div className="flex flex-col items-end gap-1.5 pointer-events-auto">
              <div className="flex items-center gap-1 bg-white/95 backdrop-blur border border-line p-1 rounded shadow-xs">
                <button
                  type="button"
                  className={`flex items-center gap-1 px-2.5 py-1 font-mono text-[10.5px] font-medium rounded transition-colors ${
                    measurementMode === 'height' ? 'bg-coral text-white font-bold' : 'text-graphite hover:bg-alabaster'
                  }`}
                  onClick={() => selectMeasurement(measurementMode === 'height' ? 'none' : 'height')}
                >
                  <span>HEIGHT TOOL</span>
                </button>
                <button
                  type="button"
                  className={`flex items-center gap-1 px-2.5 py-1 font-mono text-[10.5px] font-bold rounded shadow-xs transition-colors ${
                    measurementMode === 'slope' ? 'bg-coral text-white' : 'text-graphite hover:bg-alabaster'
                  }`}
                  onClick={() => selectMeasurement(measurementMode === 'slope' ? 'none' : 'slope')}
                >
                  <span>SLOPE TOOL</span>
                </button>
                {points.length > 0 && (
                  <button
                    type="button"
                    className="px-2 py-1 text-graphite-muted hover:text-graphite font-mono text-[10px] rounded"
                    onClick={() => setPoints([])}
                    title="Clear selected points"
                  >
                    Clear
                  </button>
                )}
              </div>

              {/* Active Measurement Card */}
              {measurementMode !== 'none' && (
                <div className="w-64 bg-white/95 backdrop-blur border border-line p-2.5 rounded shadow-xs font-mono text-[11px]">
                  <div className="flex items-center justify-between pb-1 border-b border-line">
                    <span className="font-bold text-graphite flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-coral" />
                      Active Measurement ({measurementMode.toUpperCase()})
                    </span>
                    <span className="text-[9px] px-1 bg-pine-subtle text-pine font-bold rounded">
                      {units.elevation}
                    </span>
                  </div>
                  <div className="mt-1.5 space-y-1">
                    {measurementMode === 'height' ? (
                      <div className="flex justify-between items-center">
                        <span className="text-graphite-muted text-[10px]">Height Delta (Δh):</span>
                        <span className="text-pine font-bold text-xs">
                          {measurementResult ? `${format(measurementResult.heightDifference)} ${units.elevation}` : 'Pick 2 points'}
                        </span>
                      </div>
                    ) : (
                      <>
                        <div className="flex justify-between items-center">
                          <span className="text-graphite-muted text-[10px]">Height Delta (Δh):</span>
                          <span className="text-pine font-bold text-xs">
                            {measurementResult ? `${format(measurementResult.verticalDifference)} ${units.elevation}` : '—'}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-graphite-muted text-[10px]">Surface Slope:</span>
                          <span className="text-coral font-bold text-xs bg-coral-subtle px-1.5 py-0.5 rounded">
                            {measurementResult?.slopeDegrees != null
                              ? `${format(measurementResult.slopeDegrees)}° (${format(measurementResult.slopePercent)}%)`
                              : 'Pick 2 points'}
                          </span>
                        </div>
                      </>
                    )}
                    <div className="flex justify-between text-[9px] pt-1 border-t border-line text-graphite-muted">
                      <span>Pt A: {points[0] ? `${format(points[0].elevation)} ${units.elevation}` : '—'}</span>
                      <span>Pt B: {points[1] ? `${format(points[1].elevation)} ${units.elevation}` : '—'}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* BOTTOM FLOATING HUD */}
          <div className="relative z-10 flex items-end justify-between gap-2 p-3 pointer-events-none">
            {/* Elevation Colorbar Legend */}
            <div className="bg-white/95 backdrop-blur border border-line p-2 rounded shadow-xs w-72 pointer-events-auto">
              <div className="flex justify-between font-mono text-[9px] text-graphite-muted font-semibold mb-1">
                <span>ELEVATION: Low</span>
                <span>High</span>
              </div>
              <div className="h-2 w-full rounded bg-gradient-to-r from-pine via-[#8cd3d2] to-white border border-line" />
              <div className="flex justify-between font-mono text-[8px] text-graphite-muted mt-0.5">
                <span>Valley floor</span>
                <span>Mid-slope</span>
                <span>Peak</span>
              </div>
            </div>

            {/* Center Navigation Hint */}
            <div className="bg-white/90 backdrop-blur border border-line px-3 py-1 rounded text-graphite font-mono text-[10px] flex items-center gap-1.5 pointer-events-auto shadow-xs">
              <span className="text-pine font-bold">⌘</span>
              <span>
                {navigationMode === 'fly'
                  ? 'Click canvas for fly view • WASD move • mouse look • Shift fast • Esc exit'
                  : measurementMode === 'none'
                  ? 'Left-drag to rotate • Right-drag to pan • Scroll to zoom'
                  : 'Click two points on the 3D surface to measure slope / height'}
              </span>
            </div>

            {/* Terrain Dimensions Pill */}
            <div className="bg-white/95 backdrop-blur border border-line px-3 py-1 rounded shadow-xs font-mono text-[10px] pointer-events-auto">
              <span className="text-graphite-muted">GRID: </span>
              <span className="text-graphite font-bold">{terrain.width} × {terrain.height}</span>
              <span className="text-graphite-muted mx-1">|</span>
              <span className="text-pine font-bold">{terrain.height_units || 'units'}</span>
            </div>
          </div>

          {viewerError && (
            <div className="absolute top-16 left-1/2 -translate-x-1/2 z-30 bg-red-600 text-white px-3 py-1 rounded font-mono text-xs shadow-md">
              {viewerError}
            </div>
          )}
        </>
      ) : (
        <div className="h-full w-full flex items-center justify-center p-8 text-center bg-alabaster/40">
          <div className="max-w-md p-6 bg-white border border-line rounded shadow-sm">
            <span className="text-4xl block mb-2 text-pine font-mono font-bold">05</span>
            <h3 className="font-sans text-base font-bold text-graphite">3D MissionView Awaiting Execution</h3>
            <p className="font-body text-xs text-graphite-muted mt-1">{fallback}</p>
          </div>
        </div>
      )}
    </div>
  )
}
