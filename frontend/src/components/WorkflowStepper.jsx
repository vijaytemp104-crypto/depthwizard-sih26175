function WorkflowStepper({ stages, activeIndex }) {
  return (
    <nav className="workflow" aria-label="DepthWizard workflow">
      <div className="workflow-track" aria-hidden="true" />
      {stages.map((stage, index) => {
        const state = index === activeIndex ? 'active' : 'waiting'
        return (
          <div className={`workflow-step ${state}`} key={stage.name} aria-current={state === 'active' ? 'step' : undefined}>
            <span className="step-node">{String(index + 1).padStart(2, '0')}</span>
            <span className="step-copy"><strong>{stage.name}</strong><small>{state === 'active' ? 'Active · ' : ''}{stage.detail}</small></span>
          </div>
        )
      })}
    </nav>
  )
}

export default WorkflowStepper
