import { useRef, useState } from 'react'

export default function ZoneSaisie({ surEnvoi, desactive }) {
  const [valeur, setValeur] = useState('')
  const zoneRef = useRef(null)

  function soumettre(e) {
    e.preventDefault()
    if (!valeur.trim() || desactive) return
    surEnvoi(valeur)
    setValeur('')
  }

  // Entrée envoie, Maj+Entrée retourne à la ligne.
  function touche(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      soumettre(e)
    }
  }

  return (
    <div className="zone-saisie">
      <form className="cadre-saisie" onSubmit={soumettre}>
        <textarea
          ref={zoneRef}
          rows={1}
          value={valeur}
          placeholder="Décrivez une tâche · « lis le README et résume-le » · exit pour sortir"
          onChange={(e) => setValeur(e.target.value)}
          onKeyDown={touche}
          disabled={desactive}
          aria-label="Votre demande"
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button className="bouton-envoie bouton-envoi" type="submit" disabled={desactive} aria-label="Envoyer">
            ➤
          </button>
        </div>
      </form>
      <div style={{ height: 14 }} />
    </div>
  )
}

function surEnvoi() {}
