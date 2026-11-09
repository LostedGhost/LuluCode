import { useEffect, useRef, useState } from 'react'
import Sidebar from './composants/Sidebar.jsx'
import BarreHaut from './composants/BarreHaut.jsx'
import MessageAgent from './composants/MessageAgent.jsx'
import MessageUtilisateur from './composants/MessageUtilisateur.jsx'
import LigneOutil from './composants/LigneOutil.jsx'
import CartePermission from './composants/CartePermission.jsx'
import ZoneSaisie from './composants/ZoneSaisie.jsx'
import CartesAccueil from './composants/CartesAccueil.jsx'
import AccueilOrbe from './composants/AccueilOrbe.jsx'
import { appliqueTheme, litTheme } from './theme.js'

const MOTS_SORTIE = /^(exit|quit|quitter)$/i

export default function App() {
  const [blocs, setBlocs] = useState([])   // journal : {type, ...charge}
  const [enCours, setEnCours] = useState(false)
  const [etat, setEtat] = useState('connexion…')
  const [info, setInfo] = useState({ profil: '—', mode: '', version: '' })
  const [conversationTitre, setConversationTitre] = useState('Nouvelle conversation')
  const [sidebarOuverte, setSidebarOuverte] = useState(false)
  const [theme, setTheme] = useState(litTheme())
  const finRef = useRef(null)

  useEffect(() => appliqueTheme(litTheme()), [])

  function defileFin() {
    requestAnimationFrame(() => {
      finRef.current?.scrollIntoView({ block: 'end' })
    })
  }

  // --- flux SSE : les événements du cœur alimentent le journal ----------
  useEffect(() => {
    const source = new EventSource('/evenements')
    source.onmessage = (e) => {
      let ev
      try { ev = JSON.parse(e.data) } catch { return }
      const d = ev.donnees || {}
      switch (ev.type) {
        case 'connecte':
          setEtat('prêt')
          fetch('/historique').then((r) => r.json()).then((h) => {
            if (h.profil) setInfo({ profil: h.profil, mode: h.mode, version: h.version })
            if (h.titre) setConversationTitre(h.titre)
            const replays = h.historique.map((x) =>
              x.role === 'utilisateur'
                ? { type: 'utilisateur', texte: x.texte }
                : { type: 'agent', texte: x.texte })
            if (replays.length) setBlocs(replays)
          }).catch(() => {})
          break
        case 'tache_demarree':
          setConversationTitre((d.tache || '').slice(0, 60) || conversationTitre)
          break
        case 'texte':
          if (!d.deja_affiche && d.texte) setBlocs((b) => [...b, { type: 'agent', texte: d.texte }])
          break
        case 'outil_appel': {
          const a = d.arguments || {}
          const cible = a.chemin || a.commande || a.motif
            || Object.values(a).map(String).join(', ')
          setBlocs((b) => [...b, { type: 'outil', nom: d.outil, cible, niveau: d.niveau ?? 1 }])
          break
        }
        case 'diff':
          setBlocs((b) => [...b, { type: 'diff', chemin: d.chemin, diff: d.diff }])
          break
        case 'permission_demandee':
          setBlocs((b) => [...b, {
            type: 'permission', id: d.id, outil: d.outil,
            niveau: d.niveau, detail: d.detail || '', raison: d.raison || '',
          }])
          break
        case 'erreur':
          setBlocs((b) => [...b, { type: 'erreur', message: d.message || '' }])
          break
        case 'plafond':
          setBlocs((b) => [...b, { type: 'plafond', raison: d.raison || '' }])
          break
        case 'tache_terminee':
          setEnCours(false)
          setEtat('prêt')
          break
        default:
          break
      }
    }
    source.onerror = () => {
      setEtat('connexion perdue…')
      setTimeout(() => location.reload(), 2500)
    }
    return () => source.close()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(defileFin, [blocs, enCours])

  // --- actions -----------------------------------------------------------

  async function envoyer(tache) {
    const texte = tache.trim()
    if (!texte || enCours) return
    if (MOTS_SORTIE.test(texte)) {
      setBlocs((b) => [...b, {
        type: 'agent',
        texte: 'Session page terminée. Le serveur reste actif — Ctrl+C dans le terminal pour l’arrêter.',
      }])
      return
    }
    setBlocs((b) => [...b, { type: 'utilisateur', texte }])
    setEnCours(true)
    setEtat('agent en action…')
    try {
      const reponse = await fetch('/tache', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tache: texte }),
      })
      if (!reponse.ok) {
        const err = await reponse.json().catch(() => ({ detail: 'échec' }))
        setBlocs((b) => [...b, { type: 'erreur', message: err.detail || 'échec' }])
        setEnCours(false)
        setEtat('prêt')
      }
    } catch {
      setBlocs((b) => [...b, { type: 'erreur', message: 'serveur injoignable' }])
      setEnCours(false)
      setEtat('prêt')
    }
  }

  async function repondPermission(id, accepte) {
    setBlocs((b) => b.map((x) => (x.type === 'permission' && x.id === id
      ? { ...x, traite: accepte ? 'accordée' : 'refusée' }
      : x)))
    try {
      await fetch('/permission', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifiant: id, accepte }),
      })
    } catch {
      /* le serveurcoupera à la déconnexion ; sans action de plus */
    }
  }

  function changeTheme(cible) {
    setTheme(cible)
    import('./theme.js').then((m) => m.enregistreTheme(cible))
  }

  const vide = blocs.length === 0

  return (
    <div className="app">
      <Sidebar
        ouverte={sidebarOuverte}
        ferme={() => setSidebarOuverte(false)}
        titre={conversationTitre}
        info={info}
        theme={theme}
        changeTheme={changeTheme}
      />
      {sidebarOuverte && (
        <div className="fond-sidebar" onClick={() => setSidebarOuverte(false)} />
      )}
      <div className="main">
        <BarreHaut
          ouvreSidebar={() => setSidebarOuverte(true)}
          etat={etat}
          profil={info.profil}
        />
        <div className="conteneur-conversation">
          {vide ? (
            <div className="conversation">
              <AccueilOrbe />
              <CartesAccueil surChoix={envoyer} />
            </div>
          ) : (
            <div className="conversation">
              {blocs.map((bloc, i) => {
                switch (bloc.type) {
                  case 'utilisateur': return <MessageUtilisateur key={i} texte={blockText(bloc)} />
                  case 'agent': return <MessageAgent key={i} texte={blockText(bloc)} />
                  case 'outil': return <LigneOutil key={i} nom={bloc.nom} cible={bloc.cible} niveau={bloc.niveau} />
                  case 'diff': return <Diff key={i} chemin={bloc.chemin} diff={bloc.diff} />
                  case 'permission':
                    return <CartePermission key={i} {...bloc} surReponse={repondPermission} />
                  case 'erreur': return <LigneErreur key={i} message={bloc.message} />
                  case 'plafond': return <LignePlafond key={i} raison={bloc.raison} />
                  default: return null
                }
              })}
              {enCours && (
                <div className="bloc agent">
                  <span className="etiquette">LuluCode</span>
                  <span className="attente"><i /><i /><i /></span>
                </div>
              )}
              <div ref={finRef} />
            </div>
          )}
        </div>
        <ZoneSaisie surEnvoi={envoyer} desactive={enCours} />
      </div>
    </div>
  )
}

function blockText(bloc) {
  return typeof bloc.texte === 'string' ? bloc.texte : ''
}

function Diff({ chemin, diff }) {
  const lignes = String(diff || '').split('\n')
  return (
    <div className="bloc">
      <div className="diff-ca">
        <strong>{chemin}</strong>
        {lignes.map((l, i) => (
          <div key={i}
               style={{ color: l.startsWith('+') ? 'var(--vert)'
                        : l.startsWith('-') ? 'var(--rouge)' : undefined }}>
            {l}
          </div>
        ))}
      </div>
    </div>
  )
}

function LigneErreur({ message }) {
  return (
    <div className="bloc outil-ligne erreur-ligne">
      <span className="point pt-3">⏺</span>
      {message}
    </div>
  )
}

function LignePlafond({ raison }) {
  return (
    <div className="bloc outil-ligne" style={{ color: 'var(--jaune)' }}>
      plafond · {raison}
    </div>
  )
}
