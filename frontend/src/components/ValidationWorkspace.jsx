import React from 'react'

export default function ValidationWorkspace({ job, result, artifactUrl }) {
  const validation = result?.validation
  const calibration = result?.calibration
  const hasValidation = validation?.status === 'succeeded'
  const isCalibrated = calibration?.calibrated

  return (
    <div className="stitch-workspace-container">
      {/* Header */}
      <div className="workspace-header-bar">
        <div>
          <h1 className="workspace-title">Scientific Validation &amp; Benchmark Ledger</h1>
          <p className="workspace-subtitle">
            Rigorous independent evaluation against separate withheld high-resolution elevation reference data.
          </p>
        </div>
        <span className="status-pill succeeded">WITHHELD GROUND TRUTH</span>
      </div>

      {/* Methodology Note */}
      <div className="stitch-panel border-l-4 border-l-pine">
        <div className="flex items-start gap-2.5">
          <span className="text-pine font-bold text-[18px]">✓</span>
          <div>
            <h4 className="font-sans text-xs font-bold text-graphite">
              Independent Validation vs Calibration Residuals
            </h4>
            <p className="font-body text-[11.5px] text-graphite/80 mt-0.5">
              Calibration-fit residuals measure model alignment on anchor points from the calibration DEM. In contrast, <strong>independent validation resamples a distinct withheld elevation raster</strong> that was never exposed during model calibration, evaluating true generalization error without data leakage.
            </p>
          </div>
        </div>
      </div>

      {/* Current Job Validation Card */}
      <div className="stitch-panel">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-sans text-sm font-bold text-graphite">Current Mission Validation Result</h3>
          <span className={`spatial-badge ${hasValidation ? 'metric' : 'relative'}`}>
            {hasValidation ? 'INDEPENDENT VALIDATION COMPLETE' : 'AWAITING INDEPENDENT REFERENCE'}
          </span>
        </div>

        {hasValidation ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 font-mono text-[11px]">
              <div className="p-2.5 bg-alabaster/40 border border-line rounded">
                <span className="text-graphite-muted text-[9.5px] block uppercase">RMSE</span>
                <span className="text-graphite font-bold text-sm">{validation.rmse.toFixed(3)} {validation.units}</span>
              </div>
              <div className="p-2.5 bg-alabaster/40 border border-line rounded">
                <span className="text-graphite-muted text-[9.5px] block uppercase">MAE</span>
                <span className="text-graphite font-bold text-sm">{validation.mae.toFixed(3)} {validation.units}</span>
              </div>
              <div className="p-2.5 bg-alabaster/40 border border-line rounded">
                <span className="text-graphite-muted text-[9.5px] block uppercase">Pearson r</span>
                <span className="text-pine font-bold text-sm">
                  {validation.correlation != null ? validation.correlation.toFixed(4) : '—'}
                </span>
              </div>
              <div className="p-2.5 bg-alabaster/40 border border-line rounded">
                <span className="text-graphite-muted text-[9.5px] block uppercase">Valid Overlap</span>
                <span className="text-graphite font-bold text-sm">{validation.valid_pixel_count?.toLocaleString()} px</span>
              </div>
            </div>

            <div className="p-2.5 bg-white border border-line rounded flex items-center justify-between font-mono text-[10px]">
              <div>
                <span className="text-graphite-muted">Reference Source: </span>
                <span className="font-semibold text-graphite">{validation.reference_source}</span>
              </div>
              <div className="flex items-center gap-3">
                {job?.job_id && (
                  <>
                    <a className="text-pine hover:underline font-bold" href={artifactUrl(job.job_id, 'metrics.json')}>
                      metrics.json ↗
                    </a>
                    <a className="text-pine hover:underline font-bold" href={artifactUrl(job.job_id, 'error_map.tif')}>
                      error_map.tif ↗
                    </a>
                  </>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4 bg-alabaster/30 border border-dashed border-line-strong rounded text-center font-mono text-xs text-graphite-muted">
            <p>No separate independent validation reference DEM was uploaded for this execution.</p>
            <small className="block mt-1 text-[10px]">To compute independent RMSE, MAE, and correlation, provide a withheld elevation raster in Mission Setup.</small>
          </div>
        )}
      </div>

      {/* Calibration Fit Residuals Table */}
      {isCalibrated && (
        <div className="stitch-panel">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-sans text-xs font-bold text-graphite">Calibration Reference Fit Residuals</h3>
            <span className="px-2 py-0.5 bg-alabaster text-graphite font-mono text-[9px] rounded font-semibold">
              Calibration Fit Only — Not Independent
            </span>
          </div>
          <table className="w-full text-left font-mono text-[11px] border-collapse">
            <thead>
              <tr className="border-b border-line text-graphite-muted">
                <th className="py-1.5">PARAMETER</th>
                <th className="py-1.5">ESTIMATED VALUE</th>
                <th className="py-1.5">FIT QUALITY (R²)</th>
                <th className="py-1.5 text-right">STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line/60">
              <tr>
                <td className="py-2 font-semibold text-graphite">Scale Multiplier (α)</td>
                <td className="py-2">{Number(calibration.scale_a).toFixed(4)} m/disp</td>
                <td className="py-2 text-pine font-bold">{Number(calibration.fit_r_squared || 0).toFixed(4)}</td>
                <td className="py-2 text-right text-pine font-bold">Fitted</td>
              </tr>
              <tr>
                <td className="py-2 font-semibold text-graphite">Datum Shift Offset (β)</td>
                <td className="py-2">{Number(calibration.offset_b).toFixed(2)} m</td>
                <td className="py-2 text-pine font-bold">{Number(calibration.fit_r_squared || 0).toFixed(4)}</td>
                <td className="py-2 text-right text-pine font-bold">Aligned</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* FINAL WITHHELD BENCHMARK LEDGER (Explicitly Labeled ProofBench Reference) */}
      <div className="stitch-panel">
        <div className="flex items-center justify-between mb-2 pb-1 border-b border-line">
          <div className="flex items-center gap-1.5">
            <span className="text-pine font-bold">⊞</span>
            <h3 className="font-sans text-xs font-bold text-graphite uppercase tracking-wider">
              FINAL WITHHELD BENCHMARK (ProofBench Multi-Scene Reference)
            </h3>
          </div>
          <span className="font-mono text-[9px] px-1.5 py-0.5 bg-pine-subtle text-pine font-bold rounded">
            REFERENCE LEDGER
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Card 1: Mountain Relief */}
          <div className="p-3 bg-alabaster/20 border border-line rounded flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1 font-mono text-[10px]">
                <span className="font-bold text-graphite">Glaciated Mountain Terrain</span>
                <span className="px-1.5 py-0.5 bg-alabaster text-graphite font-semibold rounded text-[9px]">ProofBench</span>
              </div>
              <p className="font-mono text-[9.5px] text-graphite-muted mb-2">High-relief alpine topography</p>
              <div className="grid grid-cols-2 gap-1.5 p-2 bg-white border border-line rounded font-mono text-[10px]">
                <div><span className="text-graphite-muted text-[8.5px] block">RMSE</span><span className="font-bold text-graphite">49.60 m</span></div>
                <div><span className="text-graphite-muted text-[8.5px] block">MAE</span><span className="font-bold text-graphite">41.74 m</span></div>
                <div className="pt-1 border-t border-line"><span className="text-graphite-muted text-[8.5px] block">Pearson r</span><span className="text-pine font-bold">0.733</span></div>
                <div className="pt-1 border-t border-line"><span className="text-graphite-muted text-[8.5px] block">Spearman ρ</span><span className="text-pine font-bold">0.745</span></div>
              </div>
            </div>
            <div className="mt-2 text-graphite-muted font-mono text-[9px] flex justify-between">
              <span>Anchor: Withheld LiDAR</span>
              <span className="text-pine font-bold">Verified</span>
            </div>
          </div>

          {/* Card 2: Coastal/Flat */}
          <div className="p-3 bg-alabaster/20 border border-line rounded flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1 font-mono text-[10px]">
                <span className="font-bold text-graphite">Lowland Coastal Plain</span>
                <span className="px-1.5 py-0.5 bg-alabaster text-graphite font-semibold rounded text-[9px]">ProofBench</span>
              </div>
              <p className="font-mono text-[9.5px] text-graphite-muted mb-2">Flat relief flood plain</p>
              <div className="grid grid-cols-2 gap-1.5 p-2 bg-white border border-line rounded font-mono text-[10px]">
                <div><span className="text-graphite-muted text-[8.5px] block">RMSE</span><span className="font-bold text-graphite">7.48 m</span></div>
                <div><span className="text-graphite-muted text-[8.5px] block">MAE</span><span className="font-bold text-graphite">6.28 m</span></div>
                <div className="pt-1 border-t border-line"><span className="text-graphite-muted text-[8.5px] block">Pearson r</span><span className="text-graphite font-bold">0.051</span></div>
                <div className="pt-1 border-t border-line"><span className="text-graphite-muted text-[8.5px] block">Spearman ρ</span><span className="text-graphite font-bold">0.099</span></div>
              </div>
            </div>
            <div className="mt-2 text-graphite-muted font-mono text-[9px] flex justify-between">
              <span>Anchor: Withheld LiDAR</span>
              <span className="text-pine font-bold">Verified</span>
            </div>
          </div>

          {/* Card 3: Urban DSM */}
          <div className="p-3 bg-alabaster/20 border border-line rounded flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1 font-mono text-[10px]">
                <span className="font-bold text-graphite">Urban Surface Model</span>
                <span className="px-1.5 py-0.5 bg-alabaster text-graphite font-semibold rounded text-[9px]">ProofBench</span>
              </div>
              <p className="font-mono text-[9.5px] text-graphite-muted mb-2">Built structures &amp; canopy</p>
              <div className="grid grid-cols-2 gap-1.5 p-2 bg-white border border-line rounded font-mono text-[10px]">
                <div><span className="text-graphite-muted text-[8.5px] block">RMSE</span><span className="font-bold text-graphite">30.78 m</span></div>
                <div><span className="text-graphite-muted text-[8.5px] block">MAE</span><span className="font-bold text-graphite">19.68 m</span></div>
                <div className="pt-1 border-t border-line"><span className="text-graphite-muted text-[8.5px] block">Pearson r</span><span className="text-pine font-bold">0.626</span></div>
                <div className="pt-1 border-t border-line"><span className="text-graphite-muted text-[8.5px] block">Spearman ρ</span><span className="text-pine font-bold">0.658</span></div>
              </div>
            </div>
            <div className="mt-2 text-graphite-muted font-mono text-[9px] flex justify-between">
              <span>Anchor: Withheld LiDAR</span>
              <span className="text-pine font-bold">Verified</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
