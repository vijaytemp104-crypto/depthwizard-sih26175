import React, { useRef, useState } from 'react'

const ACCEPTED = '.png,.jpg,.jpeg,.tif,.tiff,image/png,image/jpeg,image/tiff'

export default function UploadPanel({
  file,
  referenceFile,
  validationReferenceFile,
  onFileSelected,
  onReferenceSelected,
  onValidationReferenceSelected,
  onRun,
  busy,
}) {
  const inputRef = useRef(null)
  const referenceRef = useRef(null)
  const validationReferenceRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const chooseFirst = (files) => {
    const chosen = files?.[0]
    if (chosen) onFileSelected(chosen)
  }

  const isGeoTIFF = file?.name?.toLowerCase().endsWith('.tif') || file?.name?.toLowerCase().endsWith('.tiff')

  return (
    <div className="stitch-workspace-container" aria-labelledby="setup-heading">
      {/* Header */}
      <div className="workspace-header-bar">
        <div>
          <h1 id="setup-heading" className="workspace-title">Mission Setup &amp; Sensor Calibration</h1>
          <p className="workspace-subtitle">
            Ingest optical earth observation imagery and bind calibration references for metric 3D DSM reconstruction.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="primary-coral-btn"
            disabled={!file || busy}
            onClick={onRun}
          >
            <span>{busy ? 'ANALYZING TERRAIN…' : 'ANALYZE TERRAIN →'}</span>
          </button>
        </div>
      </div>

      {/* Grid: Optical Input & References */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Optical Input Zone */}
        <div className="stitch-panel flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <span className="text-pine font-bold text-[18px]">◎</span>
                <h3 className="font-sans text-sm font-bold text-graphite">1. Optical Imagery Input</h3>
              </div>
              <span className={`status-chip ${file ? 'metric' : 'relative'}`}>
                {file ? 'LOADED' : 'AWAITING FILE'}
              </span>
            </div>
            <p className="font-body text-[12px] text-graphite-muted mb-3">
              Accepts orthorectified GeoTIFF, PNG, or JPG from Copernicus Sentinel-2, Landsat-8/9, or UAV photogrammetry.
            </p>

            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED}
              className="hidden"
              onChange={(e) => {
                chooseFirst(e.target.files)
                e.target.value = ''
              }}
              aria-label="Select an overhead image"
            />
            {file ? (
              <div className="p-3 border border-pine bg-pine-subtle/30 rounded">
                <div className="flex items-start justify-between">
                  <div className="flex gap-2.5 min-w-0">
                    <div className="w-9 h-9 bg-pine flex items-center justify-center rounded text-white font-mono text-xs font-bold flex-shrink-0">
                      {isGeoTIFF ? 'TIF' : 'RGB'}
                    </div>
                    <div className="min-w-0">
                      <div className="font-mono text-[11px] font-bold text-graphite truncate">{file.name}</div>
                      <div className="font-mono text-[10px] text-graphite-muted mt-0.5">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB • {file.type || (isGeoTIFF ? 'image/tiff' : 'image/png')}
                      </div>
                    </div>
                  </div>
                  <span className="text-pine font-bold text-base">✓</span>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-2.5 pt-2 border-t border-line font-mono text-[10px]">
                  <div>
                    <span className="text-graphite-muted block text-[9px]">FORMAT:</span>
                    {isGeoTIFF ? 'Georeferenced Grid' : 'Standard 8-bit RGB'}
                  </div>
                  <div>
                    <span className="text-graphite-muted block text-[9px]">PIPELINE MODE:</span>
                    {referenceFile ? 'Calibrated Metric DSM' : isGeoTIFF ? 'Georeferenced Relative' : 'Relative Disparity'}
                  </div>
                </div>
              </div>
            ) : (
              <div
                className={`stitch-dropzone ${dragging ? 'dragging' : ''}`}
                onDragEnter={(e) => { e.preventDefault(); setDragging(true) }}
                onDragOver={(e) => e.preventDefault()}
                onDragLeave={(e) => { e.preventDefault(); setDragging(false) }}
                onDrop={(e) => { e.preventDefault(); setDragging(false); chooseFirst(e.dataTransfer.files) }}
              >
                <span className="text-pine text-2xl font-bold block mb-1">↑</span>
                <h4 className="font-sans text-xs font-bold text-graphite">Drop overhead satellite image here</h4>
                <p className="font-body text-[11px] text-graphite-muted mt-0.5">or browse your local filesystem</p>
                <button
                  type="button"
                  className="mt-2.5 px-3 py-1 bg-white border border-line-strong hover:border-pine text-graphite font-mono text-[11px] font-bold rounded shadow-xs transition-colors"
                  onClick={() => inputRef.current?.click()}
                >
                  Browse Imagery ↗
                </button>
              </div>
            )}
          </div>

          <div className="mt-3 flex items-center justify-between text-graphite-muted font-mono text-[10px]">
            <span>Format: PNG / JPG / GeoTIFF</span>
            {file && (
              <button
                type="button"
                className="text-pine hover:underline font-semibold"
                onClick={() => inputRef.current?.click()}
              >
                Replace Image
              </button>
            )}
          </div>
        </div>

        {/* Calibration & Validation References */}
        <div className="stitch-panel flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <span className="text-pine font-bold text-[18px]">☵</span>
                <h3 className="font-sans text-sm font-bold text-graphite">2. Reference Elevation Datasets</h3>
              </div>
              <span className={`status-chip ${referenceFile ? 'metric' : 'relative'}`}>
                {referenceFile ? 'CALIBRATION BOUND' : 'OPTIONAL REFERENCE'}
              </span>
            </div>
            <p className="font-body text-[12px] text-graphite-muted mb-3">
              Optional reference surfaces convert monocular relative disparity into metric elevation in metres via least-squares scale (α) and offset (β).
            </p>

            <div className="space-y-2.5">
              {/* Calibration Reference Row */}
              <div className="p-2.5 border border-line bg-alabaster/30 rounded flex items-center justify-between">
                <div className="min-w-0 pr-2">
                  <span className="font-sans text-[11px] font-bold text-graphite block">
                    Calibration Reference (DEM)
                  </span>
                  <span className="font-mono text-[10px] text-graphite-muted block truncate">
                    {referenceFile ? referenceFile.name : 'Optional · used to fit the metric DSM'}
                  </span>
                </div>
                <input
                  ref={referenceRef}
                  type="file"
                  accept=".tif,.tiff,image/tiff"
                  className="hidden"
                  onChange={(e) => onReferenceSelected(e.target.files?.[0] || null)}
                  aria-label="Select a calibration reference DEM"
                />
                <button
                  type="button"
                  className="px-2.5 py-1 bg-white border border-line-strong hover:border-pine text-graphite font-mono text-[10px] font-bold rounded shadow-xs flex-shrink-0"
                  onClick={() => referenceRef.current?.click()}
                >
                  {referenceFile ? 'Change DEM' : 'Select DEM'}
                </button>
              </div>

              {/* Validation Reference Row */}
              <div className="p-2.5 border border-line bg-alabaster/30 rounded flex items-center justify-between">
                <div className="min-w-0 pr-2">
                  <span className="font-sans text-[11px] font-bold text-graphite block">
                    Independent Validation Reference
                  </span>
                  <span className="font-mono text-[10px] text-graphite-muted block truncate">
                    {validationReferenceFile ? validationReferenceFile.name : 'Optional · separate withheld elevation GeoTIFF'}
                  </span>
                </div>
                <input
                  ref={validationReferenceRef}
                  type="file"
                  accept=".tif,.tiff,image/tiff"
                  className="hidden"
                  onChange={(e) => onValidationReferenceSelected(e.target.files?.[0] || null)}
                  aria-label="Select an independent validation reference"
                />
                <button
                  type="button"
                  className="px-2.5 py-1 bg-white border border-line-strong hover:border-pine text-graphite font-mono text-[10px] font-bold rounded shadow-xs flex-shrink-0"
                  onClick={() => validationReferenceRef.current?.click()}
                >
                  {validationReferenceFile ? 'Change Ref' : 'Select Ref'}
                </button>
              </div>
            </div>
          </div>

          <div className="mt-3 flex items-center justify-between text-graphite-muted font-mono text-[10px]">
            <span>Affine least-squares: α · d + β</span>
            <span className="text-pine font-bold">
              {referenceFile ? 'Metric Fit Enabled' : 'Relative Disparity Mode'}
            </span>
          </div>
        </div>
      </div>

      {/* Scientific Mode Determination Banner */}
      <div className="stitch-panel">
        <h3 className="font-sans text-sm font-bold mb-3 text-graphite">Scientific Operational Mode Determination</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {/* Calibrated Metric */}
          <div className="p-3 bg-white border-2 border-pine rounded flex flex-col justify-between shadow-xs">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-sans text-xs font-bold text-pine">GeoTIFF + DEM Calibration</span>
                <span className="status-chip metric text-[9px] py-0.5">CALIBRATED · METRIC DSM</span>
              </div>
              <p className="font-body text-[11px] text-graphite/80">
                Provides true metric elevation in metres, physically accurate slope gradient calculations, precise vertical cross-sections, and reliable georeferenced disaster assessment.
              </p>
            </div>
            <ul className="mt-2.5 pt-2 border-t border-line space-y-1 font-mono text-[10px] text-graphite">
              <li className="flex items-center gap-1.5"><span className="text-pine font-bold">✓</span> Real heights in metres (AMSL, EGM2008 datum)</li>
              <li className="flex items-center gap-1.5"><span className="text-pine font-bold">✓</span> Validated landslide slope stability grading</li>
              <li className="flex items-center gap-1.5"><span className="text-pine font-bold">✓</span> Cryptographically sealed evidence passport</li>
            </ul>
          </div>

          {/* Uncalibrated Relative */}
          <div className="p-3 bg-white border border-straw rounded flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-sans text-xs font-bold text-graphite">Standard PNG / JPG (Fallback)</span>
                <span className="status-chip relative text-[9px] py-0.5">RELATIVE DEPTH · NOT METRIC</span>
              </div>
              <p className="font-body text-[11px] text-graphite/80">
                Unitless relative disparity only. Reflects ordinal spatial depth without physical height units. Non-metric and strictly forbidden for direct engineering hazard assessments.
              </p>
            </div>
            <ul className="mt-2.5 pt-2 border-t border-line space-y-1 font-mono text-[10px] text-graphite-muted">
              <li className="flex items-center gap-1.5"><span className="text-coral font-bold">!</span> No real-world meter coordinates</li>
              <li className="flex items-center gap-1.5"><span className="text-coral font-bold">!</span> Inability to calculate quantitative slope gradient</li>
              <li className="flex items-center gap-1.5"><span className="text-coral font-bold">!</span> Operational warning flag automatically appended</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
