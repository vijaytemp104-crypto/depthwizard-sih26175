import test from 'node:test'
import assert from 'node:assert/strict'
import { loadMissionTerrain, relativeTerrainFromNpy } from './relativeTerrain.js'

function npy(height, width, values, { version = 1, dtype = '<f4', fortran = false } = {}) {
  const prefix = version === 1 ? 10 : 12
  const dictionary = `{'descr': '${dtype}', 'fortran_order': ${fortran ? 'True' : 'False'}, 'shape': (${height}, ${width}), }`
  const padding = 64 - ((prefix + dictionary.length + 1) % 64)
  const header = new TextEncoder().encode(dictionary + ' '.repeat(padding) + '\n')
  const buffer = new ArrayBuffer(prefix + header.length + values.length * 4)
  const bytes = new Uint8Array(buffer)
  bytes.set([147, 78, 85, 77, 80, 89, version, 0])
  const view = new DataView(buffer)
  if (version === 1) view.setUint16(8, header.length, true)
  else view.setUint32(8, header.length, true)
  bytes.set(header, prefix)
  values.forEach((value, i) => view.setFloat32(prefix + header.length + i * 4, value, dtype !== '>f4'))
  return buffer
}

const relativeResult = {
  calibration: { calibrated: false },
  depth: { status: 'succeeded', mock: false, units: 'relative', height: 3, width: 4, artifacts: { array: 'outputs/job/depth.npy' } },
  terrain: { mode: 'synthetic_placeholder', width: 2, height: 2, heights: [[0, 0.25], [0.75, 1]] },
}
const values = [9, 2, 4, 6, 3, 10, 7, 11, 12, 5, 1, 8]

test('successful no-DEM data comes from depth.npy, not the synthetic result grid', async () => {
  const before = structuredClone(relativeResult)
  const buffer = npy(3, 4, values)
  const bytes = new Uint8Array(buffer).slice()
  const terrain = await loadMissionTerrain(relativeResult, async (name) => {
    assert.equal(name, 'depth.npy')
    return buffer
  })
  assert.deepEqual(terrain.heights.flat(), values)
  assert.equal(terrain.mode, 'relative_depth')
  assert.equal(terrain.height_units, 'relative')
  assert.equal(terrain.coordinate_mode, 'relative')
  assert.deepEqual(relativeResult, before)
  assert.deepEqual(new Uint8Array(buffer), bytes)
})

test('calibrated path returns the identical DSM object without any artifact read', async () => {
  const terrain = Object.freeze({ coordinate_mode: 'geospatial', height_units: 'metres', heights: [[1600, 1601], [1602, 1603]] })
  const result = { calibration: { calibrated: true }, terrain }
  assert.equal(await loadMissionTerrain(result, () => assert.fail('Metric path must not fetch depth')), terrain)
})

test('regular stride samples actual values and preserves corners, orientation and aspect', () => {
  const height = 257
  const width = 401
  const source = Array.from({ length: height * width }, (_, i) => i)
  const grid = relativeTerrainFromNpy(npy(height, width, source), { height, width })
  const step = 4
  assert.equal(grid.viewer_decimation.step, step)
  assert.ok(grid.width <= 129 && grid.height <= 129)
  assert.equal(grid.relative_display_grid.aspect, 256 / 400)
  grid.heights.forEach((row, r) => row.forEach((value, c) => {
    const originalRow = Math.round(grid.relative_display_grid.rows[r] * (height - 1))
    const originalColumn = Math.round(grid.relative_display_grid.columns[c] * (width - 1))
    assert.equal(value, source[originalRow * width + originalColumn])
  }))
  assert.equal(grid.heights[0][0], source[0])
  assert.equal(grid.heights.at(-1).at(-1), source.at(-1))
  assert.equal(grid.relative_display_grid.rows.at(-1), 1)
  assert.equal(grid.relative_display_grid.columns.at(-1), 1)
})

test('stride retains a non-aligned last pixel and thin images still have two edges', () => {
  for (const [height, width] of [[260, 402], [2, 600]]) {
    const source = Array.from({ length: height * width }, (_, i) => i)
    const grid = relativeTerrainFromNpy(npy(height, width, source), { height, width })
    assert.ok(grid.width >= 2 && grid.height >= 2)
    assert.equal(grid.heights.at(-1).at(-1), source.at(-1))
    assert.equal(grid.relative_display_grid.aspect, (height - 1) / (width - 1))
  }
})

