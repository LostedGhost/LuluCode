export default function LigneOutil({ nom, cible, niveau }) {
  const n = Math.max(0, Math.min(3, Number(niveau) || 0))
  return (
    <div className="bloc outil-ligne">
      <span className={`point pt-${n}`}>⏺</span>
      {nom}
      {cible ? <> · {cible}</> : null}
    </div>
  )
}
