document.getElementById('burger')?.addEventListener('click', () => {
  document.querySelector('.nav')?.classList.toggle('open');
});

/* --- Фильтр цены --- */
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

/* --- Загрузчик фото/видео для объявлений --- */
(function initMediaUploader() {
  const root = document.getElementById('media-uploader');
  const grid = document.getElementById('media-uploader-grid');
  if (!root || !grid) return;

  const max = parseInt(root.dataset.max, 10) || 10;
  const min = parseInt(root.dataset.min, 10) || 1;
  const existing = parseInt(root.dataset.existing, 10) || 0;
  const countEl = document.getElementById('media-uploader-count');
  const form = document.getElementById('listing-form');
  let slotIndex = 0;

  const updateCount = () => {
    const filled = grid.querySelectorAll('.media-uploader__item.is-done').length;
    const total = existing + filled;
    if (countEl) countEl.textContent = `Выбрано: ${filled} · Всего будет: ${total} / ${max}`;
  };

  const createAddSlot = () => {
    const total = existing + grid.querySelectorAll('.media-uploader__item.is-done').length;
    if (total >= max) return;

    const slot = document.createElement('div');
    slot.className = 'media-uploader__item media-uploader__item--add';
    slot.innerHTML = `
      <label class="media-uploader__add-label">
        <input type="file" name="media" class="media-uploader__input" accept="image/*,video/mp4,video/webm,video/quicktime">
        <span class="media-uploader__plus">+</span>
        <span class="media-uploader__add-text">Добавить</span>
      </label>`;
    const input = slot.querySelector('input');
    input.addEventListener('change', () => handleFile(slot, input));
    grid.appendChild(slot);
  };

  const handleFile = (slot, input) => {
    const file = input.files[0];
    if (!file) return;

    slot.classList.remove('media-uploader__item--add');
    slot.classList.add('is-done');
    slot.innerHTML = '';

    const isVideo = file.type.startsWith('video/');
    if (isVideo) {
      const vid = document.createElement('video');
      vid.src = URL.createObjectURL(file);
      vid.muted = true;
      slot.appendChild(vid);
      const badge = document.createElement('span');
      badge.className = 'media-uploader__badge';
      badge.textContent = '▶';
      slot.appendChild(badge);
    } else {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      img.alt = '';
      slot.appendChild(img);
    }

    const check = document.createElement('span');
    check.className = 'media-uploader__check';
    check.textContent = '✓';
    slot.appendChild(check);

    const name = document.createElement('span');
    name.className = 'media-uploader__name';
    name.textContent = file.name.length > 18 ? file.name.slice(0, 15) + '…' : file.name;
    slot.appendChild(name);

    const hidden = document.createElement('input');
    hidden.type = 'file';
    hidden.name = 'media';
    hidden.hidden = true;
    const dt = new DataTransfer();
    dt.items.add(file);
    hidden.files = dt.files;
    slot.appendChild(hidden);

    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'media-uploader__remove';
    remove.textContent = '×';
    remove.title = 'Убрать';
    remove.addEventListener('click', () => {
      slot.remove();
      if (!grid.querySelector('.media-uploader__item--add')) createAddSlot();
      updateCount();
    });
    slot.appendChild(remove);

    slot.querySelector('.media-uploader__add-label')?.remove();
    if (!grid.querySelector('.media-uploader__item--add')) createAddSlot();
    updateCount();
  };

  createAddSlot();
  updateCount();

  form?.addEventListener('submit', (e) => {
    const filled = grid.querySelectorAll('.media-uploader__item.is-done').length;
    if (existing + filled < min) {
      e.preventDefault();
      alert(`Добавьте хотя бы ${min} фото или видео`);
    }
  });
})();

/* --- Аватар в профиле --- */
document.querySelector('.avatar-upload input[type=file]')?.addEventListener('change', function () {
  const name = this.files[0]?.name || 'Файл не выбран';
  const el = document.getElementById('avatar-filename');
  if (el) el.textContent = name;
});

/* --- Чат: вложение --- */
document.getElementById('chat-attachment')?.addEventListener('change', function () {
  const el = document.getElementById('chat-file-name');
  if (!el) return;
  if (this.files[0]) {
    el.textContent = '📎 ' + this.files[0].name;
    el.hidden = false;
  } else {
    el.hidden = true;
  }
});

