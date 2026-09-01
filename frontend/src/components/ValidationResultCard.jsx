import React from 'react'

function ValidationResultCard({ validation, evidence, jobId, status, artifactUrl }) {
  if (validation?.status !== 'succeeded') {
    return (
      <article className={`stage-card stage-${status}`}>
        <p className="micro-label">Independent reference</p><span className="mock-label">{status?.toUpperCase()}</span>
        <h3>Independent Validation</h3>
        <p>{validation?.reason || 'Awaiting a separate independent elevation reference.'}</p>
      </article>
    )
  }
  const correlation = validation.correlation == null ? 'Undefined' : validation.correlation.toFixed(5)
  return (
    <article className={`stage-card calibration-result-card stage-${status}`}>
      <div className="stage-top"><span>04</span><span className="waiting-tag"><i />{status}</span></div>
      <p className="micro-label">Independent reference</p>
      <div className="depth-badges"><span>INDEPENDENT VALIDATION</span><span>METRIC DSM</span></div>
      <h3>Independent Validation</h3>
      <dl className="depth-metadata">
        <div><dt>RMSE</dt><dd>{validation.rmse.toFixed(3)} {validation.units}</dd></div>
        <div><dt>MAE</dt><dd>{validation.mae.toFixed(3)} {validation.units}</dd></div>
        <div><dt>Pearson correlation</dt><dd>{correlation}</dd></div>
        <div><dt>Valid pixels</dt><dd>{validation.valid_pixel_count}</dd></div>
        <div><dt>Reference</dt><dd>{validation.reference_source}</dd></div>
        <div><dt>Units</dt><dd>{validation.units}</dd></div>
      </dl>
      {validation.warnings?.map((warning) => <p className="calibration-warning" key={warning}>{warning}</p>)}
      <div className="artifact-links">
        <a href={artifactUrl(jobId, 'metrics.json')}>metrics.json</a>
        <a href={artifactUrl(jobId, 'error_map.tif')}>error_map.tif</a>
        {evidence?.evidence_passport && <a href={artifactUrl(jobId, 'evidence_passport.json')}>evidence_passport.json</a>}
      </div>
    </article>
  )
}

export default ValidationResultCard
