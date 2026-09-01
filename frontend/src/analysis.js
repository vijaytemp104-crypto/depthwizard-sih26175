export function measurementUnits(terrain) {
  const metric = terrain?.coordinate_mode === 'geospatial'
    && terrain?.height_units === 'metres'
    && Array.isArray(terrain?.transform)
    && terrain.transform.length >= 6
  return metric
    ? { metric: true, elevation: 'm', horizontal: 'm' }
    : { metric: false, elevation: 'RELATIVE UNITS', horizontal: 'VIEWER GRID UNITS' }
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
