const CARTES = [
  {
    titre: 'Explorer le projet',
    sous: 'Structure, conventions, points d’entrée',
    remplissage: 'Analyse la structure du projet et explique ce que fait chaque dossier principal.',
    icone: '⌕', variante: '',
  },
  {
    titre: 'Analyser & tester',
    sous: 'Plan de tests, exécution, résultats vérifiés',
    remplissage: 'Évalue les tests existants et propose un plan de tests adapté à ce projet.',
    icone: '✓', variante: 'vert',
  },
  {
    titre: 'Corriger & écrire',
    sous: 'Diff proposé avant toute modification',
    remplissage: '',
    icone: '✎', variante: 'violet',
  },
  {
    titre: 'Comprendre',
    sous: 'Explications et avis argumentés',
    remplissage: '',
    icone: '◆', variante: 'jaune',
  },
]

export default function CartesAccueil({ surChoix }) {
  return (
    <>
      <div style={{ textAlign: 'center', color: 'var(--gris)', fontSize: 'var(--taille-sm)', marginBottom: 'var(--e-3)' }}>
        Ou choisissez un point de départ :
      </div>
      <div className="cartes">
        {CARTES.map((c) => (
          <button
            key={c.titre}
            className="carte-action"
            onClick={() =>
              surChoix(c.remplissage || c.titre)
            }
          >
            <span className={`icone-tuile ${c.variante}`}>{c.icone}</span>
            <span>
              <b>{c.titre}</b>
              <small>{c.sous}</small>
            </span>
          </button>
        ))}
      </div>
    </>
  )
}
