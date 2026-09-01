import React from 'react'

function DepthResultCard({ depth, jobId, status, artifactUrl }) {
  if (!depth) {
    return <article className={`stage-card stage-${status}`}><p className="micro-label">Relative surface</p><h3>Depth</h3><p>A source-grid relative depth layer and model metadata will appear here after inference.</p></article>
  }

  const metadata = depth.model_metadata || {}
  return (
    <article className={`stage-card depth-result-card stage-${status}`}>
      <div className="stage-top"><span>02</span><span className="waiting-tag"><i />{status}</span></div>
      <img className="depth-preview" src={artifactUrl(jobId, 'depth.png')} alt="Relative monocular depth preview" />
      <p className="micro-label">Relative surface</p>
      <div className="depth-badges"><span>REAL DEPTH</span><span>RELATIVE</span><span>NOT METRIC</span></div>
      <h3>Depth</h3>
      <dl className="depth-metadata">
        <div><dt>Model</dt><dd>{metadata.model_name || 'Unavailable'}</dd></div>
        <div><dt>Checkpoint</dt><dd>{metadata.checkpoint || 'Unavailable'}</dd></div>
        <div><dt>Device</dt><dd>{metadata.device || 'Unavailable'}</dd></div>
        <div><dt>Runtime</dt><dd>{metadata.runtime_seconds == null ? 'Unavailable' : `${metadata.runtime_seconds.toFixed(3)} s`}</dd></div>
        <div><dt>Input</dt><dd>{metadata.input_shape?.join(' × ') || 'Unavailable'}</dd></div>
        <div><dt>Output</dt><dd>{metadata.output_shape?.join(' × ') || 'Unavailable'}</dd></div>
      </dl>
      <div className="artifact-links">
        {['depth.npy', 'depth.png', 'model_metadata.json'].map((name) => <a key={name} href={artifactUrl(jobId, name)}>{name}</a>)}
      </div>
    </article>
  )
}

export default DepthResultCard
