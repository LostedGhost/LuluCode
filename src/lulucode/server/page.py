"""Page de l'interface web de LuluCode (HTML/CSS/JS, aucun build).

Structure inspirée des assistants modernes (accueil centré, cartes
d'actions, conversation en colonne unique), habillée à la palette
LuluCode (GitHub dark + cyan/violet de la marque).
"""

PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LuluCode</title>
<style>
  :root {
    --fond:#0d1117; --panneau:#161b22; --panneau2:#1b2230;
    --bordure:#30363d; --texte:#e6edf3; --gris:#8b949e;
    --cyan:#22d3ee; --violet:#a78bfa; --vert:#3fb950;
    --bleu:#58a6ff; --jaune:#d29922; --rouge:#f85149;
    --degrade:linear-gradient(90deg,#22d3ee,#a78bfa);
  }
  * { box-sizing:border-box; }
  html, body { height:100%; }
  body { margin:0; background:var(--fond); color:var(--texte);
         font:15px/1.5 'Segoe UI', Roboto, sans-serif;
         display:flex; height:100vh; overflow:hidden; }

  /* --- barre latérale --- */
  aside { width:250px; min-width:250px; background:var(--panneau);
          border-right:1px solid var(--bordure); display:flex;
          flex-direction:column; }
  .logo-bloc { display:flex; align-items:center; gap:10px;
               padding:16px 16px 12px; }
  .logo-marque { width:34px; height:34px; border-radius:10px;
                 background:var(--degrade); display:flex;
                 align-items:center; justify-content:center;
                 font:700 15px monospace; color:#0d1117; }
  .nom { font-weight:800; font-size:16px; color:var(--texte); }
  .slogan { font-size:10.5px; color:var(--gris); display:block; margin-top:1px; }
  .nouvelle-action { margin:4px 12px 10px; padding:10px 12px;
                     background:var(--degrade); border:0; border-radius:10px;
                     color:#0d1117; font-weight:700; cursor:pointer;
                     font-size:14px; width:calc(100% - 24px); }
  .section-titre { color:var(--gris); font-size:11.5px; text-transform:uppercase;
                   letter-spacing:.08em; padding:14px 18px 6px; }
  ul.conversations { list-style:none; margin:0; padding:0 8px; flex:1;
                     overflow-y:auto; }
  ul.conversations li { padding:8px 10px; border-radius:8px; cursor:pointer;
                        font-size:13.5px; color:var(--texte);
                        white-space:nowrap; overflow:hidden;
                        text-overflow:ellipsis; }
  ul.conversations li:hover { background:rgba(255,255,255,.04); }
  ul.conversations li.actif { background:rgba(34,211,238,.10);
                              color:var(--cyan); }
  .pied-sidebar { border-top:1px solid var(--bordure); padding:12px 16px;
                  font-size:12.5px; color:var(--gris); }
  .pied-meta strong { color:var(--texte); }

  /* --- zone principale --- */
  main { flex:1; display:flex; flex-direction:column; min-width:0; }
  .barre-haut { display:flex; align-items:center; justify-content:space-between;
                padding:10px 18px; border-bottom:1px solid var(--bordure);
                background:rgba(22,27,34,.6); backdrop-filter:blur(6px); }
  .puce-modele { display:inline-flex; align-items:center; gap:7px;
                 background:var(--panneau); border:1px solid var(--bordure);
                 border-radius:999px; padding:5px 12px; font-size:12.5px;
                 color:var(--texte); }
  .puce-modele .pointvert { width:7px; height:7px; border-radius:50%;
                            background:var(--vert); display:inline-block; }
  #etat { color:var(--gris); font-size:13px; }

  main .interieur { flex:1; overflow-y:auto; display:flex;
                    flex-direction:column; }
  #journal { max-width:820px; width:100%; margin:0 auto; padding:22px 20px 30px; }

  /* --- accueil (avant premier message) --- */
  .accueil { text-align:center; padding:8vh 16px 12px; }
  .salut { font-size:34px; font-weight:800; margin:18px 0 4px; }
  .salut .accent { background:var(--degrade);
                   -webkit-background-clip:text; background-clip:text;
                   color:transparent; }
  .question { color:var(--gris); margin-bottom:6px; }
  .question { color:var(--texte); font-size:17px; font-weight:600;
              margin-bottom:8px; }
  .sous-texte { color:var(--gris); font-size:13.5px; max-width:520px;
                margin:0 auto 22px; }
  .orbe { width:88px; height:88px; margin:26px auto 4px; border-radius:50%;
          background:radial-gradient(circle at 32% 28%, #67e8f9 0%,
                     var(--cyan) 26%, var(--violet) 62%, #312e81 85%);
          box-shadow:0 0 60px rgba(34,211,238,.35),
                     0 0 120px rgba(167,139,250,.25); }

  /* --- journal --- */
  .bloc { margin-bottom:16px; line-height:1.6; white-space:pre-wrap; }
  .utilisateur .bulle { background:var(--panneau);
                        border:1px solid var(--bordure);
                        border-radius:14px 14px 14px 4px; padding:10px 14px;
                        display:inline-block; max-width:85%; }
  .chevron { color:var(--cyan); font-weight:700; margin-right:8px; }
  .agent { color:var(--texte); }
  .agent pre { background:var(--panneau); border:1px solid var(--bordure);
               border-radius:10px; padding:12px; overflow-x:auto;
               font:13px Consolas,monospace; }
  .agent code.enligne { background:var(--panneau); border-radius:5px;
                        padding:1px 6px; font-family:Consolas,monospace;
                        font-size:13px; color:var(--cyan); }
  .outil { color:var(--gris); font-size:13.5px; margin:10px 0; }
  .pt { margin-right:8px; }
  .pt-0 { color:var(--vert); } .pt-1 { color:var(--jaune); }
  .pt-2 { color:var(--jaune); } .pt-3 { color:var(--rouge); }
  .erreur { color:var(--rouge); }
  .diff { background:var(--panneau); border:1px solid var(--bordure);
          border-radius:10px; padding:10px 14px;
          font:12.5px/1.5 Consolas, monospace; overflow-x:auto; }
  .plus { color:var(--vert); } .moins { color:var(--rouge); }
  .perm { border:1px solid var(--jaune); background:rgba(210,153,34,.06);
          border-radius:12px; padding:13px 16px; margin:12px 0; }
  .perm .titre { font-weight:700; color:var(--jaune); margin-bottom:5px; }
  .perm .detail { font:12.5px Consolas, monospace; color:var(--gris);
                  margin-bottom:10px; word-break:break-all; }
  .perm button { cursor:pointer; border-radius:8px; padding:6px 15px;
                 font-size:13px; margin-right:8px; background:transparent;
                 border:1px solid var(--bordure); color:var(--texte);
                 transition:opacity .15s; }
  .perm button:hover { opacity:.8; }
  .perm .oui { border-color:var(--vert); color:var(--vert); }
  .perm .oui-s { border-color:var(--bleu); color:var(--bleu); }
  .perm .non { border-color:var(--rouge); color:var(--rouge); }

  /* --- zone de saisie --- */
  .zone-saisie { max-width:820px; margin:0 auto; width:100%;
                 padding:0 20px 18px; }
  .cadre-saisie { background:var(--panneau); border:1px solid var(--bordure);
                  border-radius:16px; padding:12px 14px 10px;
                  transition:border-color .2s; }
  .cadre-saisie:focus-within { border-color:var(--cyan); }
  .cadre-saisie textarea { width:100%; background:transparent;
                           border:0; resize:none; color:var(--texte);
                           font:15px/1.5 inherit; height:46px;
                           outline:none; }
  .outil-barre { display:flex; align-items:center; gap:10px; }
  .outil-barre .plus { width:32px; height:32px; border-radius:50%;
                       border:1px solid var(--bordure); color:var(--gris);
                       background:transparent; cursor:pointer; font-size:17px; }
  .outil-barre .astuce { color:var(--gris); font-size:12px; flex:1; }
  #bouton-envoi { width:36px; height:36px; border-radius:50%; border:0;
                  background:var(--degrade); color:#0d1117;
                  font-size:16px; font-weight:800; cursor:pointer; }
  #bouton-envoi:disabled { opacity:.4; cursor:default; }

  /* --- cartes d'actions rapides (accueil) --- */
  .cartes { display:grid; grid-template-columns:1fr 1fr; gap:12px;
            max-width:820px; margin:26px auto 0; padding:0 20px; }
  .carte { text-align:left; background:var(--panneau);
           border:1px solid var(--bordure); border-radius:14px;
           padding:14px 16px; cursor:pointer; color:var(--texte);
           transition:border-color .15s, transform .15s; }
  .carte:hover { border-color:var(--cyan); transform:translateY(-1px); }
  .carte .icone { width:30px; height:30px; border-radius:9px;
                  display:inline-flex; align-items:center;
                  justify-content:center; margin-right:10px;
                  background:rgba(34,211,238,.12); color:var(--cyan);
                  font-size:15px; vertical-align:middle; }
  .carte b { font-size:14px; display:block; margin-bottom:2px; }
  .carte small { color:var(--gris); line-height:1.4; display:block;
                 margin-top:3px; }
</style>
</head>
<body>
<aside>
  <div class="logo-marque" style="display:flex;align-items:center;gap:10px;padding:16px 16px 10px;">
    <div class="logo-marque" style="width:34px;height:34px;border-radius:10px;background:var(--degrade);display:flex;align-items:center;justify-content:center;font:800 13px monospace;color:#0d1117;">&gt;_</div>
    <div><div class="nom">LuluCode</div>
         <div class="slogan" style="font-size:10.5px;color:var(--gris)">Lis · Propose · Vérifie</div></div>
  </div>
  <button class="nouvelle-action" id="bouton-nouvelle">+ Nouvelle tâche</button>
  <div class="section-titre" style="color:var(--gris);font-size:11px;letter-spacing:.08em;padding:14px 16px 6px;text-transform:uppercase;">Conversation</div>
  <ul class="conversations"><li class="actuelle"><span id="titre-conversation">Nouvelle conversation</span></li></ul>
  <div class="pied-meta">
    <div><b>profil</b> <span id="meta-profil">—</span></div>
    <div><b>mode</b> <span id="mode"> — </span></div>
    <div><b>version</b> <span id="version">—</span></div>
  </div>
</aside>

<main>
  <div class="barre-haut">
    <span class="puce-modele"><span class="pointvert"></span>LuluCode
      <span id="modele-nom" style="color:var(--gris);font-size:12.5px"></span></span>
    <span id="etat" class="etat">connexion…</span>
  </div>

  <div class="interieur" id="conteneur-journal">
    <div id="accueil" style="text-align:center; padding-top:8vh;">
      <div class="orbe"><div class="orbe" style="width:76px;height:76px;border-radius:50%;
           background:radial-gradient(circle at 34% 30%, #a5f3fc, var(--cyan) 40%, var(--violet) 70%, #312e81);
           box-shadow:0 0 60px rgba(34,211,238,.35), 0 0 110px rgba(167,139,250,.22);
           margin:0 auto 18px;"></div></div>
      <div class="salut accent" style="font-size:30px;font-weight:800;">Hello <span class="nom-accent" style="background:var(--degrade);-webkit-background-clip:text;background-clip:text;color:transparent;">vous</span></div>
      <div class="question" style="color:var(--texte);font-size:17px;font-weight:600;margin:10px 0 6px;">Que pouvons-nous créer aujourd'hui ?</div>
      <div class="sous-texte" style="color:var(--gris);">Explorez du code, générez des fichiers, lancez des tests, discutez d'architecture — en français, avec vos fichiers.</div>
    </div>
    <div id="journal"></div>
  </div>

  <div class="zone-saisie" style="max-width:860px;margin:0 auto;width:100%;padding:0 20px 8px;">
    <form class="envoi" id="formulaire" style="background:var(--panneau);
          border:1px solid var(--bordure);border-radius:16px;
          display:flex;align-items:flex-end;gap:10px;padding:12px 14px;margin:0;">
      <input id="saisie" placeholder="Demandez une tâche : « Lis le README, résume-le »"
             autocomplete="off" style="background:transparent;border:0;color:var(--texte);
             font:15px/1.4 inherit;flex:1;letter-spacing:.2px;height:36px;outline:none;">
      <button id="bouton-envoi" type="submit">➤</button>
    </form>
    <div class="cartes" id="cartes">
      <button class="carte" data-rempli="Analyse la structure du projet et dis-moi ce que fait chaque dossier principal.">
        <span class="ic" style="color:var(--cyan);font-weight:700;">⌕</span>
        <div><b>Explorer le projet</b><span style="color:var(--gris);font-size:12.5px;display:block;">Structure, conventions, entrées du code</span></div>
      </button>
      <button class="carte" data-rempli="Propose un plan de tests pour ce projet.">
        <span class="ic" style="color:var(--vert);">✓</span>
        <div><b>Analyser &amp; tester</b>
        <span style="color:var(--gris);font-size:12.5px;display:block;">Plan de tests, exécution, résultats vérifiés</span></div>
      </button>
      <button class="carte" data-rempli="Corrige le bug que je décris ensuite : ">
        <span class="ic" style="color:var(--violet);">✎</span>
        <div><b>Corriger &amp; écrire</b>
        <span style="color:var(--gris);font-size:12.5px;display:block;">Diff proposé avant toute modification</span></div>
      </button>
      <button class="carte" data-rempli="Explique-moi l'architecture globale de ce projet.">
        <span class="ic" style="color:var(--bleu);">◆</span>
        <div><b>Comprendre</b>
        <span style="color:var(--gris);font-size:12.5px;display:block;">Explications et avis argumentés</span></div>
      </button>
    </div>
  </div>

<script>
const journal = document.getElementById('journal');
const etat = document.getElementById('etat');
const champ = document.getElementById('saisie');
const bouton = document.getElementById('bouton-envoi');

function echappe(t) { const d = document.createElement('div');
                      d.textContent = t == null ? '' : String(t);
                      return d.innerHTML; }

function ajoute(html, classe) {
  const div = document.createElement('div');
  div.className = 'bloc ' + (classe || '');
  div.innerHTML = html;
  journal.appendChild(div);
  document.getElementById('journal').parentElement.scrollTop = 999999;
  div.scrollIntoView({block:'end'});
}

function carte_remplit(texte) { champ.value = texte; champ.focus(); }
document.querySelectorAll('.carte').forEach((c) => {
  c.addEventListener('click', () => {
    champ.value = c.dataset.rempli || '';
    champ.focus();
  });
});
document.getElementById('bouton-nouvelle').addEventListener('click', () => {
  location.reload();
});

// --- envoi ---
document.getElementById('formulaire').addEventListener('submit', async (e) => {
  e.preventDefault();
  const texte = champ.value.trim();
  champ.value = '';
  if (!texte) return;
  if (/^(exit|quit|quitter)$/i.test(texte)) {
    ajoute('Session page terminée. Arrêtez le serveur par Ctrl+C.', 'agent');
    return;
  }
  masque_accueil();
  ajoute('<div class="bulle-utilisateur">' + echappe(texte) + '</div>', 'utilisateur');
  bouton.disabled = true;
  etat.textContent = 'en action…';
  const reponse = await fetch('/tache', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({tache: texte})});
  if (!reponse.ok) {
    const err = await reponse.json().catch(() => ({detail:'erreur'}));
    ajoute('⛔ ' + echappe(err.detail || 'échec'), 'erreur');
    bouton.disabled = false; etat.textContent = 'prêt';
  }
});

function masque_accueil() {
  const accueil = document.getElementById('accueil');
  if (accueil) accueil.style.display = 'none';
  const cartes = document.querySelector('.cartes');
  if (cartes) cartes.remove();
}
function montre_accueil_si_vide() {
  if (!journal.children.length) {
    const a = document.getElementById('accueil');
    if (a) a.style.display = '';
  }
}

// Markdown minimal : titres, gras, code inline, blocs de code, listes
function rendu_md(t) {
  let s = echappe(t);
  s = s.replace(/```(\\w*)\\n([\\s\\S]*?)```/g,
    (m, lang, code) => '<pre><code>' + code + '</code></pre>');
  s = s.replace(/`([^`\\n]+)`/g, '<code class="enligne">$1</code>');
  s = s.replace(/^### (.*)$/gm, '<b>$1</b>');
  s = s.replace(/\\*\\*([^*]+)\\*\\*/g, '<b>$1</b>');
  s = s.replace(/^[-*] (.*)$/gm, '• $1');
  s = s.replace(/\\|(.+)\\|/g, (m) => '<code class="tbl">' + m + '</code>');
  return s;
}

// --- flux SSE ---
const source = new EventSource('/evenements');
source.onmessage = (e) => {
  let ev; try { ev = JSON.parse(e.data); } catch { return; }
  const d = ev.donnees || {};
  switch (ev.type) {
    case 'connecte':
      etat.textContent = 'prêt';
      fetch('/historique').then(r => r.json()).then((h) => {
        document.getElementById('titre-conversation').textContent
          = d.titre;
        h.historique.forEach((entree) => {
          if (entree.role === 'utilisateur')
            ajoute('<span class="chevron">&gt;</span> ' + echappe(entree.texte), 'utilisateur');
          else
            ajoute(rendu_md(entree.texte), 'agent');
        });
      });
      break;
    case 'tache_demarree':
      document.getElementById('titre-conversation').textContent
        = (d.tache || '').slice(0, 50);
      break;
    case 'texte':
      if (d.deja_affiche) break;
      ajoute(rendu_md(d.texte || ''), 'agent');
      break;
    case 'outil_appel': {
      const a = d.arguments || {};
      const cible = a.chemin || a.commande || a.motif || '';
      const n = d.niveau ?? 1;
      ajoute('<span class="pt pt-' + n + '">⏺</span>'
             + echappe(d.outil || '') + ' · ' + echappe(cible), 'outil');
      break;
    }
    case 'diff': {
      const lignes = echappe(d.diff || '').split('\\n').map((l) =>
        l.startsWith('+') ? '<span class="plus">' + l + '</span>'
        : l.startsWith('-') ? '<span class="moins">' + l + '</span>' : l
      ).join('\\n');
      ajoute('<div class="diff"><b>' + echappe(d.chemin || '') + '</b>\\n' + lignes + '</div>', 'agent');
      break;
    }
    case 'permission_demandee': {
      const bloc = document.createElement('div');
      bloc.className = 'perm';
      bloc.innerHTML =
        '<div class="titre">Autoriser ' + echappe(d.outil) + ' (niveau '
        + echappe(String(d.niveau)) + ') ?</div>'
        + '<div class="detail">' + echappe(d.detail || '') + '</div>'
        + '<button class="oui" data-i="' + d.id + '">[o] une fois</button>'
        + '<button class="oui-s" data-i="' + d.id + '">[s] session</button>'
        + '<button class="non" data-i="' + d.id + '">[n] refuser</button>';
      bloc.querySelectorAll('button').forEach((b) => {
        b.addEventListener('click', async () => {
          b.disabled = true;
          await fetch('/permission', {method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({identifiant: b.dataset.i,
                                  accepte: b.classList.contains('oui')})});
          bloc.remove();
        });
      });
      journal.appendChild(bloc);
      journal.scrollTop = journal.scrollHeight;
      break;
    }
    case 'erreur':
      ajoute('<span class="pt pt-3">⏺</span> erreur · ' + echappe(d.message || ''), 'erreur');
      break;
    case 'plafond':
      ajoute('<span class="plafond">plafond · ' + echappe(d.raison || '') + '</span>');
      break;
    case 'tache_terminee':
      etat.textContent = 'prêt';
      bouton.disabled = false;
      break;
  }
};
source.onerror = () => {
  etat.textContent = 'connexion perdue…';
  setTimeout(() => location.reload(), 2500);
};
</script>
</body>
</html>"""


def _page_session() -> str:
    return _PAGE


def _page_acces_refuse() -> str:
    return """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>LuluCode</title></head>
<body style="background:#0d1117;color:#e6edf3;font:16px sans-serif;display:flex;
             align-items:center;justify-content:center;height:100vh;margin:0">
<p style="color:#8b949e;max-width:480px;text-align:center">Aucune session active.
Lancez <code>lulucode web</code> dans un terminal, puis ouvrez
<code>http://127.0.0.1:8341/</code>.</p></body></html>"""
