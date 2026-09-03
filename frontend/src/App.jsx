import React, { useEffect, useRef, useState } from 'react'
import Header from './components/Header.jsx'
import SidebarRail from './components/SidebarRail.jsx'
import SpatialDrawer from './components/SpatialDrawer.jsx'
import UploadPanel from './components/UploadPanel.jsx'
import ProcessingWorkspace from './components/ProcessingWorkspace.jsx'
import MissionView from './components/MissionViewAnalysis.jsx'
import ValidationWorkspace from './components/ValidationWorkspace.jsx'
import EvidencePassportWorkspace from './components/EvidencePassportWorkspace.jsx'
import { artifactUrl, getJob, getJobResult, startDemoPipeline } from './api/client.js'

export default function App() {
  const [activeTab, setActiveTab] = useState('setup')
  const [selectedFile, setSelectedFile] = useState(null)
  const [referenceFile, setReferenceFile] = useState(null)
  const [validationReferenceFile, setValidationReferenceFile] = useState(null)
  const [job, setJob] = useState(null)
  const [result, setResult] = useState(null)
  const [uiState, setUiState] = useState('idle')
  const [error, setError] = useState('')
  const [textureUrl, setTextureUrl] = useState(null)

  // Manage texture preview URL
  useEffect(() => {
    if (!selectedFile) {
      setTextureUrl(null)
      return undefined
    }
    const objectUrl = URL.createObjectURL(selectedFile)
    setTextureUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [selectedFile])

  // Global Keyboard Shortcuts (Cmd/Ctrl + 1..5)
  useEffect(() => {
    const handleKeyDown = (e) => {
      const tag = document.activeElement?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return

      if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '5') {
        e.preventDefault()
        const tabMap = { '1': 'setup', '2': 'processing', '3': 'missionview', '4': 'validation', '5': 'evidence' }
        const target = tabMap[e.key]
        if (target) setActiveTab(target)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleFile = (file) => {
    if (file) {
      setSelectedFile(file)
      setReferenceFile(null)
      setValidationReferenceFile(null)
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
    setActiveTab('processing')

    try {
      const created = await startDemoPipeline(selectedFile, referenceFile, validationReferenceFile)
      setJob(created)
      setUiState(created.job_status === 'succeeded' ? 'succeeded' : 'running')
      if (created.job_status === 'succeeded') {
        setActiveTab('missionview')
      }
    } catch (requestError) {
      setUiState('error')
      setError(requestError.message)
    }
  }

  // Job status polling
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
        if (current.job_status === 'succeeded') {
          setUiState('succeeded')
          setActiveTab('missionview')
        }
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
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [job?.job_id, job?.job_status])

  // Result retrieval on job completion
  useEffect(() => {
    if (job?.job_status !== 'succeeded' || result) return
    getJobResult(job.job_id)
      .then(setResult)
      .catch((resultError) => {
        setUiState('error')
        setError(`Result retrieval failed: ${resultError.message}`)
      })
  }, [job?.job_id, job?.job_status, result])

  const missionState = error
    ? 'error'
    : !job
    ? 'empty'
    : job.job_status === 'succeeded' && !result
    ? 'loading'
    : job.job_status

  const previewArtifact = result?.input?.texture_preview?.artifact
  const effectiveTextureUrl = previewArtifact && job?.job_id ? artifactUrl(job.job_id, previewArtifact) : textureUrl

  return (
    <div className="stitch-app-shell">
      {/* 1. Global App Bar */}
      <Header job={job} result={result} onSelectTab={setActiveTab} />

      {/* 2. Workspace Layout (Sidebar Rail + Main Content Canvas + Spatial Drawer) */}
      <div className="stitch-body-layout">
        {/* Left Workflow Rail */}
        <SidebarRail
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          job={job}
          result={result}
          onVectorize={() => setActiveTab('missionview')}
        />

        {/* Central Workspace Canvas */}
        <main className="stitch-main-canvas" id="main-content">
          {/* TAB 1: Mission Setup */}
          {activeTab === 'setup' && (
            <div className="workspace-tab-pane">
              <UploadPanel
                file={selectedFile}
                referenceFile={referenceFile}
                validationReferenceFile={validationReferenceFile}
                onFileSelected={handleFile}
                onReferenceSelected={setReferenceFile}
                onValidationReferenceSelected={setValidationReferenceFile}
                onRun={runDemo}
                busy={uiState === 'uploading' || uiState === 'running'}
              />
            </div>
          )}

          {/* TAB 2: Processing Pipeline */}
          {activeTab === 'processing' && (
            <div className="workspace-tab-pane">
              <ProcessingWorkspace
                job={job}
                result={result}
                onNavigateMissionView={() => setActiveTab('missionview')}
              />
            </div>
          )}

          {/* TAB 3: 3D Analysis / MissionView */}
          {activeTab === 'missionview' && (
            <div className="workspace-tab-pane h-full flex flex-row">
              <div className="flex-1 h-full min-w-0 relative">
                <MissionView
                  terrain={result?.terrain}
                  textureUrl={effectiveTextureUrl}
                  mock={!result?.calibration?.calibrated}
                  state={missionState}
                  errorMessage={error}
                />
              </div>
              {/* Right Spatial Information Drawer */}
              <SpatialDrawer file={selectedFile} job={job} result={result} />
            </div>
          )}

          {/* TAB 4: Validation */}
          {activeTab === 'validation' && (
            <div className="workspace-tab-pane">
              <ValidationWorkspace
                job={job}
                result={result}
                artifactUrl={artifactUrl}
              />
            </div>
          )}

          {/* TAB 5: Evidence Passport */}
          {activeTab === 'evidence' && (
            <div className="workspace-tab-pane">
              <EvidencePassportWorkspace
                job={job}
                result={result}
                artifactUrl={artifactUrl}
              />
            </div>
          )}
        </main>
      </div>

      {/* Error banner if present */}
      {error && (
        <div className="global-error-toast" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError('')}>✕</button>
        </div>
      )}
    </div>
  )
}
