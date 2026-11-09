/* Gestion du thème clair/sombre : localStorage + attribut <html data-theme>.
   Trois états : null (suit le système), "clair", "sombre". */
const CLE = 'lulucode-theme'

export function litTheme() {
  try {
    return localStorage.getItem(CLE) // 'clair' | 'sombre' | null (auto)
  } catch {
    return null
  }
}

export function appliqueTheme(valeur) {
  const racine = document.documentElement
  if (valeur) racine.setAttribute('data-theme', valeur)
  else racine.removeAttribute('data-theme')
}

export function enregistreTheme(valeur) {
  try {
    if (valeur) localStorage.setItem(CLE, valeur)
    else localStorage.removeItem(CLE)
  } catch {
    /* stockage indisponible : le thème reste pour la session seulement */
  }
  appliqueTheme(valeur)
}
