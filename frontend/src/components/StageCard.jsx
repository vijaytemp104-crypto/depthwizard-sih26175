import React from 'react'

function StageCard({ index, eyebrow, title, description, status = 'waiting', label, downloads = [] }) {
  const statusText = status === 'waiting' || status === 'pending' ? 'Waiting for processing' : status
  return (
    <article className={`stage-card stage-${status}`}>
      <div className="stage-top"><span>{index}</span><span className="waiting-tag"><i />{statusText}</span></div>
      <div className="stage-visual" aria-hidden="true"><i /><i /><i /><span>{index}</span></div>
      <p className="micro-label">{eyebrow}</p>
      {label && <span className="mock-label">{label}</span>}
      <h3>{title}</h3>
      <p>{description}</p>
      {downloads.length > 0 && <div className="artifact-links">{downloads.map((item) => <a key={item.name} href={item.href}>{item.name}</a>)}</div>}
    </article>
  )
}

export default StageCard
