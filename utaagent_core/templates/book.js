(() => {
'use strict';
const body = document.body;
const songs = Array.from(document.querySelectorAll('.song'));
const levels = ['N5','N4','N3','N2','N1','ungraded'];
let currentLevel = 'all';
const storageKey = 'utaagent:vocab:' + body.dataset.bookId;
let storageAvailable = true;
const make = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};
const status = (song, text) => { song.querySelector('.editor-status').textContent = text; };
function sanitize(raw) {
  if (!raw || raw.version !== 1) throw new Error('state');
  const custom = [];
  const ids = new Set();
  for (const entry of Array.isArray(raw.custom) ? raw.custom.slice(0,5000) : []) {
    if (!entry || typeof entry.id !== 'string' || !/^custom-[a-zA-Z0-9-]+$/.test(entry.id) ||
        ids.has(entry.id) || !songs.some(song => song.id === entry.song) || !levels.includes(entry.jlpt)) continue;
    const limits = {surface:120,reading:200,base:120,pos:40,gloss:2000};
    if (Object.entries(limits).some(([key,max]) => typeof entry[key] !== 'string' || entry[key].length > max)) continue;
    if (!entry.surface.trim() || !entry.gloss.trim()) continue;
    ids.add(entry.id);
    custom.push(Object.fromEntries(['id','song','jlpt',...Object.keys(limits)].map(key => [key,entry[key]])));
  }
  const allowed = new Set([...document.querySelectorAll('.word-note:not([data-custom])')].map(n => n.id));
  custom.forEach(entry => allowed.add(entry.id));
  return {version:1,revision:Number.isSafeInteger(raw.revision) && raw.revision >= 0 ? raw.revision : 0,
    custom,removed:[...new Set((Array.isArray(raw.removed) ? raw.removed : []).filter(id => allowed.has(id)))]};
}
let state;
try { state = sanitize(JSON.parse(document.getElementById('vocab-state').textContent)); }
catch (_) { state = {version:1,revision:0,custom:[],removed:[]}; }
try {
  const saved = localStorage.getItem(storageKey);
  if (saved) {
    const candidate = sanitize(JSON.parse(saved));
    if (candidate.revision > state.revision) state = candidate;
  }
} catch (_) { storageAvailable = false; }
function updateStorageLabel() {
  document.getElementById('save-status').textContent = storageAvailable ?
    '修改自动保存在此浏览器；分享或长期保存请下载 HTML。' :
    '浏览器保存不可用，请下载修改后的 HTML，以免关闭后丢失。';
}
function persist() {
  state.revision = Math.max(Date.now(),state.revision + 1);
  try { localStorage.setItem(storageKey,JSON.stringify(state)); storageAvailable = true; }
  catch (_) { storageAvailable = false; }
  updateStorageLabel();
}
document.querySelectorAll('.word-note[data-custom],.remove-word').forEach(node => node.remove());
function decorate(card) {
  const button = make('button','remove-word','移除');
  button.type = 'button';
  button.setAttribute('aria-label','从词语手帖移除：' + card.dataset.surface);
  card.appendChild(button);
}
function addCustomCard(entry) {
  const card = make('li','word-note');
  card.id = entry.id;
  card.dataset.custom = 'true';
  card.dataset.jlpt = entry.jlpt;
  card.dataset.lemma = entry.base || entry.surface;
  card.dataset.pos = entry.pos;
  card.dataset.surface = entry.surface;
  const heading = make('div');
  const term = make('span');
  term.lang = 'ja';
  if (entry.reading && entry.reading !== entry.surface) {
    const ruby = make('ruby',null,entry.surface);
    ruby.appendChild(make('rt',null,entry.reading));
    term.appendChild(ruby);
  } else term.textContent = entry.surface;
  heading.append(term,make('span','level',entry.jlpt === 'ungraded' ? '未分级' : entry.jlpt));
  card.appendChild(heading);
  if (entry.base && entry.base !== entry.surface) card.appendChild(make('p','lemma','原形：' + entry.base));
  card.append(make('p',null,entry.gloss),make('small',null,'手动添加' + (entry.pos ? ' · ' + entry.pos : '')));
  decorate(card);
  document.getElementById(entry.song).querySelector('.word-notes').appendChild(card);
}
document.querySelectorAll('.word-note').forEach(decorate);
state.custom.forEach(addCustomCard);

function filterVocabulary(level) {
  currentLevel = level;
  document.querySelectorAll('[data-vocab-level]').forEach(button => {
    button.setAttribute('aria-pressed',String(button.dataset.vocabLevel === level));
  });
  songs.forEach(song => {
    const words = Array.from(song.querySelectorAll('.word-note'));
    let visible = 0, active = 0;
    words.forEach(word => {
      const removed = state.removed.includes(word.id);
      if (!removed) active++;
      word.hidden = removed || (level !== 'all' && word.dataset.jlpt !== level);
      if (!word.hidden) visible++;
    });
    song.querySelector('.vocab-count').textContent = '显示 ' + visible + ' / ' + active + ' 个词条（已去重）';
    song.querySelector('.vocab-empty').hidden = visible !== 0;
    const removed = words.filter(word => state.removed.includes(word.id));
    song.querySelector('.removed-count').textContent = String(removed.length);
    const list = song.querySelector('.removed-words');
    list.replaceChildren();
    removed.forEach(word => {
      const item = make('li');
      item.appendChild(make('span',null,word.dataset.surface));
      const restore = make('button',null,'恢复');
      restore.type = 'button'; restore.dataset.restoreWord = word.id;
      item.appendChild(restore); list.appendChild(item);
    });
    song.querySelector('.removed-empty').hidden = removed.length > 0;
  });
}
function restoreWord(id) {
  state.removed = state.removed.filter(value => value !== id);
  persist(); filterVocabulary(currentLevel);
}
function revealTarget(target) {
  if (!target || !target.closest('.annotations')) return true;
  body.classList.remove('hide-notes');
  document.getElementById('notes-toggle').setAttribute('aria-pressed','true');
  const card = target.closest('.word-note');
  if (card && state.removed.includes(card.id)) {
    const song = card.closest('.song');
    const drawer = song.querySelector('.removed-panel');
    drawer.open = true;
    status(song,'“' + card.dataset.surface + '”已从手帖移除，可在下方恢复。');
    drawer.scrollIntoView({block:'center'});
    const restore = Array.from(drawer.querySelectorAll('[data-restore-word]')).find(b => b.dataset.restoreWord === card.id);
    if (restore) restore.focus({preventScroll:true});
    return false;
  }
  if (card && card.hidden) {
    filterVocabulary('all');
    status(card.closest('.song'),'为显示该词，已切换到全部等级。');
  }
  return true;
}
document.getElementById('theme').addEventListener('change',e => {
  body.classList.remove('theme-bunko','theme-cards','theme-lyrics');
  body.classList.add('theme-' + e.target.value);
});
for (const [id,cls] of [['ruby-toggle','hide-ruby'],['notes-toggle','hide-notes']]) {
  document.getElementById(id).addEventListener('click',e => {
    body.classList.toggle(cls);
    e.currentTarget.setAttribute('aria-pressed',String(!body.classList.contains(cls)));
  });
}
document.querySelectorAll('.vocab-filter,.vocab-editor,.removed-panel,#download-book,#save-status').forEach(n => {n.hidden=false;});
document.addEventListener('click',e => {
  const button = e.target.closest('[data-vocab-level]');
  if (button) filterVocabulary(button.dataset.vocabLevel);
  const remove = e.target.closest('.remove-word');
  if (remove) {
    const card = remove.closest('.word-note');
    state.removed = [...new Set([...state.removed,card.id])];
    persist(); filterVocabulary(currentLevel);
    const song = card.closest('.song');
    status(song,'已移除“' + card.dataset.surface + '”；可在“已移除”中恢复。');
    song.querySelector('.removed-panel').open=true;
    song.querySelector('.removed-panel summary').focus();
  }
  const restore = e.target.closest('[data-restore-word]');
  if (restore) {
    const song=restore.closest('.song');
    restoreWord(restore.dataset.restoreWord);
    status(song,'词条已恢复；如未显示，请检查当前 JLPT 筛选。');
    song.querySelector('.removed-panel summary').focus();
  }
  const a=e.target.closest('a[href^="#"]');
  if (a && !revealTarget(document.getElementById(a.getAttribute('href').slice(1)))) e.preventDefault();
});
document.querySelectorAll('.add-word-form').forEach(form => {
  form.addEventListener('submit',e => {
    e.preventDefault();
    if (!form.reportValidity()) return;
    const song=form.closest('.song');
    const data=new FormData(form);
    const entry={song:song.id};
    for (const key of ['surface','reading','base','pos','gloss','jlpt']) entry[key]=String(data.get(key)||'').trim();
    if (!entry.surface || !entry.gloss) {status(song,'词形和释义不能为空或仅为空格。');return;}
    if (entry.base === '*') entry.base='';
    const lemma=entry.base||entry.surface;
    const existing=Array.from(song.querySelectorAll('.word-note')).find(card =>
      card.dataset.lemma === lemma && card.dataset.pos === entry.pos && card.dataset.jlpt === entry.jlpt);
    if (existing) {
      if (state.removed.includes(existing.id)) {
        restoreWord(existing.id);
        status(song,'该词条已存在，已恢复原词条，释义保持原样。');
      } else status(song,'该词条已在手帖中，未重复添加或覆盖释义。');
      filterVocabulary('all');
      existing.scrollIntoView({block:'center'});
      return;
    }
    entry.id='custom-' + (typeof crypto.randomUUID==='function' ? crypto.randomUUID() :
      Date.now().toString(36)+'-'+Math.random().toString(36).slice(2));
    state.custom.push(entry);
    addCustomCard(entry);
    persist(); filterVocabulary('all');
    form.reset();
    status(song,'已添加“' + entry.surface + '”，已切换到全部等级。');
  });
});
window.addEventListener('hashchange',() => {
  const target=document.getElementById(location.hash.slice(1));
  if (revealTarget(target) && target) target.scrollIntoView({block:'start'});
});
document.getElementById('download-book').addEventListener('click',() => {
  persist();
  const clone=document.documentElement.cloneNode(true);
  // Embed data as inert JSON; never interpolate user input into executable JavaScript.
  clone.querySelector('#vocab-state').textContent=JSON.stringify(state).replace(/</g,'\\u003c');
  clone.querySelectorAll('.add-word-form').forEach(form => form.reset());
  clone.querySelectorAll('.vocab-filter,.vocab-editor,.removed-panel,#download-book,#save-status,.remove-word').forEach(n => {n.hidden=true;});
  const selected=document.getElementById('theme').value;
  clone.querySelectorAll('#theme option').forEach(option => {
    if(option.value===selected) option.setAttribute('selected','');
    else option.removeAttribute('selected');
  });
  const file=new Blob(['<!doctype html>\n'+clone.outerHTML],{type:'text/html;charset=utf-8'});
  const url=URL.createObjectURL(file);
  const a=document.createElement('a');
  a.href=url;
  a.download=(document.title.replace(/[<>:"/\\|?*]/g,'_').slice(0,80)||'歌词手帖')+'-已编辑.html';
  document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),10000);
});
filterVocabulary('all');
updateStorageLabel();
revealTarget(document.getElementById(location.hash.slice(1)));
})();