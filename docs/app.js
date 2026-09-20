const $ = (id) => document.getElementById(id);
const STATIC_ROOT = document.documentElement.dataset.staticRoot || '/static/';
const API_ROOT = document.documentElement.dataset.apiRoot || '';
const IS_GITHUB_PAGES = location.hostname.endsWith('github.io');
const search = $('search'), results = $('results');
const normalize = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
const escapeHTML = (s) => String(s).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const storage = {get(key, fallback) {try {return localStorage.getItem(key) || fallback;} catch {return fallback;}}, set(key, value) {try {localStorage.setItem(key,value);} catch {}}};
let platform = storage.get('touchline-platform','PS');
if (!['PS','PC'].includes(platform)) platform = 'PS';
let generation = 0, timer, controller, players = [], recognition, listening = false, voiceState = "idle", voiceTimer;
const searchCache = new Map(), known = new Map(), priceCache = new Map();
const score = (p,q) => {const n = normalize(p.name), words=n.split(' '); return (n===q?5:words.at(-1)===q?4:n.startsWith(q)?3:words.some(w=>w.startsWith(q))?2:n.includes(q)?1:0)*1000+p.rating;};
function put(cache,key,value,max=150) {if(cache.size>=max) cache.delete(cache.keys().next().value);cache.set(key,value);}
async function api(url,signal) {const r=await fetch(url,{signal});if(!r.ok)throw Error('Kunde inte hämta data');return r.json();}
function message(text) {$('message').textContent=text;$('message').hidden=!text;}
function updatePlatform() {document.querySelector(".tabs").dataset.selected=platform;document.querySelectorAll('[data-platform]').forEach(b=>{const selected=b.dataset.platform===platform;b.classList.toggle('active',selected);b.setAttribute('aria-pressed',selected);});}
function priceMarkup(data) {
 if(!data) return '<div class="price-value pending">Hämtar pris…</div><div class="price-note">FUTBIN</div>';
 if(data.error)return '<div class="price-value pending">Ej tillgängligt</div><div class="price-note">Öppna på FUTBIN ↗</div>';
 if(!data.price)return '<div class="price-value pending">Pris saknas</div><div class="price-note">Öppna på FUTBIN ↗</div>';
 const age=Math.max(0,Math.floor((Date.now()/1000-data.fetchedAt)/60));
 return `<div class="price-value">${new Intl.NumberFormat('sv-SE').format(data.price)}<img class="coin-icon" src="${STATIC_ROOT}fc-coins.png" alt="FC Coins"></div><div class="price-note">Hämtat ${age<1?'nyss':`för ${age} min sedan`}</div>`;
}
function versionLabel(version) {
 const name = String(version || '').trim();
 const base = name.toLowerCase() === 'normal';
 return {name: base ? 'Baskort' : name || 'Okänd version', special: Boolean(name) && !base};
}
function versionMarkup(version) {
 const label = versionLabel(version);
 return `<span class="version${label.special ? ' version-special' : ''}" aria-label="Kortversion: ${escapeHTML(label.name)}">${escapeHTML(label.name)}</span>`;
}
function render(list) {
 players=list;$('empty').hidden=!!search.value.trim();
 results.innerHTML=list.map(p=>`<a class="player" href="${escapeHTML(p.url)}" target="_blank" rel="noopener noreferrer" aria-label="${escapeHTML(`${p.name}, ${p.rating}, ${versionLabel(p.version).name}, ${p.club}. Öppna på FUTBIN`)}"><img class="portrait" ${p.image?`src="${escapeHTML(p.image)}"`:''} alt="" width="58" height="58"><div><div class="player-name">${escapeHTML(p.name)}</div><div class="player-meta"><span>${escapeHTML(p.position)}</span>${versionMarkup(p.version)}</div></div><div class="club"><img ${p.clubImage?`src="${escapeHTML(p.clubImage)}"`:''} alt="" width="25" height="25"><span>${escapeHTML(p.club)}</span></div><span class="rating ${p.rating<65?'bronze':p.rating<75?'silver':''}">${p.rating||'?'}</span><div class="price" id="price-${p.id}">${priceMarkup(priceCache.get(`${platform}:${p.id}`))}</div></a>`).join('');
 results.querySelectorAll('img').forEach(img=>{img.onerror=()=>{img.style.visibility='hidden';};});
 $('result-count').textContent=list.length?`${list.length} ${list.length===1?'kort':'kort'} · FC 27`:'FC 27 · Ultimate Team';
}
async function loadPrices(list,version) {
 const market=platform;let cursor=0;
 async function worker() {
  while(cursor<list.length && version===generation) {
   const p=list[cursor++],key=`${market}:${p.id}`;
   let data=priceCache.get(key);
   if(!data || Date.now()/1000-data.fetchedAt>=120) {
    try {data=await api(`${API_ROOT}/api/prices/${p.id}?platform=${market}`,controller.signal);put(priceCache,key,data,500);}
    catch(e) {if(e.name==='AbortError')return;data={error:true};}
   }
   if(version===generation && market===platform){const el=$(`price-${p.id}`);if(el)el.innerHTML=priceMarkup(data);}
  }
 }
 await Promise.all(Array.from({length:5},worker));
}
function startQuery(immediate=false) {
 clearTimeout(timer);controller?.abort();controller=new AbortController();const version=++generation;
 const q=search.value.trim(), normalized=normalize(q);
 $('clear').hidden=!q;$('retry').hidden=true;message('');results.setAttribute('aria-busy','false');
 $('results-title').textContent=q?`Resultat för ”${q}”`:'Börja med ett namn';
 if(q.length<2){render([]);if(q)message('Skriv minst två bokstäver för att söka.');$('hint').textContent='Sök på förnamn, efternamn eller hela namnet.';return;}
 const cached=searchCache.get(normalized);
 if(cached && Date.now()-cached.time<120000){render(cached.players);$('hint').textContent='Bästa namnträffen först.';if(!cached.players.length)message('Inga spelare hittades. Prova efternamnet eller en annan stavning.');loadPrices(cached.players,version);return;}
 const instant=[...known.values()].filter(p=>normalize(p.name).includes(normalized)).sort((a,b)=>score(b,normalized)-score(a,normalized));
 render(instant);$('hint').textContent='Söker i FC27…';results.setAttribute('aria-busy','true');
 timer=setTimeout(async()=>{
  try {
   const data=await api(`${API_ROOT}/api/search?q=${encodeURIComponent(q)}`,controller.signal);
   if(version!==generation)return;
   put(searchCache,normalized,{players:data.players,time:Date.now()});data.players.forEach(p=>put(known,p.id,p,1000));render(data.players);
   if(!data.players.length)message('Inga spelare hittades. Prova efternamnet eller en annan stavning.');
   $('hint').textContent='Bästa namnträffen först.';loadPrices(data.players,version);
  } catch(e) {if(version!==generation || e.name==='AbortError')return;message(IS_GITHUB_PAGES ? 'GitHub Pages visar gränssnittet, men prisservern körs inte där ännu. Kör appen lokalt för livepriser.' : 'FUTBIN svarar inte just nu. Försök igen om en stund.');$('retry').hidden=false;$('hint').textContent='Sökningen kunde inte slutföras.';}
  finally {if(version===generation)results.setAttribute('aria-busy','false');}
 },immediate?0:160);
}
search.addEventListener('input',()=>startQuery());
$('clear').onclick=()=>{search.value='';startQuery();search.focus();};
$('retry').onclick=()=>startQuery(true);
document.querySelectorAll('[data-query]').forEach(b=>b.onclick=()=>{search.value=b.dataset.query;startQuery(true);search.focus();});
document.querySelectorAll('[data-platform]').forEach(b=>b.onclick=()=>{platform=b.dataset.platform;storage.set('touchline-platform',platform);updatePlatform();startQuery(true);});
$('close-help').onclick=()=>$('help-dialog').close();
$('voice-language').value=storage.get('touchline-language','sv-SE');
$('voice-language').onchange=()=>storage.set('touchline-language',$('voice-language').value);
function voiceStatus(text, state = 'idle') {
 const el = $('voice-status');
 el.textContent = text;
 el.hidden = !text;
 el.dataset.state = state;
}
function setVoiceState(state) {
 voiceState = state;
 listening = state === 'starting' || state === 'listening';
 $('voice').classList.toggle('listening', listening);
 $('voice').setAttribute('aria-label', listening ? 'Stoppa röstsökning' : 'Starta röstsökning');
 $('voice').setAttribute('aria-pressed', String(listening));
}
function voice() {
 if (listening) {
  clearTimeout(voiceTimer);
  recognition.abort();
  setVoiceState('idle');
  voiceStatus('');
  return;
 }
 if (!window.isSecureContext) {
  voiceStatus('Mikrofonen kräver HTTPS eller localhost. Öppna sidan via en säker adress.', 'error');
  return;
 }
 const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
 if (!Recognition) {
  voiceStatus('Den här webbläsaren saknar taligenkänning. Öppna sidan i Google Chrome eller Safari.', 'error');
  return;
 }
 const session = new Recognition();
 recognition = session;
 session.lang = $('voice-language').value;
 session.interimResults = true;
 session.maxAlternatives = 3;
 let receivedSpeech = false, failed = false;
 setVoiceState('starting');
 voiceStatus('Startar mikrofonen…');
 session.onstart = () => {
  if (recognition !== session || voiceState === 'idle') return;
  clearTimeout(voiceTimer);
  setVoiceState('listening');
  voiceStatus('Lyssnar…');
 };
 session.onresult = (event) => {
  if (recognition !== session || !listening) return;
  const transcript = Array.from(event.results).map(result => result[0].transcript).join(' ').replace(/[.!?]+$/, '').trim();
  if (!transcript) return;
  receivedSpeech = true;
  search.value = transcript;
  startQuery(event.results[event.results.length - 1].isFinal);
 };
 session.onerror = (event) => {
  if (recognition !== session) return;
  clearTimeout(voiceTimer);
  if (event.error === 'aborted') {setVoiceState('idle');return;}
  failed = true;
  setVoiceState('idle');
  const errors = {
   'not-allowed': 'Mikrofonåtkomst nekades. Tillåt mikrofonen för sidan i webbläsaren och i datorns integritetsinställningar.',
   'service-not-allowed': 'Webbläsaren tillåter inte sin taltjänst här. Prova sidan i Google Chrome eller Safari.',
   'no-speech': 'Inget tal hördes. Tryck på mikrofonen och försök igen.',
   'audio-capture': 'Ingen tillgänglig mikrofon hittades. Kontrollera vald mikrofon i webbläsaren.',
   'network': 'Webbläsarens taltjänst är inte tillgänglig (network). Helium kan sakna tjänsten även när internet fungerar. Prova Google Chrome eller Safari.',
   'language-not-supported': 'Taltjänsten stöder inte valt språk. Tryck ? och välj ett annat röstspråk.'
  };
  voiceStatus(errors[event.error] || `Taligenkänningen misslyckades (${event.error}). Prova igen.`, 'error');
 };
 session.onend = () => {
  if (recognition !== session) return;
  clearTimeout(voiceTimer);
  const wasActive = listening;
  setVoiceState('idle');
  if (!failed) voiceStatus(receivedSpeech || !wasActive ? '' : 'Inget tal registrerades. Tryck på mikrofonen för att försöka igen.');
 };
 try {
  session.start();
  voiceTimer = setTimeout(() => {
   if (recognition !== session || voiceState !== 'starting') return;
   failed = true;
   session.abort();
   setVoiceState('idle');
   voiceStatus('Mikrofonen startade inte. Kontrollera webbläsarens tillståndsfråga eller prova Google Chrome.', 'error');
  }, 15000);
 } catch (error) {
  setVoiceState('idle');
  voiceStatus(`Mikrofonen kunde inte startas (${error.name}). Prova igen.`, 'error');
 }
}
$('voice').onclick = voice;
$('voice-tip-button').onclick = voice;
if (/Mac|iPhone|iPad/.test(navigator.platform)) $('alt-key').textContent = '⌥';
document.addEventListener('keydown',(e)=>{
 if(e.repeat)return;
 if(e.altKey && e.code==='KeyV'){e.preventDefault();voice();return;}
 if($('help-dialog').open)return;
 const editing=['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)||document.activeElement.isContentEditable;
 if(e.key==='/'&&!editing){e.preventDefault();search.focus();}
 if(e.key==='?'&&!editing){e.preventDefault();$('help-dialog').showModal();}
 if(e.key==='Escape'){if(listening)voice();else{search.value='';startQuery();search.focus();}}
});
updatePlatform();
