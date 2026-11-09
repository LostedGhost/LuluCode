export default function CartePermission({ id, outil, niveau, detail, raison, traite, surReponse }) {
  if (traite) {
    return (
      <div className="bloc outil-ligne" style={{ color: traite === 'accordée' ? 'var(--vert)' : 'var(--rouge)' }}>
        <span className="point pt-0">⏺</span>
        permission {traite} — {outil}
      </div>
    )
  }
  return (
    <div className="bloc carte-perm">
      <div className="titre-perm">
        Autoriser {outil} (niveau {niveau}) ?
      </div>
      {raison ? <div style={{ fontSize: 'var(--taille-sm)', color: 'var(--gris)' }}>{raison}</div> : null}
      <div className="detail-perm">{detail}</div>
      <div className="boutons-perm">
        <button className="oui" onClick={() => surReponse(id, true)}>[o] une fois</button>
        <button className="oui-s" onClick={() => surReponse(id, true)}>[s] session</button>
        <button className="non" onClick={() => surReponse(id, false)}>[n] refuser</button>
      </div>
    </div>
  )
}
