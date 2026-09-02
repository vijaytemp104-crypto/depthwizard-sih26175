import React from 'react'

function Header({ onOpenWorkspace }) {
  return (
    <header className="topbar">
      <a className="brand" href="#top" aria-label="ChakraVIEW home">
        <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
        <span><strong>ChakraVIEW</strong><small>AI-POWERED 3D TERRAIN INTELLIGENCE</small></span>
      </a>
      <div className="header-context"><span>SMART INDIA HACKATHON 2026</span><b>SIH26175</b></div>
      <div className="header-actions">
        <div className="system-state"><span className="status-dot" />SYSTEM IDLE</div>
        <button className="outline-button" type="button" onClick={onOpenWorkspace}>Open workspace</button>
      </div>
    </header>
  )
}

export default Header
