export default function Sidebar({ ouverte, ferme, titre, info, theme, changeTheme }) {
  return (
    <aside className={`sidebar ${ouverte ? 'ouverte' : ''}`} aria-label="Paramètres">
      <div className="logo-bloc">
        <div className="logo-marque">&gt;_</div>
        <div>
          <div className="nom-marque">LuluCode</div>
          <span className="slogan">Lis · Propose · Vérifie</span>
        </div>
      </div>

      <button className="bouton-nouvelle" onClick={() => location.reload()}>
        +&nbsp;&nbsp;Nouvelle tâche
      </button>

      <div className="section-titre">Conversation</div>
      <ul className="conversations">
        <li className="actif">{titre || 'Nouvelle conversation'}</li>
      </ul>

      <div className="pied-sidebar">
        <div><b>profil</b> <strong>{info.profil || '—'}</strong></div>
        {info.mode ? <div><b>mode</b> <strong>{info.mode}</strong></div> : null}
        <div><b>version</b> <strong>{info.version || '—'}</strong></div>
        <SelecteurTheme theme={theme} changeTheme={changeTheme} />
      </div>
    </aside>
  )
}

function SelecteurTheme({ theme, changeTheme }) {
  return (
    <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
      <Bouton theme="sombre" actuel={theme} changeTheme={changeTheme}>🌙 Sombre</Bouton>
      <Bouton theme="clair" actuel={theme} changeTheme={changeTheme}>☀️ Clair</Bouton>
      <Bouton theme={null} actuel={theme} changeTheme={changeTheme}>Auto</Bouton>
    </div>
  )
}

function Bouton({ theme, actuel, changeTheme, children }) {
  const actif = theme === actuel || (theme === null && actuel == null)
  return (
    <button
      onClick={() => changeTheme(theme)}
      style={{
        flex: 1, padding: '6px 8px', fontSize: 12,
        borderRadius: 8, cursor: 'pointer',
        border: `1px solid ${actif ? 'var(--cyan)' : 'var(--bordure)'}`,
        color: actif ? 'var(--cyan)' : 'var(--gris)',
        background: actif ? 'rgba(34,211,238,.08)' : 'transparent',
      }}
    >
      {children}
    </button>
  )
}
