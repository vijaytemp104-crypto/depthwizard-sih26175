export function measurementUnits(terrain) {
  const metric = terrain?.coordinate_mode === 'geospatial'
    && terrain?.height_units === 'metres'
    && Array.isArray(terrain?.transform)
    && terrain.transform.length >= 6
  return metric
    ? { metric: true, elevation: 'm', horizontal: 'm' }
    : { metric: false, elevation: 'RELATIVE UNITS', horizontal: 'VIEWER GRID UNITS' }
}

export function prepareTerrainGrid(terrain) {
  if (!terrain) return { valid: false, message: 'Terrain data has not arrived yet.' }
  const { width, height, heights } = terrain
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 2 || height < 2) return { valid: false, message: 'Terrain grid dimensions must be at least 2 × 2.' }
  if (!Array.isArray(heights) || heights.length !== height) return { valid: false, message: 'Terrain rows do not match the declared height.' }
  const values = []
  const validMask = []
  for (const row of heights) {
    if (!Array.isArray(row) || row.length !== width) return { valid: false, message: 'Terrain columns do not match the declared width.' }
    for (const value of row) {
      if (value !== null && !Number.isFinite(value)) return { valid: false, message: 'Terrain contains an invalid height value.' }
      values.push(value)
      validMask.push(value !== null)
    }
  }
  const validIndices = validMask.flatMap((valid, index) => valid ? [index] : [])
  if (validIndices.length === 0) return { valid: false, message: 'Terrain contains no valid elevation samples.' }
  validMask.forEach((valid, index) => {
    if (valid) return
    const row = Math.floor(index / width)
    const column = index % width
    let nearest = validIndices[0]
    let nearestDistance = Infinity
    for (const candidate of validIndices) {
      const candidateRow = Math.floor(candidate / width)
      const candidateColumn = candidate % width
      const distance = (candidateRow - row) ** 2 + (candidateColumn - column) ** 2
      if (distance < nearestDistance) { nearest = candidate; nearestDistance = distance }
    }
    values[index] = values[nearest]
  })
  return { valid: true, values, validMask, nodataCount: values.length - validIndices.length }
}

export function heightMeasurement(pointA, pointB, terrain) {
  if (!pointA || !pointB) return null
  const units = measurementUnits(terrain)
  return {
    pointAElevation: pointA.elevation,
    pointBElevation: pointB.elevation,
    heightDifference: pointB.elevation - pointA.elevation,
    units,
  }
}

export function horizontalDistance(pointA, pointB, terrain) {
  const units = measurementUnits(terrain)
  if (units.metric) {
    const [a, b, , d, e] = terrain.transform
    const deltaColumn = pointB.column - pointA.column
    const deltaRow = pointB.row - pointA.row
    return Math.hypot(a * deltaColumn + b * deltaRow, d * deltaColumn + e * deltaRow)
  }
  return Math.hypot(pointB.column - pointA.column, pointB.row - pointA.row)
}

export function slopeMeasurement(pointA, pointB, terrain) {
  if (!pointA || !pointB) return null
  const run = horizontalDistance(pointA, pointB, terrain)
  const rise = pointB.elevation - pointA.elevation
  const ratio = run === 0 ? null : rise / run
  return {
    pointAElevation: pointA.elevation,
    pointBElevation: pointB.elevation,
    horizontalDistance: run,
    verticalDifference: rise,
    slopeRatio: ratio,
    slopePercent: ratio == null ? null : ratio * 100,
    slopeDegrees: ratio == null ? null : Math.atan(ratio) * 180 / Math.PI,
    units: measurementUnits(terrain),
    reason: run === 0 ? 'Slope is undefined because horizontal distance is zero.' : null,
  }
}
