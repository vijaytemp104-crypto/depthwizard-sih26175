import test from 'node:test'
import assert from 'node:assert/strict'
import { heightMeasurement, measurementUnits, prepareTerrainGrid, slopeMeasurement } from './analysis.js'

const metricTerrain = { coordinate_mode: 'geospatial', height_units: 'metres', transform: [2, 0, 500000, 0, -2, 2200000] }
const pointA = { elevation: 10, row: 0, column: 0 }
const pointB = { elevation: 16, row: 0, column: 2 }

test('height difference preserves metric units', () => {
  const result = heightMeasurement(pointA, pointB, metricTerrain)
  assert.equal(result.heightDifference, 6)
  assert.equal(result.units.elevation, 'm')
})

test('slope percent and degrees use metric rise and run', () => {
  const result = slopeMeasurement(pointA, pointB, metricTerrain)
  assert.equal(result.horizontalDistance, 4)
  assert.equal(result.slopePercent, 150)
  assert.ok(Math.abs(result.slopeDegrees - 56.309932474) < 1e-9)
})

test('zero horizontal run is handled without infinity', () => {
  const result = slopeMeasurement(pointA, { ...pointA, elevation: 12 }, metricTerrain)
  assert.equal(result.slopeRatio, null)
  assert.equal(result.slopePercent, null)
  assert.equal(result.slopeDegrees, null)
  assert.match(result.reason, /zero/)
})

test('relative terrain never claims metres', () => {
  const units = measurementUnits({ coordinate_mode: 'relative', height_units: 'relative' })
  assert.equal(units.metric, false)
  assert.equal(units.elevation, 'RELATIVE UNITS')
  assert.equal(units.horizontal, 'VIEWER GRID UNITS')
})

test('a single nodata sample does not invalidate the terrain grid', () => {
  const prepared = prepareTerrainGrid({ width: 2, height: 2, heights: [[10, null], [12, 14]] })
  assert.equal(prepared.valid, true)
  assert.equal(prepared.nodataCount, 1)
  assert.deepEqual(prepared.validMask, [true, false, true, true])
  assert.equal(Number.isFinite(prepared.values[1]), true)
})

test('an entirely nodata terrain remains invalid', () => {
  const prepared = prepareTerrainGrid({ width: 2, height: 2, heights: [[null, null], [null, null]] })
  assert.equal(prepared.valid, false)
  assert.match(prepared.message, /no valid elevation/)
})