/* --- Чат: контекстное меню --- */
(function initChatContextMenu() {
  const box = document.getElementById('chat-box');
  const menu = document.getElementById('chat-context-menu');
  if (!box || !menu) return;

  const csrf = box.dataset.csrf;
  let activeMsgId = null;

  const showMenu = (x, y, msgId) => {
    activeMsgId = msgId;
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    menu.removeAttribute('hidden');
    menu.style.display = 'block';
  };

  const hideMenu = () => {
    menu.setAttribute('hidden', '');
    menu.style.display = 'none';
    activeMsgId = null;
  };

  const openMenuForMsg = (msg, x, y) => {
    if (!msg || msg.dataset.own !== '1' || msg.dataset.hasAttachment === '1') return;
    showMenu(x, y, msg.dataset.msgId);
  };

  box.addEventListener('contextmenu', (e) => {
    const msg = e.target.closest('.chat-msg[data-own="1"]');
    if (!msg || msg.dataset.hasAttachment === '1') return;
    e.preventDefault();
    openMenuForMsg(msg, e.clientX, e.clientY);
  });

  box.querySelectorAll('.chat-msg__menu-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const msg = btn.closest('.chat-msg');
      const rect = btn.getBoundingClientRect();
      openMenuForMsg(msg, rect.left, rect.bottom + 4);
    });
  });

  document.addEventListener('click', (e) => {
    if (!menu.contains(e.target)) hideMenu();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') hideMenu();
  });

  menu.addEventListener('click', async (e) => {
    e.stopPropagation();
    const btn = e.target.closest('button[data-action]');
    if (!btn || !activeMsgId) return;
    const action = btn.dataset.action;
    const msgId = activeMsgId;
    hideMenu();

    if (action === 'delete') {
      if (!confirm('Удалить сообщение?')) return;
      const fd = new FormData();
      fd.append('csrfmiddlewaretoken', csrf);
      const res = await fetch('/messages/message/' + msgId + '/delete/', { method: 'POST', body: fd });
      if (res.ok) location.reload();
      else alert('Не удалось удалить');
      return;
    }

    if (action === 'edit') {
      const msgEl = box.querySelector('[data-msg-id="' + msgId + '"] .chat-msg__text');
      const current = msgEl?.textContent?.trim() || '';
      const next = prompt('Изменить сообщение:', current);
      if (!next || next === current) return;
      const fd = new FormData();
      fd.append('csrfmiddlewaretoken', csrf);
      fd.append('body', next);
      const res = await fetch('/messages/message/' + msgId + '/edit/', { method: 'POST', body: fd });
      if (res.ok) location.reload();
      else alert('Не удалось изменить');
    }
  });
})();

/* --- Заглушка для битых картинок --- */
document.querySelectorAll('img[data-fallback]').forEach((img) => {
  img.addEventListener('error', () => {
    img.src = img.dataset.fallback;
  });
});

/* --- Уведомления: выпадающий список (как ВК) --- */
(function initNotifyDropdown() {
  const wrap = document.getElementById('nav-notify');
  const bell = document.getElementById('notify-bell');
  const dropdown = document.getElementById('notify-dropdown');
  if (!wrap || !bell || !dropdown) return;

  const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

  const close = () => {
    dropdown.setAttribute('hidden', '');
    dropdown.style.display = 'none';
  };

  const open = async () => {
    dropdown.removeAttribute('hidden');
    dropdown.style.display = 'flex';
    if (csrf) {
      const fd = new FormData();
      fd.append('csrfmiddlewaretoken', csrf);
      fetch('/accounts/notifications/read/', { method: 'POST', body: fd }).catch(() => {});
      wrap.querySelectorAll('.nav-badge').forEach((b) => b.remove());
      dropdown.querySelectorAll('.nav-notify__item--new').forEach((el) => el.classList.remove('nav-notify__item--new'));
    }
  };

  bell.addEventListener('click', (e) => {
    e.stopPropagation();
    if (dropdown.hasAttribute('hidden')) open();
    else close();
  });

  document.addEventListener('click', (e) => {
    if (!wrap.contains(e.target)) close();
  });
})();

/* --- Лайтбокс: смотреть фото в чате без скачивания --- */
(function initLightbox() {
  const lb = document.getElementById('img-lightbox');
  const lbImg = document.getElementById('lightbox-img');
  const lbClose = document.getElementById('lightbox-close');
  if (!lb || !lbImg) return;

  const show = (src) => {
    lbImg.src = src;
    lb.removeAttribute('hidden');
    lb.style.display = 'flex';
  };
  const hide = () => {
    lb.setAttribute('hidden', '');
    lb.style.display = 'none';
    lbImg.src = '';
  };

  document.querySelectorAll('.chat-lightbox-trigger').forEach((img) => {
    img.addEventListener('click', () => show(img.src));
    img.addEventListener('keydown', (e) => { if (e.key === 'Enter') show(img.src); });
  });

  lbClose?.addEventListener('click', hide);
  lb.addEventListener('click', (e) => { if (e.target === lb) hide(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hide(); });
})();
