import React from 'react'

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 bytes'
  const units = ['bytes', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** index
  return `${value.toFixed(index === 0 ? 0 : 2)} ${units[index]}`
}

const extensionOf = (name) => name.includes('.') ? name.split('.').pop().toUpperCase() : 'Unknown'

function FileSummary({ file, onClear }) {
  return (
    <section className="file-card" aria-labelledby="file-summary-title">
      <div className="section-heading compact">
        <div><p className="micro-label">Local inspection</p><h2 id="file-summary-title">Selected file</h2></div>
        {file && <button className="text-button" type="button" onClick={onClear}>Clear</button>}
      </div>
      {file ? (
        <dl className="file-facts">
          <div><dt>Filename</dt><dd title={file.name}>{file.name}</dd></div>
          <div><dt>Extension</dt><dd>{extensionOf(file.name)}</dd></div>
          <div><dt>Browser type</dt><dd>{file.type || 'Not reported'}</dd></div>
          <div><dt>File size</dt><dd>{formatBytes(file.size)}</dd></div>
        </dl>
      ) : (
        <div className="empty-file"><span aria-hidden="true">＋</span><p>No image selected</p><small>Only browser-known facts will appear here. No CRS, coordinates, elevation or depth is inferred.</small></div>
      )}
    </section>
  )
}

export default FileSummary
