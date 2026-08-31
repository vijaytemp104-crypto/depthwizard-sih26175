import React from 'react'

function WorkflowStepper({ stages, stageStates }) {
  const keys = ['ingest', 'depth', 'calibration', 'validation', 'terrain', 'evidence']
  return (
    <nav className="workflow" aria-label="DepthWizard workflow">
      <div className="workflow-track" aria-hidden="true" />
      {stages.map((stage, index) => {
        const backendState = stageStates[keys[index]] || 'waiting'
        const state = backendState === 'running' || (index === 0 && backendState === 'waiting') ? 'active' : backendState
        return (
          <div className={`workflow-step ${state}`} key={stage.name} aria-current={state === 'active' ? 'step' : undefined}>
            <span className="step-node">{String(index + 1).padStart(2, '0')}</span>
            <span className="step-copy"><strong>{stage.name}</strong><small>{state === 'active' ? 'Active' : state === 'waiting' || state === 'pending' ? 'Waiting' : state} · {stage.detail}</small></span>
          </div>
        )
      })}
    </nav>
  )
}

export default WorkflowStepper
