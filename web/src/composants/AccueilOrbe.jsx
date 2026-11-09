export default function AccueilOrbe() {
  return (
    <div className="accueil">
      <div className="orbe" aria-hidden="true" />
      <h1 className="salut">
        Hello <span className="accent">vous</span>
      </h1>
      <p style={{ color: 'var(--texte)', fontWeight: 600, margin: '0 0 6px', fontSize: 'var(--taille-lg)' }}>
        Que pouvons-nous créer aujourd'hui ?
      </p>
      <p className="sous-accueil">
        Demandez une tâche, explorez du code, générez des tests ou discutez
        d&apos;architecture — avec vos fichiers, en français.
      </p>
    </div>
  )
}
