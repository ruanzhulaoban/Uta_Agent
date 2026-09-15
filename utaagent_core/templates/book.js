(() => {
const body = document.body;
document.getElementById('theme').addEventListener('change', e => {
  body.classList.remove('theme-bunko','theme-cards','theme-lyrics');
  body.classList.add('theme-' + e.target.value);
});
for (const [id, cls] of [['ruby-toggle','hide-ruby'],['notes-toggle','hide-notes']]) {
  document.getElementById(id).addEventListener('click', e => {
    body.classList.toggle(cls);
    e.currentTarget.setAttribute('aria-pressed', String(!body.classList.contains(cls)));
  });
}
document.addEventListener('click', e => {
  const a = e.target.closest('a[href^="#"]');
  if (!a) return;
  const target = document.getElementById(a.getAttribute('href').slice(1));
  if (target && target.closest('.annotations')) {
    body.classList.remove('hide-notes');
    document.getElementById('notes-toggle').setAttribute('aria-pressed','true');
  }
});
})();