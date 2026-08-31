import { useRef, useState } from 'react'

const ACCEPTED = '.png,.jpg,.jpeg,.tif,.tiff,image/png,image/jpeg,image/tiff'

function UploadPanel({ onFileSelected }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const chooseFirst = (files) => {
    const file = files?.[0]
    if (file) onFileSelected(file)
  }

  return (
    <section className="upload-card" aria-labelledby="upload-title">
      <div className="section-heading compact">
        <div><p className="micro-label">01 · Mission input</p><h2 id="upload-title">Add overhead imagery</h2></div>
        <span className="active-tag">Active stage</span>
      </div>
      <p className="upload-intro">Choose one overhead RGB satellite or aerial image. Selection stays in your browser for now and does not start processing.</p>
      <div
        className={`drop-zone ${dragging ? 'dragging' : ''}`}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true) }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => { event.preventDefault(); setDragging(false) }}
        onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFirst(event.dataTransfer.files) }}
      >
        <input ref={inputRef} type="file" accept={ACCEPTED} onChange={(event) => chooseFirst(event.target.files)} aria-label="Select an overhead image" />
        <span className="drop-icon" aria-hidden="true"><i /><i /></span>
        <h3>Drop a single image here</h3>
        <p>or browse a local file to inspect its basic metadata</p>
        <button className="primary-button" type="button" onClick={() => inputRef.current?.click()}>Select image <span aria-hidden="true">↗</span></button>
        <small>PNG · JPG/JPEG · GeoTIFF/TIF/TIFF</small>
      </div>
      <div className="mode-row">
        <article><span className="mode-icon">R</span><div><strong>Relative mode</strong><p>Ordinary PNG/JPG inputs remain in arbitrary relative units unless calibration evidence is supplied.</p></div></article>
        <article><span className="mode-icon geo">G</span><div><strong>Geospatial-capable</strong><p>GeoTIFF may carry CRS, transform and pixel scale; metric output still requires valid evidence.</p></div></article>
      </div>
    </section>
  )
}

export default UploadPanel
