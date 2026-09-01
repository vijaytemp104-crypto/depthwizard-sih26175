import React from 'react'

function CalibrationResultCard({ calibration, jobId, status, artifactUrl }) {
  if (!calibration?.calibrated) {
    return (
      <article className={`stage-card stage-${status}`}>
        <p className="micro-label">Metric alignment</p><span className="mock-label">{status?.toUpperCase()}</span>
        <h3>Calibration / DSM</h3><p>{calibration?.reason || 'Awaiting a georeferenced source and reference DEM.'}</p>
      </article>
    )
  }
  return (
    <article className={`stage-card calibration-result-card stage-${status}`}>
      <div className="stage-top"><span>03</span><span className="waiting-tag"><i />{status}</span></div>
      <p className="micro-label">Metric alignment</p>
      <div className="depth-badges"><span>CALIBRATED</span><span>METRIC</span><span>CALIBRATION FIT</span></div>
      <h3>Calibration / DSM</h3>
      <dl className="depth-metadata">
        <div><dt>Reference</dt><dd>{calibration.reference_source}</dd></div>
        <div><dt>Method</dt><dd>{calibration.method}</dd></div>
        <div><dt>Scale a</dt><dd>{calibration.scale_a}</dd></div>
        <div><dt>Offset b</dt><dd>{calibration.offset_b}</dd></div>
        <div><dt>Fit RMSE</dt><dd>{calibration.fit_rmse_metres?.toFixed(3)} m · calibration fit only</dd></div>
        <div><dt>Fit R²</dt><dd>{calibration.fit_r_squared?.toFixed(5)} · calibration fit only</dd></div>
        <div><dt>Valid pixels</dt><dd>{calibration.valid_anchor_count}</dd></div>
        <div><dt>CRS</dt><dd>{calibration.crs}</dd></div>
      </dl>
      {calibration.warnings?.map((warning) => <p className="calibration-warning" key={warning}>{warning}</p>)}
      <div className="artifact-links">
        {['calibrated_dsm.tif', 'terrain.json', 'calibration.json'].map((name) => <a key={name} href={artifactUrl(jobId, name)}>{name}</a>)}
      </div>
    </article>
  )
}

export default CalibrationResultCard
