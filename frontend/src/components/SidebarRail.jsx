import React from 'react'

const TABS = [
  { id: 'setup', num: '1', title: 'Mission Setup', desc: 'Optical & DEM references', icon: 'radar' },
  { id: 'processing', num: '2', title: 'Processing Pipeline', desc: 'Telemetry & transforms', icon: 'reorder' },
  { id: 'missionview', num: '3', title: '3D Analysis / MissionView', desc: 'Interactive terrain viewport', icon: 'public' },
  { id: 'validation', num: '4', title: 'Validation', desc: 'LiDAR ground truth stats', icon: 'fact_check' },
  { id: 'evidence', num: '5', title: 'Evidence Passport', desc: 'Ledger & artifact exports', icon: 'verified_user' },
]

const STAGE_KEYS = [
  { key: 'ingest', label: 'INP', title: 'Input Ingestion' },
  { key: 'depth', label: 'DEP', title: 'Depth Synthesis' },
  { key: 'calibration', label: 'CAL', title: 'DEM Calibration' },
  { key: 'validation', label: 'VAL', title: 'Validation Check' },
  { key: 'terrain', label: 'MSN', title: '3D Viewport' },
  { key: 'evidence', label: 'EVD', title: 'Evidence Passport' },
]

export default function SidebarRail({ activeTab, onSelectTab, job, result, onVectorize }) {
  const isMetric = result?.calibration?.calibrated
  const crs = result?.calibration?.crs || 'EPSG:32619'
  const stages = job?.stages || {}

  return (
    <nav className="stitch-sidebar-rail" aria-label="Scientific Workflow Navigation">
      {/* Sidebar Header */}
      <div className="sidebar-rail-header">
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs font-bold text-pine uppercase tracking-wider">ORBITAL WORKSPACE</span>
          <span className="font-mono text-[10px] px-1.5 py-0.5 bg-alabaster text-graphite font-semibold rounded">SIH26175</span>
        </div>
        <p className="font-mono text-[10px] text-graphite-muted mt-0.5">
          {crs} • {isMetric ? 'Metric Calibrated' : 'Relative Surface'}
        </p>
      </div>

      {/* Main Navigation Tabs */}
      <div className="sidebar-rail-nav">
        <div className="flex flex-col gap-1.5">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                type="button"
                className={`sidebar-nav-btn ${isActive ? 'active' : ''}`}
                onClick={() => onSelectTab(tab.id)}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="material-symbols-outlined text-[18px] flex-shrink-0">
                    {tab.icon === 'radar' ? '◎' : tab.icon === 'reorder' ? '≡' : tab.icon === 'public' ? '⊕' : tab.icon === 'fact_check' ? '✓' : '🛡'}
                  </span>
                  <div className="flex flex-col text-left truncate">
                    <span className="font-mono text-[12px] font-bold truncate leading-tight">{tab.title}</span>
                    <span className="font-mono text-[10px] opacity-75 truncate leading-tight">{tab.desc}</span>
                  </div>
                </div>
                <kbd className="sidebar-kbd">⌘{tab.num}</kbd>
              </button>
            )
          })}
        </div>

        {/* Mini 6-Stage Flow Box */}
        <div className="sidebar-flow-box">
          <div className="flex items-center justify-between mb-1.5 font-mono text-[9px]">
            <span className="font-bold text-graphite-muted uppercase tracking-wider">Scientific Pipeline</span>
            <span className="font-bold text-pine">
              {job ? (job.job_status === 'succeeded' ? '100% SECURED' : job.job_status.toUpperCase()) : 'IDLE'}
            </span>
          </div>
          <div className="grid grid-cols-6 gap-1 text-center font-mono text-[9px]">
            {STAGE_KEYS.map((stage) => {
              const status = stages[stage.key]?.status || (job ? 'waiting' : 'idle')
              const isSucceeded = status === 'succeeded'
              const isRunning = status === 'running'
              const isSkipped = status === 'skipped'
              let stateClass = 'stage-chip-idle'
              if (isRunning) stateClass = 'stage-chip-running'
              else if (isSucceeded) stateClass = 'stage-chip-succeeded'
              else if (isSkipped) stateClass = 'stage-chip-skipped'

              return (
                <div
                  key={stage.key}
                  className={`stage-mini-chip ${stateClass}`}
                  title={`${stage.title}: ${status}`}
                >
                  {stage.label}
                </div>
              )
            })}
          </div>
        </div>

        {/* Vectorize / View Terrain Quick Action */}
        <div className="sidebar-action-wrap">
          <button
            type="button"
            className="sidebar-vectorize-btn"
            onClick={() => onSelectTab('missionview')}
          >
            <span className="text-[14px]">☵</span>
            <span>Inspect 3D Terrain</span>
          </button>
        </div>
      </div>

      {/* Sidebar Footer */}
      <div className="sidebar-rail-footer">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1">Datum:</span>
          <span className="font-semibold text-graphite">{result?.calibration?.vertical_datum || 'EGM2008 / WGS84'}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1">Telemetry:</span>
          <span className="font-bold text-pine">{job ? `${job.job_status} (${job.job_id.slice(0, 8)})` : 'Nominal (0.0ms)'}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1">Model:</span>
          <span className="font-semibold text-graphite">DA-V2-S (Offline)</span>
        </div>
      </div>
    </nav>
  )
}
