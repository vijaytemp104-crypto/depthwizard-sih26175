import React, { useEffect, useRef, useState } from 'react'
import Header from './components/Header.jsx'
import WorkflowStepper from './components/WorkflowStepper.jsx'
import UploadPanel from './components/UploadPanel.jsx'
import FileSummary from './components/FileSummary.jsx'
import StageCard from './components/StageCard.jsx'
import DepthResultCard from './components/DepthResultCard.jsx'
import MissionView from './components/MissionView.jsx'
import { artifactUrl, getJob, getJobResult, startDemoPipeline } from './api/client.js'

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

const stageKeys = ['ingest', 'depth', 'calibration', 'validation', 'terrain', 'evidence']

const resultCopy = {
  depth: { label: 'REAL DEPTH', title: 'Depth', done: 'Relative monocular inference — not metric elevation' },
  calibration: { label: 'SKIPPED', title: 'Calibration / DSM', done: 'Skipped — awaiting calibration module' },
  validation: { label: 'SKIPPED', title: 'Proof / Validation', done: 'Skipped — awaiting independent validation' },
  terrain: { label: 'PLACEHOLDER', title: '3D MissionView', done: 'Synthetic 2×2 unitless grid only — no terrain or elevation output' },
  evidence: { label: 'PROVENANCE', title: 'Downloads / Evidence', done: 'Real depth model provenance; not independent validation' },
}

function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [job, setJob] = useState(null)
  const [result, setResult] = useState(null)
  const [uiState, setUiState] = useState('idle')
  const [error, setError] = useState('')
  const [textureUrl, setTextureUrl] = useState(null)
  const workspaceRef = useRef(null)

  useEffect(() => {
    if (!selectedFile) {
      setTextureUrl(null)
      return undefined
    }
    const objectUrl = URL.createObjectURL(selectedFile)
    setTextureUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [selectedFile])

  const handleFile = (file) => {
    if (file) {
      setSelectedFile(file)
      setJob(null)
      setResult(null)
      setError('')
      setUiState('idle')
    }
  }

  const runDemo = async () => {
    if (!selectedFile || uiState === 'uploading' || uiState === 'running') return
    setError('')
    setResult(null)
    setUiState('uploading')
    try {
      const created = await startDemoPipeline(selectedFile)
      setJob(created)
      setUiState(created.job_status === 'succeeded' ? 'succeeded' : 'running')
    } catch (requestError) {
      setUiState('error')
      setError(requestError.message)
    }
  }

  useEffect(() => {
    if (!job?.job_id || !['running', 'pending'].includes(job.job_status)) return undefined
    let cancelled = false
    let failures = 0
    const poll = async () => {
      try {
        const current = await getJob(job.job_id)
        if (cancelled) return
        failures = 0
        setJob(current)
        if (current.job_status === 'succeeded') setUiState('succeeded')
        if (current.job_status === 'failed') {
          setUiState('error')
        setError('Relative-depth inference could not complete. No fake success output was produced.')
        }
      } catch (pollError) {
        failures += 1
        if (failures >= 3 && !cancelled) {
          setUiState('error')
          setError(`Status polling failed: ${pollError.message}`)
        }
      }
    }
    poll()
    const timer = window.setInterval(poll, 800)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [job?.job_id, job?.job_status])

  useEffect(() => {
    if (job?.job_status !== 'succeeded' || result) return
    getJobResult(job.job_id)
      .then(setResult)
      .catch((resultError) => {
        setUiState('error')
        setError(`Result retrieval failed: ${resultError.message}`)
      })
  }, [job?.job_id, job?.job_status, result])

  const workflowStates = Object.fromEntries(stageKeys.map((key) => [key, job?.stages?.[key]?.status || 'waiting']))
  const futureCards = futureStages.map((card, index) => {
    const key = stageKeys[index + 1]
    const output = resultCopy[key]
    const status = workflowStates[key]
    return {
      ...card,
      status,
      label: result && output ? output.label : null,
      description: result && output ? output.done : card.description,
      downloads: result && key === 'evidence'
        ? ['depth.npy', 'depth.png', 'model_metadata.json', 'depth_evidence.json'].map((name) => ({ name, href: artifactUrl(job.job_id, name) }))
        : [],
    }
  })

  const scrollToWorkspace = () => workspaceRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  const missionState = error
    ? 'error'
    : !job
      ? 'empty'
      : job.job_status === 'succeeded' && !result
        ? 'loading'
        : job.job_status

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

        <WorkflowStepper stages={stages} stageStates={workflowStates} />

        <section className="demo-banner" aria-label="Pipeline notice">
          <strong>{result ? 'REAL DEPTH · RELATIVE · NOT METRIC' : 'RELATIVE DEPTH PIPELINE'}</strong>
          <p>Depth inference uses Depth Anything V2 Small. Calibration and independent validation are not yet integrated; the 3D terrain remains synthetic.</p>
          <span>{job ? `JOB ${job.job_id.slice(0, 8).toUpperCase()}` : 'NO JOB CREATED'}</span>
        </section>

        <section className="workspace-grid" ref={workspaceRef}>
          <UploadPanel file={selectedFile} onFileSelected={handleFile} onRun={runDemo} busy={uiState === 'uploading' || uiState === 'running'} />
          <div className="workspace-side">
            <FileSummary file={selectedFile} onClear={() => setSelectedFile(null)} />
            <section className="flow-card" aria-labelledby="future-flow-title">
              <div className="section-heading compact">
                <div><p className="micro-label">Future pipeline</p><h2 id="future-flow-title">What happens next</h2></div>
                <span className={job ? 'active-tag' : 'not-live-tag'}>{job ? job.job_status : 'Not started'}</span>
              </div>
              <ol className="flow-list">
                {['RGB image', 'Relative depth', 'Calibration', 'DSM', 'Independent validation', 'Textured 3D', 'Measurements & evidence'].map((item, index) => (
                  <li key={item}><span>{String(index + 1).padStart(2, '0')}</span>{item}</li>
                ))}
              </ol>
            </section>
          </div>
        </section>

        {error && <div className="error-banner" role="alert"><strong>Depth pipeline error</strong><span>{error}</span></div>}

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
            {futureCards.map((stage) => stage.title === 'Depth'
              ? <DepthResultCard key={stage.title} depth={result?.depth} jobId={job?.job_id} status={stage.status} artifactUrl={artifactUrl} />
              : stage.title === '3D MissionView'
                ? <MissionView key={stage.title} terrain={result?.terrain} textureUrl={textureUrl} mock={result?.terrain?.mock} state={missionState} errorMessage={error} />
                : <StageCard key={stage.title} {...stage} />)}
          </div>
        </section>
      </main>

      <footer><span>DepthWizard · Smart India Hackathon 2026</span><span>Relative depth · No metric claim without calibration</span></footer>
    </div>
  )
}

export default App
