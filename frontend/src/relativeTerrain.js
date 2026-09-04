// Decode only the numeric, row-major float32 NPY contract written by our adapter.
// No source buffer/result mutation, normalization, inversion, or metric conversion.
export function relativeTerrainFromNpy(buffer, expected) {
  const fail = () => { throw new Error('Relative depth artifact is invalid or unsupported.') }
  if (!(buffer instanceof ArrayBuffer) || buffer.byteLength < 12) fail()
  const view = new DataView(buffer)
  if ([147, 78, 85, 77, 80, 89].some((byte, i) => view.getUint8(i) !== byte)) fail()
  const version = view.getUint8(6)
  if (![1, 2, 3].includes(version) || view.getUint8(7) !== 0) fail()
  const prefix = version === 1 ? 10 : 12
  const headerLength = version === 1 ? view.getUint16(8, true) : view.getUint32(8, true)
  const offset = prefix + headerLength
  if (headerLength > 65536 || offset > buffer.byteLength) fail()
  const header = new TextDecoder().decode(new Uint8Array(buffer, prefix, headerLength))
  const dtype = /['"]descr['"]\s*:\s*['"]([<>]f4)['"]/.exec(header)?.[1]
  const shape = /['"]shape['"]\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*,?\s*\)/.exec(header)
  if (!dtype || !shape || !/['"]fortran_order['"]\s*:\s*False\b/.test(header)) fail()
  const height = Number(shape[1])
  const width = Number(shape[2])
  const count = height * width
  if (height < 2 || width < 2 || !Number.isSafeInteger(count)
    || offset + count * 4 !== buffer.byteLength
    || height !== expected?.height || width !== expected?.width) fail()
  const littleEndian = dtype === '<f4'
  for (let i = 0; i < count; i += 1) {
    if (!Number.isFinite(view.getFloat32(offset + i * 4, littleEndian))) fail()
  }
  // Match the metric viewer's regular stride, retaining the final row/column
  // as well so the complete RGB image and depth cover identical extents.
  const step = Math.max(1, Math.ceil(height / 128), Math.ceil(width / 128))
  const indices = (length) => {
    const values = []
    for (let i = 0; i < length; i += step) values.push(i)
    if (values.at(-1) !== length - 1) values.push(length - 1)
    return values
  }
  const rows = indices(height)
  const columns = indices(width)
  return {
    mock: false, mode: 'relative_depth', status: 'succeeded',
    coordinate_mode: 'relative', height_units: 'relative',
    width: columns.length, height: rows.length,
    heights: rows.map((row) => columns.map((column) =>
      view.getFloat32(offset + (row * width + column) * 4, littleEndian))),
    full_raster_width: width, full_raster_height: height,
    viewer_decimation: { method: 'regular stride with boundary samples', step },
    // Display-only positions preserve aspect ratio and UVs at boundary samples.
    relative_display_grid: {
      aspect: (height - 1) / (width - 1),
      rows: rows.map((row) => row / (height - 1)),
      columns: columns.map((column) => column / (width - 1)),
    },
  }
}

export async function loadMissionTerrain(result, readArtifact) {
  // Do not load, decode, or otherwise touch calibrated terrain.
  if (result?.calibration?.calibrated === true) return result.terrain
  const depth = result?.depth
  if (depth?.status !== 'succeeded' || depth.mock !== false || depth.units !== 'relative'
    || !/(^|\/)depth\.npy$/.test(depth.artifacts?.array || '')) {
    throw new Error('Real relative depth is unavailable; no synthetic terrain is displayed.')
  }
  return relativeTerrainFromNpy(await readArtifact('depth.npy'), depth)
}
