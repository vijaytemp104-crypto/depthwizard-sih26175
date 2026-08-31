import { useRef, useState } from 'react'
import Header from './components/Header.jsx'
import WorkflowStepper from './components/WorkflowStepper.jsx'
import UploadPanel from './components/UploadPanel.jsx'
import FileSummary from './components/FileSummary.jsx'
import StageCard from './components/StageCard.jsx'

const stages = [
  { name: 'Input', detail: 'Single RGB image' },
  { name: 'Depth', detail: 'Relative surface' },
  { name: 'Calibration', detail: 'Metric alignment' },
  { name: 'Validation', detail: 'Independent proof' },
  { name: 'MissionView', detail: 'Textured 3D' },
  { name: 'Evidence', detail: 'Artifacts & provenance' },
]

const futureStages = [
  { index: '02', eyebrow: 'Relative surface', title: 'Depth', description: 'A source-grid depth layer and model metadata will appear here after inference is integrated.' },
  { index: '03', eyebrow: 'Metric alignment', title: 'Calibration / DSM', description: 'Calibration evidence and geospatial DSM artifacts will be shown only when they legitimately exist.' },
  { index: '04', eyebrow: 'Independent reference', title: 'Proof / Validation', description: 'RMSE, MAE and correlation remain absent until an independent elevation reference is available.' },
  { index: '05', eyebrow: 'Spatial inspection', title: '3D MissionView', description: 'This workspace is reserved for a future textured terrain flythrough and measurement tools.' },
  { index: '06', eyebrow: 'Traceable delivery', title: 'Downloads / Evidence', description: 'Verified artifacts, provenance and evidence exports will be collected here after processing.' },
]

function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const workspaceRef = useRef(null)

  const handleFile = (file) => {
    if (file) setSelectedFile(file)
  }

  const scrollToWorkspace = () => workspaceRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })

  return (
    <div className="app-shell">
      <Header onOpenWorkspace={scrollToWorkspace} />

      <main>
        <section className="intro" aria-labelledby="workspace-title">
          <div className="intro-copy">
            <p className="kicker"><span>SIH26175</span> · Single-view height estimation</p>
            <h1 id="workspace-title">From overhead imagery to <em>defensible</em> terrain evidence.</h1>
            <p className="intro-lede">A transparent scientific workflow for relative depth, evidence-based calibration, independent validation and future 3D mission review.</p>
          </div>
          <aside className="principle-card" aria-label="Core scientific principle">
            <span className="principle-number">01</span>
            <div>
              <p className="micro-label">Core principle</p>
              <p>Relative depth is a useful geometric signal. It is <strong>not exact metres</strong> without trustworthy calibration evidence.</p>
            </div>
          </aside>
        </section>

        <WorkflowStepper stages={stages} activeIndex={0} />

        <section className="workspace-grid" ref={workspaceRef}>
          <UploadPanel onFileSelected={handleFile} />
          <div className="workspace-side">
            <FileSummary file={selectedFile} onClear={() => setSelectedFile(null)} />
            <section className="flow-card" aria-labelledby="future-flow-title">
              <div className="section-heading compact">
                <div><p className="micro-label">Future pipeline</p><h2 id="future-flow-title">What happens next</h2></div>
                <span className="not-live-tag">Not connected</span>
              </div>
              <ol className="flow-list">
                {['RGB image', 'Relative depth', 'Calibration', 'DSM', 'Independent validation', 'Textured 3D', 'Measurements & evidence'].map((item, index) => (
                  <li key={item}><span>{String(index + 1).padStart(2, '0')}</span>{item}</li>
                ))}
              </ol>
            </section>
          </div>
        </section>

        <section className="guardrail-strip" aria-label="Scientific data rules">
          <div><span>PNG · JPG</span><p>Relative mode by default. Exact metric claims require valid external calibration evidence.</p></div>
          <div><span>GeoTIFF</span><p>May preserve CRS, affine transform and pixel scale for geospatial processing.</p></div>
          <div><span>Validation</span><p>Metrics appear only against an independent reference elevation source.</p></div>
        </section>

        <section className="future-section" aria-labelledby="future-stages-title">
          <div className="section-heading">
            <div><p className="micro-label">Downstream workspaces</p><h2 id="future-stages-title">Built for the full mission workflow</h2></div>
            <p>Each surface remains deliberately empty until real processing is connected.</p>
          </div>
          <div className="stage-grid">
            {futureStages.map((stage) => <StageCard key={stage.title} {...stage} />)}
          </div>
        </section>
      </main>

      <footer><span>DepthWizard · Smart India Hackathon 2026</span><span>Workflow shell · No processing connected</span></footer>
    </div>
  )
}

export default App
