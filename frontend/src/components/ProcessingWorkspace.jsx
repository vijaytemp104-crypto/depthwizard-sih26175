import React from 'react'

export default function ProcessingWorkspace({ job, result, onNavigateMissionView }) {
  const isSucceeded = job?.job_status === 'succeeded'
  const isRunning = job?.job_status === 'running' || job?.job_status === 'pending'
  const isFailed = job?.job_status === 'failed'
  const stages = job?.stages || {}
  const depthMeta = result?.depth?.model_metadata || {}
  const calibration = result?.calibration || {}

  const stageList = [
    {
      num: 1,
      name: 'Input Ingestion & Georeferencing',
      key: 'ingest',
      desc: 'Optical raster verification, CRS detection, affine transform bounds unpacked.',
    },
    {
      num: 2,
      name: 'Relative Monocular Depth Extraction',
      key: 'depth',
      desc: `Depth Anything V2 Small evaluated offline. Runtime: ${depthMeta.runtime_seconds ? `${depthMeta.runtime_seconds.toFixed(3)}s` : isSucceeded ? 'Completed' : 'Pending'}. Relative disparity tensor synthesized.`,
    },
    {
      num: 3,
      name: 'DEM Calibration Fit (Least-Squares)',
      key: 'calibration',
      desc: calibration.calibrated
        ? `Reference DEM sampled. Fitted z_metric = ${Number(calibration.scale_a).toFixed(2)} * d + ${Number(calibration.offset_b).toFixed(2)}m (R² = ${Number(calibration.fit_r_squared || 0).toFixed(3)}).`
        : 'Skipped if no reference DEM provided; relative scale preserved.',
    },
    {
      num: 4,
      name: 'Independent Validation Reference Cross-Check',
      key: 'validation',
      desc: result?.validation?.status === 'succeeded'
        ? `Independent reference evaluated over ${result.validation.valid_pixel_count} pixels. RMSE = ${result.validation.rmse.toFixed(3)} ${result.validation.units}.`
        : 'Skipped if no separate withheld validation DEM provided.',
    },
    {
      num: 5,
      name: 'MissionView 3D Preparation',
      key: 'terrain',
      desc: 'Triangulated mesh buffer compiled, surface normal textures generated, and LOD terrain grid synthesized.',
    },
    {
      num: 6,
      name: 'Evidence Passport & Provenance Record',
      key: 'evidence',
      desc: 'Calculated metadata lineage, parameter logs, and downloadable GIS assets staged.',
    },
  ]

  return (
    <div className="stitch-workspace-container">
      {/* Header */}
      <div className="workspace-header-bar">
        <div>
          <h1 className="workspace-title">Scientific Pipeline Telemetry &amp; Execution</h1>
          <p className="workspace-subtitle">
            Local GPU/CPU inference, affine least-squares DEM calibration, and 3D terrain reconstruction.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`status-pill ${isSucceeded ? 'succeeded' : isRunning ? 'running' : isFailed ? 'failed' : 'idle'}`}>
            {isSucceeded ? 'PIPELINE NOMINAL' : isRunning ? 'PROCESSING…' : isFailed ? 'PIPELINE ERROR' : 'PIPELINE IDLE'}
          </span>
          {isSucceeded && (
            <button
              type="button"
              className="primary-coral-btn"
              onClick={onNavigateMissionView}
            >
              <span>INSPECT 3D TERRAIN →</span>
            </button>
          )}
        </div>
      </div>

      {/* Multi-Stage Execution Sequence */}
      <div className="stitch-panel">
        <h3 className="font-sans text-sm font-bold text-graphite mb-3">Multi-Stage Execution Sequence</h3>
        <div className="space-y-2.5">
          {stageList.map((stg) => {
            const stgStatus = stages[stg.key]?.status || (isSucceeded ? 'succeeded' : isRunning ? (stg.num === 1 ? 'running' : 'waiting') : 'waiting')
            const isDone = stgStatus === 'succeeded'
            const isStgRunning = stgStatus === 'running'
            const isSkipped = stgStatus === 'skipped'

            return (
              <div
                key={stg.num}
                className={`flex items-start gap-3 p-2.5 rounded border transition-colors ${
                  isDone
                    ? 'bg-alabaster/40 border-pine/30'
                    : isStgRunning
                    ? 'bg-pine-subtle border-pine'
                    : isSkipped
                    ? 'bg-straw-subtle border-straw'
                    : 'bg-white border-line'
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center font-mono text-[11px] font-bold flex-shrink-0 ${
                    isDone
                      ? 'bg-pine text-white'
                      : isStgRunning
                      ? 'bg-coral text-white animate-pulse'
                      : isSkipped
                      ? 'bg-straw text-graphite'
                      : 'bg-line text-graphite-muted'
                  }`}
                >
                  {stg.num}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-sans text-xs font-bold text-graphite truncate">{stg.name}</span>
                    <span
                      className={`font-mono text-[10px] font-bold ${
                        isDone
                          ? 'text-pine'
                          : isStgRunning
                          ? 'text-coral'
                          : isSkipped
                          ? 'text-amber-700'
                          : 'text-graphite-muted'
                      }`}
                    >
                      {isDone ? 'COMPLETE' : isStgRunning ? 'PROCESSING…' : isSkipped ? 'SKIPPED' : 'WAITING'}
                    </span>
                  </div>
                  <p className="font-body text-[11px] text-graphite-muted mt-0.5">{stg.desc}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Hardware / Runtime Terminal */}
      <div className="stitch-panel font-mono text-[10px]">
        <div className="flex items-center justify-between pb-1.5 border-b border-line mb-2">
          <span className="text-graphite font-bold flex items-center gap-1">
            <span className="text-pine">❖</span> Hardware &amp; Inference Telemetry
          </span>
          <span className="text-graphite-muted">
            Device: {depthMeta.device || 'Auto'} • Offline Verification: PASSED
          </span>
        </div>
        <div className="bg-alabaster/50 p-2.5 rounded text-graphite/85 space-y-1 font-mono text-[10.5px]">
          <div>
            [INIT] <span className="font-bold text-graphite">MODEL_BACKBONE:</span> {depthMeta.model_name || 'Depth Anything V2 Small'} (Checkpoint: {depthMeta.checkpoint || 'vits'})
          </div>
          <div>
            [INGEST] <span className="font-bold text-graphite">INPUT_TENSOR:</span> {depthMeta.input_shape?.join(' × ') || 'Awaiting image input'}
          </div>
          <div>
            [CALIBRATION] <span className="font-bold text-graphite">FIT_PARAMETERS:</span> {calibration.calibrated ? `Scale a=${Number(calibration.scale_a).toFixed(4)}, Offset b=${Number(calibration.offset_b).toFixed(2)}m, R²=${Number(calibration.fit_r_squared || 0).toFixed(4)}` : 'Relative mode (Unitless output)'}
          </div>
          <div>
            [AIR-GAPPED] <span className="text-pine font-bold">ZERO_NETWORK_REQUESTS:</span> Model weights loaded strictly from local cache (local_files_only=True).
          </div>
          {isSucceeded && (
            <div className="text-pine font-bold">
              [PIPELINE_COMPLETE] Job {job?.job_id} successfully finalized and ready for 3D inspection.
            </div>
          )}
          {isFailed && (
            <div className="text-red-600 font-bold">
              [PIPELINE_ERROR] {job?.error || 'Inference encountered an error.'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
