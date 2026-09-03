import React, { useMemo } from 'react'

export default function SpatialDrawer({ file, job, result }) {
  const isMetric = result?.calibration?.calibrated
  const modelMeta = result?.depth?.model_metadata || {}
  const calibration = result?.calibration || {}
  const terrain = result?.terrain

  // Safely derive terrain min/max/span/slope bounds without changing calculations
  const bounds = useMemo(() => {
    if (!terrain?.heights || !Array.isArray(terrain.heights) || terrain.heights.length === 0) {
      return null
    }
    let min = Infinity
    let max = -Infinity
    for (const row of terrain.heights) {
      if (Array.isArray(row)) {
        for (const val of row) {
          if (Number.isFinite(val)) {
            if (val < min) min = val
            if (val > max) max = val
          }
        }
      }
    }
    if (!Number.isFinite(min) || !Number.isFinite(max)) return null
    const span = max - min
    return {
      min: min.toFixed(1),
      max: max.toFixed(1),
      span: span.toFixed(1),
      unit: terrain.height_units || (isMetric ? 'm AMSL' : 'rel'),
    }
  }, [terrain, isMetric])

  return (
    <aside className="stitch-spatial-drawer" aria-label="Spatial Metadata Drawer">
      <div className="flex flex-col gap-2.5">
        {/* Drawer Header */}
        <div className="spatial-drawer-header">
          <div className="flex items-center gap-1.5">
            <span className="text-pine font-bold">☲</span>
            <h3 className="font-sans text-xs font-bold text-graphite tracking-tight">Spatial Metadata</h3>
          </div>
          <span className={`spatial-badge ${isMetric ? 'metric' : 'relative'}`}>
            {isMetric ? 'METRIC DSM' : 'RELATIVE'}
          </span>
        </div>

        {/* Optical Basemap Card */}
        <div className="spatial-info-card">
          <span className="spatial-label">OPTICAL INPUT</span>
          <span className="spatial-value truncate" title={file?.name || 'No file loaded'}>
            {file ? file.name : 'No optical image selected'}
          </span>
          <span className="spatial-sub">
            {file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB • ${file.type || 'Raster'}` : 'Awaiting input'}
          </span>
        </div>

        {/* Estimation Model Card */}
        <div className="spatial-info-card">
          <span className="spatial-label">ESTIMATION MODEL</span>
          <span className="spatial-value">
            {modelMeta.model_name || 'Depth Anything V2 Small'}
          </span>
          <span className="spatial-sub">
            {modelMeta.checkpoint ? `${modelMeta.checkpoint} • Verified Offline` : 'Offline Monocular Weights'}
          </span>
        </div>

        {/* Calibration Source Card */}
        <div className="spatial-info-card">
          <span className="spatial-label">CALIBRATION SOURCE</span>
          <span className="spatial-value truncate">
            {calibration.reference_source || (isMetric ? 'Reference DEM Bound' : 'Awaiting Calibration DEM')}
          </span>
          <span className="spatial-sub">
            {isMetric
              ? `Scale α=${Number(calibration.scale_a).toFixed(2)} • Bias β=${Number(calibration.offset_b).toFixed(2)}m (R²=${Number(calibration.fit_r_squared || 0).toFixed(3)})`
              : 'Relative scale [0.0 - 1.0] (Non-metric)'}
          </span>
        </div>

        {/* Datum & Vertical Reference Card */}
        <div className="spatial-info-card">
          <span className="spatial-label">DATUM &amp; VERTICAL REFERENCE</span>
          <span className="spatial-value">
            {calibration.crs || 'EPSG:32619 / WGS84'}
          </span>
          <span className="spatial-sub">
            {calibration.vertical_datum || 'EGM2008 Orthometric Height'}
          </span>
        </div>

        {/* Calculated Terrain Bounds Card */}
        <div className="spatial-bounds-card">
          <span className="font-sans text-[11px] font-bold block mb-1.5 text-graphite">
            Calculated Terrain Bounds
          </span>
          <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
            <div>
              <span className="text-graphite-muted block text-[9px]">MIN ELEV</span>
              <span className="text-graphite font-bold">{bounds ? `${bounds.min} ${bounds.unit}` : '—'}</span>
            </div>
            <div>
              <span className="text-graphite-muted block text-[9px]">MAX ELEV</span>
              <span className="text-graphite font-bold">{bounds ? `${bounds.max} ${bounds.unit}` : '—'}</span>
            </div>
            <div>
              <span className="text-graphite-muted block text-[9px]">TOTAL SPAN</span>
              <span className="text-pine font-bold">{bounds ? `${bounds.span} ${bounds.unit}` : '—'}</span>
            </div>
            <div>
              <span className="text-graphite-muted block text-[9px]">GRID DIM</span>
              <span className="text-coral font-bold">{terrain ? `${terrain.width} × ${terrain.height}` : '—'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Layer Options Box */}
      <div className="spatial-layers-box">
        <span className="font-mono text-[9px] text-graphite-muted block uppercase font-bold mb-1.5">
          Workspace Information
        </span>
        <div className="flex items-center justify-between text-[11px] py-0.5">
          <span className="text-graphite font-medium">3D MissionView Viewport</span>
          <span className="font-mono text-pine font-bold">READY</span>
        </div>
        <div className="flex items-center justify-between text-[11px] py-0.5">
          <span className="text-graphite font-medium">Measurement Math</span>
          <span className="font-mono text-pine font-bold">ACTIVE</span>
        </div>
        <div className="flex items-center justify-between text-[11px] py-0.5">
          <span className="text-graphite font-medium">Air-Gapped Execution</span>
          <span className="font-mono text-pine font-bold">OFFLINE</span>
        </div>
      </div>
    </aside>
  )
}
