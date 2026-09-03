import React from 'react'
import ChakraViewLogo from './ChakraViewLogo'

export default function Header({ job, result, onSelectTab }) {
  const isMetric = result?.calibration?.calibrated
  const isRunning = job?.job_status === 'running' || job?.job_status === 'pending'
  const isSucceeded = job?.job_status === 'succeeded'
  const isFailed = job?.job_status === 'failed'
  const crs = result?.calibration?.crs || 'EPSG:32619'
  const datum = result?.calibration?.vertical_datum || 'EGM2008'

  return (
    <header className="stitch-topbar" aria-label="ChakraVIEW Header">
      {/* Brand & Logo */}
      <div className="flex items-center gap-3">
        <ChakraViewLogo size={40} />
        <div className="flex flex-col justify-center">
          <div className="flex items-baseline gap-2">
            <span className="font-sans text-[20px] font-bold tracking-tight text-graphite leading-tight">
              Chakra<span className="text-pine">VIEW</span>
            </span>
            <span className="font-mono text-[11px] text-pine font-semibold tracking-wider uppercase hidden sm:inline">
              — From Orbit to Action
            </span>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="font-mono text-[9px] text-graphite/70 px-1.5 py-0.2 bg-alabaster rounded border border-line leading-tight font-medium">
              SIH26175
            </span>
            <span className="font-mono text-[10px] text-graphite-muted leading-tight hidden md:inline">
              AI-Powered 3D Terrain Intelligence for Disaster Management
            </span>
          </div>
        </div>

        {/* Active Session Indicator */}
        {job?.job_id && (
          <div className="hidden lg:flex items-center gap-2 pl-3 border-l border-line">
            <span className="font-mono text-[10px] px-2 py-0.5 bg-pine-subtle text-pine font-bold rounded">
              SESSION ACTIVE
            </span>
            <span className="font-mono text-[11px] text-graphite-muted">
              ID: {job.job_id.slice(0, 12)}
            </span>
          </div>
        )}
      </div>

      {/* Desktop Telemetry Cluster & Status Badges */}
      <div className="flex items-center gap-3">
        {/* System Readiness */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-alabaster/60 border border-line rounded text-graphite">
          <span className={`w-2 h-2 rounded-full ${isRunning ? 'bg-coral animate-pulse' : isFailed ? 'bg-red-500' : 'bg-pine'}`} />
          <span className="font-mono text-[10px] font-bold tracking-wider">
            {isRunning ? 'PROCESSING' : isFailed ? 'ERROR' : isSucceeded ? 'OUTPUT READY' : 'SYSTEM READY'}
          </span>
        </div>

        {/* Model Spec */}
        <div className="hidden xl:flex flex-col text-right font-mono text-[10px]">
          <span className="text-graphite-muted text-[8.5px] uppercase">MODEL ENGINE</span>
          <span className="text-graphite font-medium">Depth Anything V2-S</span>
        </div>

        {/* Projection & Datum */}
        <div className="hidden xl:flex flex-col text-right pl-3 border-l border-line font-mono text-[10px]">
          <span className="text-graphite-muted text-[8.5px] uppercase">CRS / DATUM</span>
          <span className="text-graphite font-medium">{crs} · {datum}</span>
        </div>

        {/* Pipeline State Chip */}
        <div className={`status-chip ${isMetric ? 'metric' : 'relative'}`}>
          <span className="material-symbols-outlined text-[14px]">
            {isMetric ? '✓' : '!'}
          </span>
          <span className="font-mono text-[10px] font-bold tracking-wider">
            {isMetric ? 'CALIBRATED · METRIC DSM' : 'RELATIVE DEPTH · NOT METRIC'}
          </span>
        </div>

        {/* Trailing Action Buttons */}
        <div className="flex items-center gap-2 pl-2 border-l border-line">
          <button
            type="button"
            className="primary-coral-btn text-[11px] py-1 px-2.5"
            onClick={() => onSelectTab('evidence')}
            title="Export Evidence Passport"
          >
            <span>Export Evidence</span>
          </button>
          <button
            type="button"
            className="icon-tool-btn"
            onClick={() => onSelectTab('setup')}
            title="Mission Setup & Calibration"
          >
            ⚙
          </button>
          <button
            type="button"
            className="icon-tool-btn"
            onClick={() => onSelectTab('validation')}
            title="Scientific Validation"
          >
            ℹ
          </button>
        </div>
      </div>
    </header>
  )
}
