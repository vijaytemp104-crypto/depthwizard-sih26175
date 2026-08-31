function StageCard({ index, eyebrow, title, description }) {
  return (
    <article className="stage-card">
      <div className="stage-top"><span>{index}</span><span className="waiting-tag"><i />Waiting for processing</span></div>
      <div className="stage-visual" aria-hidden="true"><i /><i /><i /><span>{index}</span></div>
      <p className="micro-label">{eyebrow}</p>
      <h3>{title}</h3>
      <p>{description}</p>
    </article>
  )
}

export default StageCard
