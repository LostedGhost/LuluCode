# Bible de projet : LuluCode (vitrine GitHub)

> Source de vérité du projet. Chaque animation et chaque asset doit s'y conformer.

## 1. Cadre

- **Support(s)** : vitrine GitHub — README.md + 4 assets SVG animés (`banner`, `terminal`, `architecture`, `permissions`)
- **Public** : développeurs francophones, niveaux intermédiaire à confirmé, sensibles à la souveraineté des données et aux modèles locaux
- **Usage** : potentiellement commercial, mais aucun asset tiers → aucun problème de licence
- **Ton** : sobre, précis, confiant
- **Format** : 4 SVG (`banner` 1200×300, `terminal` 900×500, `architecture` 1000×660, `permissions` 1000×430)

## 2. Histoire

- **Pitch** : « Lâchez un agent de code sur votre machine sans lâcher la main. »
- **Enjeu** : le visiteur veut un agent de code qui ne trahit pas son code ni son huis-clos (pas d'exode vers le cloud).
- **Arc** (structure « problème → découverte → démonstration → invitation ») :
  1. Problème ressenti : les agents connus envoient tout chez un fournisseur.
  2. Découverte : LuluCode tourne en local, au format OpenAI, avec n'importe quel modèle.
  3. Démonstration : le système de permissions rend l'agent contrôlable — c'est la pièce centrale.
  4. Invitation : démarrage en trois commandes, contribution bienvenue.
- **Détail récurrent** : le **curseur cyan clignotant** — il apparaît dans `banner` et dans `terminal`, et incarne « l'agent à l'écoute, sous votre contrôle ». Second fil rouge : le dégradé #22d3ee → #a78bfa réservé à la marque.

## 3. Personnages

Aucun personnage figuratif. Le « personnage » implicite est **la fenêtre de terminal** : sombre, familière, toujours dans le même style.

## 4. Direction visuelle

- **Style principal** : interface sombre « GitHub dark », néons discrets, angles arrondis 8–24 px, aucun effet flashy, texte toujours lisible.
- **Palette** :
  - fond page : `#0d1117` · panneaux : `#161b22` · bordures : `#30363d`
  - texte principal : `#e6edf3` · texte secondaire : `#8b949e`
  - dégradé de marque : `#22d3ee` (cyan) → `#a78bfa` (violet)
  - statut sémantique : `#3fb950` (autorisé) · `#d29922` (attente / risque 2) · `#f85149` (danger) · `#58a6ff` (info)
- **Typographies** : titres `'Segoe UI', Roboto, Helvetica, Arial, sans-serif` · code et terminal `'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace` — **polices système uniquement** (GitHub bloque les polices distantes dans `<img>`).
- **Lumière et cadrage** : plat, frontal, aucune ombre portée marquée ; profondeur suggérée par opacités faibles (plateaux à 0.05–0.12).
- **Langage animé** :
  - entrées en cascade (stagger 100–350 ms), `cubic-bezier(0.22, 1, 0.36, 1)` ;
  - frappe « machine à écrire » pour le message utilisateur (uniquement dans `terminal`) ;
  - flux de données = tirets animés le long des connecteurs (uniquement dans `architecture`) ;
  - un seul élément en mouvement à la fois par scène ;
  - boucle infinie tolérée pour : curseur, flux de tirets, balayage de la barre de risque — jamais plus de 3 éléments en boucle par SVG.
- **Accessibilité** : `role="img"` + `<title>` + `<desc>` sur chaque SVG ; `@media (prefers-reduced-motion: reduce)` coupe toutes les animations et « dessine » l'état final à l'état statique (dégradation gracieuse : sans support CSS, tout est visible).
- **Références** : l'UI GitHub dark elle-même ; les fenêtres de terminal des docs de projets dev crédibles (Aider, OpenCode) ; charts d'architecture liminaires ( Traits fins, étiquettes courtes).
- **Interdits** : emojis ; dégradé arc-en-ciel ; police fantaisie ; texte généré par IA ; mouvement permanent agressif (scintillement, rotation,蓬 pulsation > 2 éléments) ; images/photographies tierces ; logos de marques tierces (Ollama, React…) sans mention textuelle neutre ; texte sur fond insuffisamment contrasté.

## 5. Direction sonore

Sans objet (assets SVG statiques au scroll).

## 6. Contraintes techniques

- **Formats d'export** : SVG 1.1, texte en UTF-8, animations **CSS uniquement dans `<style>`** (pas de JavaScript ni de SMIL : GitHub sert les SVG via `<img>` Sanitizés).
- **Résolutions** : celles indiquées ci-dessus, `viewBox` fixe.
- **Accessibilité** : titres/desc, contraste ≥ 4.5:1 pour le texte courant, réduction de mouvement respectée.
- **Outils disponibles** : Node v24 disponible (sans usage nécessaire) ; **pas** de clé banque d'images, **pas** de ComfyUI, **pas** de FFmpeg → source unique légitime : le code.
- **Poids** : chaque SVG < 20 Ko ; métadonnées C2PA des versions précédentes non reprises (assets réécrits).

## 7. Validation

- **Qui valide** : Ludel (mainteneur du projet).
- **Étapes** : bible → storyboard → assets → relecture visuelle locale (ouvrir les SVG dans un navigateur, puis vérifier le rendu sur GitHub après commit — GitHub proxifie via camo).
- **Critères** : lisibilité à taille naturelle sur mobile (bannière lisible à ~600 px), animations non bloquantes à la lecture, cohérence palette/tirroir sur les 4 fichiers.
