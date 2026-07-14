document.getElementById('burger')?.addEventListener('click', () => {
  document.querySelector('.nav')?.classList.toggle('open');
});

/* --- Фильтр цены: слайдер + поля ввода --- */
(function initPriceRange() {
  const minRange = document.getElementById('price-min-range');
  const maxRange = document.getElementById('price-max-range');
  const minInput = document.getElementById('price-min-input');
  const maxInput = document.getElementById('price-max-input');
  if (!minRange || !maxRange || !minInput || !maxInput) return;

  const syncFromRange = () => {
    let lo = parseInt(minRange.value, 10) || 0;
    let hi = parseInt(maxRange.value, 10) || 0;
    if (lo > hi) {
      if (document.activeElement === minRange) maxRange.value = lo;
      else minRange.value = hi;
      lo = parseInt(minRange.value, 10);
      hi = parseInt(maxRange.value, 10);
    }
    minInput.value = lo || '';
    maxInput.value = hi >= parseInt(maxRange.max, 10) ? '' : hi;
  };

  const syncFromInput = () => {
    const max = parseInt(maxRange.max, 10);
    let lo = parseInt(minInput.value, 10);
    let hi = parseInt(maxInput.value, 10);
    if (!isNaN(lo)) minRange.value = Math.min(lo, max);
    if (!isNaN(hi)) maxRange.value = Math.min(hi, max);
    else maxRange.value = max;
  };

  minRange.addEventListener('input', syncFromRange);
  maxRange.addEventListener('input', syncFromRange);
  minInput.addEventListener('input', syncFromInput);
  maxInput.addEventListener('input', syncFromInput);
})();

/* --- Чат: контекстное меню (ПКМ) --- */
(function initChatContextMenu() {
  const box = document.getElementById('chat-box');
  const menu = document.getElementById('chat-context-menu');
  if (!box || !menu) return;

  const csrf = box.dataset.csrf;
  let activeMsgId = null;

  const hideMenu = () => {
    menu.hidden = true;
    activeMsgId = null;
  };

  box.addEventListener('contextmenu', (e) => {
    const msg = e.target.closest('.chat-msg[data-own="1"]');
    if (!msg || msg.dataset.hasAttachment === '1') return;
    e.preventDefault();
    activeMsgId = msg.dataset.msgId;
    menu.style.left = `${e.pageX}px`;
    menu.style.top = `${e.pageY}px`;
    menu.hidden = false;
  });

  document.addEventListener('click', hideMenu);

  menu.addEventListener('click', async (e) => {
    const btn = e.target.closest('button[data-action]');
    if (!btn || !activeMsgId) return;
    const action = btn.dataset.action;
    hideMenu();

    if (action === 'delete') {
      const fd = new FormData();
      fd.append('csrfmiddlewaretoken', csrf);
      const res = await fetch(`/messages/message/${activeMsgId}/delete/`, { method: 'POST', body: fd });
      if (res.ok) location.reload();
      return;
    }

    if (action === 'edit') {
      const msgEl = box.querySelector(`[data-msg-id="${activeMsgId}"] .chat-msg__text`);
      const current = msgEl?.textContent?.trim() || '';
      const next = prompt('Изменить сообщение:', current);
      if (!next || next === current) return;
      const fd = new FormData();
      fd.append('csrfmiddlewaretoken', csrf);
      fd.append('body', next);
      const res = await fetch(`/messages/message/${activeMsgId}/edit/`, { method: 'POST', body: fd });
      if (res.ok) location.reload();
    }
  });
})();
