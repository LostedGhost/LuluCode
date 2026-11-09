export default function BarreHaut({ ouvreSidebar, etat, profil }) {
  return (
    <div className="barre-haut">
      <button className="bouton-icone burger" onClick={ouvreSidebar} aria-label="Menu">
        ☰
      </button>
      <span className="puce-modele">
        <span className="point-vert" />
        LuluCode
        {profil && profil !== '—' && <span className="detail">· {profil}</span>}
      </span>
      <span style={{ flex: 1 }} />
      <span style={{ color: 'var(--gris)', fontSize: 'var(--taille-sm)' }}>{etat}</span>
    </div>
  )
}