test('float32 byte order and NPY header versions preserve numeric values', () => {
  for (const version of [1, 2, 3]) {
    for (const dtype of ['<f4', '>f4']) {
      const grid = relativeTerrainFromNpy(npy(3, 4, values, { version, dtype }), { height: 3, width: 4 })
      assert.deepEqual(grid.heights.flat(), values)
    }
  }
})

test('constant depth remains constant, without invented relief', () => {
  const grid = relativeTerrainFromNpy(npy(3, 4, values.map(() => 7)), { height: 3, width: 4 })
  assert.deepEqual(grid.heights.flat(), values.map(() => 7))
})

test('missing or failed real depth never falls back to synthetic success', async () => {
  for (const depth of [undefined, { ...relativeResult.depth, artifacts: {} }, { ...relativeResult.depth, mock: true }, { ...relativeResult.depth, status: 'failed' }]) {
    await assert.rejects(loadMissionTerrain({ ...relativeResult, depth }, () => assert.fail('Do not fetch invalid result')), /unavailable/)
  }
  await assert.rejects(loadMissionTerrain(relativeResult, async () => { throw new Error('404 missing artifact') }), /404/)
})

test('corrupt, mismatched, non-finite, object and Fortran artifacts fail closed', () => {
  const expected = { height: 3, width: 4 }
  const valid = npy(3, 4, values)
  for (const buffer of [new ArrayBuffer(0), valid.slice(0, -1), npy(2, 6, values),
    npy(3, 4, [NaN, ...values.slice(1)]), npy(3, 4, [Infinity, ...values.slice(1)]),
    npy(3, 4, values, { dtype: '|O' }), npy(3, 4, values, { fortran: true })]) {
    assert.throws(() => relativeTerrainFromNpy(buffer, expected), /invalid or unsupported/)
  }
})

test('MissionView UI keeps relative tools disabled and metric tools/units unchanged', async () => {
  const { createServer } = await import('vite')
  const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  try {
    const { default: React } = await import('react')
    const { renderToStaticMarkup } = await import('react-dom/server')
    const { default: MissionView } = await server.ssrLoadModule('/src/components/MissionViewAnalysis.jsx')
    const { default: SpatialDrawer } = await server.ssrLoadModule('/src/components/SpatialDrawer.jsx')
    const relative = relativeTerrainFromNpy(npy(3, 4, values), relativeResult.depth)
    const metric = { width: 2, height: 2, heights: [[1600, 1601], [1602, 1603]], coordinate_mode: 'geospatial', height_units: 'metres', transform: [2, 0, 0, 0, -2, 0] }
    for (const [terrain, mock] of [[relative, true], [metric, false]]) {
      const html = renderToStaticMarkup(React.createElement(MissionView, { terrain, mock, state: 'succeeded' }))
      const buttons = html.match(/<button\b[^>]*>[\s\S]*?<\/button>/g)
      for (const label of ['HEIGHT TOOL', 'SLOPE TOOL']) {
        assert.equal(/disabled/.test(buttons.find((button) => button.includes(label))), mock)
      }
      assert.ok(html.includes(mock ? 'RELATIVE DEPTH · NOT METRIC' : 'CALIBRATED · METRIC DSM'))
      assert.equal(html.includes('Metric slope requires elevation calibration'), mock)
      assert.equal(html.includes('metres'), !mock)
      assert.equal(html.includes('Relative Relief'), false)
      const drawer = renderToStaticMarkup(React.createElement(SpatialDrawer, { result: { calibration: { calibrated: !mock }, terrain } }))
      if (mock) {
        assert.ok(drawer.includes('Relative Depth Bounds'))
        assert.ok(!drawer.includes('metres') && !drawer.includes('EGM2008') && !drawer.includes('EPSG:32619'))
      }
    }
    const error = renderToStaticMarkup(React.createElement(MissionView, { mock: true, state: 'error', errorMessage: 'Relative depth unavailable' }))
    assert.ok(error.includes('Relative depth unavailable'))
    assert.ok(!error.includes('Interactive terrain viewer'))
  } finally {
    await server.close()
  }
})
