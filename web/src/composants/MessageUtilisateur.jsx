export default function MessageUtilisateur({ texte }) {
  return (
    <div className="bloc utilisateur">
      <div className="bulle">
        <span className="etiquette">Vous</span>
        {texte}
      </div>
    </div>
  )
}
