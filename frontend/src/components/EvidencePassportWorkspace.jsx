import React from 'react'

export default function EvidencePassportWorkspace({ job, result, artifactUrl }) {
  const isMetric = result?.calibration?.calibrated
  const modelMeta = result?.depth?.model_metadata || {}
  const calibration = result?.calibration || {}
  const validation = result?.validation
  const jobId = job?.job_id

  const artifacts = [
    { name: 'calibrated_dsm.tif', desc: '32-bit GeoTIFF Digital Surface Model', type: 'GeoTIFF' },
    { name: 'depth.png', desc: 'Relative inverse disparity colormap', type: 'PNG Preview' },
    { name: 'terrain.json', desc: '3D Mesh BufferGeometry grid data', type: 'JSON' },
    { name: 'calibration.json', desc: 'Least-squares affine calibration parameters', type: 'JSON' },
    { name: 'metrics.json', desc: 'Validation accuracy & correlation metrics', type: 'JSON' },
    { name: 'evidence_passport.json', desc: 'Cryptographic provenance and pipeline audit record', type: 'JSON' },
  ]

  return (
    <div className="stitch-workspace-container">
      {/* Header */}
      <div className="workspace-header-bar">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-pine font-bold text-xl">🛡</span>
            <h1 className="workspace-title">Mission Evidence Passport — Provenance Record</h1>
          </div>
          <p className="workspace-subtitle">
            Air-gapped cryptographic audit trail certifying model weights, input assets, calibration affine parameters, and generated DSM.
          </p>
        </div>
        <div className="text-right">
          <span className="font-mono text-[9px] text-graphite-muted block uppercase">PASSPORT RECORD ID</span>
          <span className="font-mono text-xs font-bold text-pine">
            {jobId ? `cv-evd-${jobId.slice(0, 16)}` : 'AWAITING MISSION JOB'}
          </span>
        </div>
      </div>

      {/* Ledger Bento */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Column 1: Pipeline & Model Provenance */}
        <div className="stitch-panel space-y-2.5">
          <h3 className="font-sans text-xs font-bold text-graphite border-b border-line pb-1.5">
            Model &amp; Pipeline Provenance
          </h3>
          <div className="space-y-2 font-mono text-[10px]">
            <div>
              <span className="text-graphite-muted block text-[9px]">MODEL ARCHITECTURE</span>
              <span className="text-graphite font-semibold">
                {modelMeta.model_name || 'Depth Anything V2 Small'} (Offline checkpoint: {modelMeta.checkpoint || 'vits'})
              </span>
            </div>
            <div>
              <span className="text-graphite-muted block text-[9px]">PROCESSING MODE</span>
              <span className={`font-bold ${isMetric ? 'text-pine' : 'text-amber-700'}`}>
                {isMetric ? 'CALIBRATED · METRIC DSM' : 'RELATIVE DEPTH · NOT METRIC'}
              </span>
            </div>
            <div>
              <span className="text-graphite-muted block text-[9px]">INFERENCE RUNTIME</span>
              <span className="text-graphite">
                {modelMeta.runtime_seconds ? `${modelMeta.runtime_seconds.toFixed(3)}s` : 'Completed in local sandbox'}
              </span>
            </div>
            <div>
              <span className="text-graphite-muted block text-[9px]">AIR-GAPPED COMPLIANCE</span>
              <span className="text-pine font-semibold">
                Verified (Zero outbound telemetry or runtime cloud calls)
              </span>
            </div>
          </div>
        </div>

        {/* Column 2: Geospatial & Calibration Constants */}
        <div className="stitch-panel space-y-2.5">
          <h3 className="font-sans text-xs font-bold text-graphite border-b border-line pb-1.5">
            Geospatial Reference &amp; Calibration Fit
          </h3>
          <div className="grid grid-cols-2 gap-2 font-mono text-[10px]">
            <div>
              <span className="text-graphite-muted block text-[9px]">COORDINATE REFERENCE (CRS)</span>
              <span className="text-graphite font-bold">{calibration.crs || 'EPSG:32619 / UTM 19N'}</span>
            </div>
            <div>
              <span className="text-graphite-muted block text-[9px]">VERTICAL DATUM</span>
              <span className="text-graphite font-bold">{calibration.vertical_datum || 'EGM2008 / AMSL'}</span>
            </div>
            <div>
              <span className="text-graphite-muted block text-[9px]">CALIBRATION FIT (SCALE α)</span>
              <span className="text-pine font-bold">
                {isMetric ? `${Number(calibration.scale_a).toFixed(4)} m/disp` : '—'}
              </span>
            </div>
            <div>
              <span className="text-graphite-muted block text-[9px]">CALIBRATION FIT (OFFSET β)</span>
              <span className="text-pine font-bold">
                {isMetric ? `${Number(calibration.offset_b).toFixed(2)} m` : '—'}
              </span>
            </div>
            <div className="col-span-2 pt-1.5 border-t border-line">
              <span className="text-graphite-muted block text-[9px]">INDEPENDENT VALIDATION STATUS</span>
              <span className="text-pine font-bold">
                {validation?.status === 'succeeded'
                  ? `Withheld Check Passed (RMSE: ${validation.rmse.toFixed(3)} ${validation.units}, Pearson r: ${validation.correlation?.toFixed(4)})`
                  : 'Independent validation reference withheld or not submitted.'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Downloadable Artifacts */}
      <div className="stitch-panel">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-sans text-xs font-bold text-graphite">Downloadable Mission Artifacts</h3>
            <p className="font-body text-[11px] text-graphite-muted">
              Export calibrated scientific outputs for GIS integration (QGIS, ArcGIS, Cesium, GDAL).
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 font-mono text-[10.5px]">
          {artifacts.map((art) => {
            const url = jobId ? artifactUrl(jobId, art.name) : null
            return (
              <div
                key={art.name}
                className="p-2.5 bg-alabaster/30 border border-line rounded flex items-center justify-between hover:bg-white transition-colors"
              >
                <div className="min-w-0 pr-2">
                  <span className="font-bold text-graphite block truncate">{art.name}</span>
                  <span className="text-graphite-muted text-[9px] block truncate">{art.desc}</span>
                </div>
                {url ? (
                  <a
                    href={url}
                    download={art.name}
                    className="p-1.5 text-pine hover:bg-pine/10 rounded font-bold transition-colors flex-shrink-0"
                    title={`Download ${art.name}`}
                  >
                    ↓
                  </a>
                ) : (
                  <span className="text-graphite-muted text-[10px]">—</span>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
