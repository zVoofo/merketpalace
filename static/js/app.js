document.getElementById('burger')?.addEventListener('click', () => {
  document.getElementById('main-nav')?.classList.toggle('open');
});

/* Сброс горизонтального сдвига шапки после переполнения */
(function resetPageScroll() {
  document.documentElement.scrollLeft = 0;
  document.body.scrollLeft = 0;
  document.querySelector('.nav')?.scrollTo(0, 0);
})();

/* --- Подтверждение действий (data-confirm) --- */
(function initConfirmDialogs() {
  document.addEventListener('submit', (e) => {
    const form = e.target.closest('form[data-confirm]');
    if (!form) return;
    if (!window.confirm(form.dataset.confirm)) e.preventDefault();
  });

  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-confirm]');
    if (!el || el.tagName === 'FORM') return;
    if (!window.confirm(el.dataset.confirm)) {
      e.preventDefault();
      e.stopImmediatePropagation();
    }
  }, true);
})();

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

/* --- Мобильная панель фильтров каталога --- */
(function initCatalogFilters() {
  const toggle = document.getElementById('filter-toggle');
  const panel = document.getElementById('catalog-filters-panel');
  if (!toggle || !panel) return;

  toggle.addEventListener('click', () => {
    const open = panel.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
})();

/* --- Обрезка фото перед загрузкой --- */
const ImageCropper = (() => {
  const SIZE = 320;
  const OUTPUT = 1200;
  let modal, canvas, zoomInput, img, offsetX, offsetY, zoom, baseScale;
  let dragging = false, dragStart = null, pendingResolve, pendingReject, sourceFile;

  const ensureModal = () => {
    if (modal) return;
    modal = document.getElementById('image-crop-modal');
    canvas = document.getElementById('crop-canvas');
    zoomInput = document.getElementById('crop-zoom');
    if (!modal || !canvas) return;

    modal.querySelector('[data-crop-cancel]')?.addEventListener('click', () => close(null));
    modal.querySelector('[data-crop-skip]')?.addEventListener('click', () => close(sourceFile));
    modal.querySelector('[data-crop-apply]')?.addEventListener('click', () => {
      exportCropped().then((file) => close(file)).catch(() => close(sourceFile));
    });
    modal.querySelector('[data-crop-close]')?.addEventListener('click', () => close(null));
    zoomInput?.addEventListener('input', () => {
      zoom = parseFloat(zoomInput.value) || 1;
      clampOffset();
      draw();
    });

    const onPointerDown = (e) => {
      dragging = true;
      canvas.classList.add('is-dragging');
      dragStart = { x: e.clientX, y: e.clientY, ox: offsetX, oy: offsetY };
      canvas.setPointerCapture(e.pointerId);
    };
    const onPointerMove = (e) => {
      if (!dragging || !dragStart) return;
      offsetX = dragStart.ox + (e.clientX - dragStart.x);
      offsetY = dragStart.oy + (e.clientY - dragStart.y);
      clampOffset();
      draw();
    };
    const onPointerUp = (e) => {
      dragging = false;
      canvas.classList.remove('is-dragging');
      dragStart = null;
      try { canvas.releasePointerCapture(e.pointerId); } catch (_) { /* noop */ }
    };
    canvas.addEventListener('pointerdown', onPointerDown);
    canvas.addEventListener('pointermove', onPointerMove);
    canvas.addEventListener('pointerup', onPointerUp);
    canvas.addEventListener('pointercancel', onPointerUp);
  };

  const clampOffset = () => {
    if (!img) return;
    const s = baseScale * zoom;
    const w = img.width * s;
    const h = img.height * s;
    offsetX = Math.min(0, Math.max(SIZE - w, offsetX));
    offsetY = Math.min(0, Math.max(SIZE - h, offsetY));
  };

  const draw = () => {
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#141210';
    ctx.fillRect(0, 0, SIZE, SIZE);
    const s = baseScale * zoom;
    ctx.drawImage(img, offsetX, offsetY, img.width * s, img.height * s);
    ctx.strokeStyle = 'rgba(255,255,255,.25)';
    ctx.strokeRect(0.5, 0.5, SIZE - 1, SIZE - 1);
  };

  const exportCropped = () => new Promise((resolve, reject) => {
    const out = document.createElement('canvas');
    out.width = out.height = OUTPUT;
    const ctx = out.getContext('2d');
    const ratio = OUTPUT / SIZE;
    const s = baseScale * zoom * ratio;
    ctx.drawImage(img, offsetX * ratio, offsetY * ratio, img.width * s, img.height * s);
    out.toBlob((blob) => {
      if (!blob) { reject(new Error('crop failed')); return; }
      const name = (sourceFile.name || 'photo').replace(/\.[^.]+$/, '') + '.jpg';
      resolve(new File([blob], name, { type: 'image/jpeg', lastModified: Date.now() }));
    }, 'image/jpeg', 0.9);
  });

  const close = (result) => {
    modal.hidden = true;
    if (result === null) pendingReject?.(new Error('cancelled'));
    else pendingResolve?.(result);
    pendingResolve = pendingReject = null;
    sourceFile = null;
    img = null;
  };

  const shouldCrop = (file) => file.type.startsWith('image/')
    && file.type !== 'image/gif'
    && file.type !== 'image/svg+xml';

  return {
    open(file) {
      ensureModal();
      if (!modal || !canvas || !shouldCrop(file)) return Promise.resolve(file);
      sourceFile = file;
      return new Promise((resolve, reject) => {
        pendingResolve = resolve;
        pendingReject = reject;
        const url = URL.createObjectURL(file);
        const image = new Image();
        image.onload = () => {
          URL.revokeObjectURL(url);
          img = image;
          baseScale = Math.max(SIZE / img.width, SIZE / img.height);
          zoom = 1;
          if (zoomInput) zoomInput.value = '1';
          offsetX = (SIZE - img.width * baseScale) / 2;
          offsetY = (SIZE - img.height * baseScale) / 2;
          clampOffset();
          draw();
          modal.hidden = false;
        };
        image.onerror = () => {
          URL.revokeObjectURL(url);
          resolve(file);
        };
        image.src = url;
      });
    },
  };
})();

/* --- Загрузчик фото/видео для объявлений --- */
(function initMediaUploader() {
  const root = document.getElementById('media-uploader');
  const grid = document.getElementById('media-uploader-grid');
  if (!root || !grid) return;

  const max = parseInt(root.dataset.max, 10) || 10;
  const min = parseInt(root.dataset.min, 10) || 1;
  const enableCrop = root.dataset.crop !== '0';
  let existingCount = root.querySelectorAll('.media-uploader__item.is-existing').length
    || parseInt(root.dataset.existing, 10) || 0;
  const countEl = document.getElementById('media-uploader-count');
  const form = root.closest('form') || document.getElementById('listing-form');

  const countNewFiles = () => grid.querySelectorAll('.media-uploader__item.is-done:not(.is-existing)').length;

  const updateCount = () => {
    const filled = countNewFiles();
    const total = existingCount + filled;
    if (countEl) countEl.textContent = `Новых: ${filled} · Всего: ${total} / ${max}`;
  };

  const removeExisting = (slot) => {
    const id = slot.dataset.imageId;
    if (id && form) {
      const hidden = document.createElement('input');
      hidden.type = 'hidden';
      hidden.name = 'remove_media';
      hidden.value = id;
      form.appendChild(hidden);
    }
    slot.remove();
    existingCount = Math.max(0, existingCount - 1);
    if (!grid.querySelector('.media-uploader__item--add')) createAddSlot();
    updateCount();
  };

  grid.querySelectorAll('.media-uploader__item.is-existing .media-uploader__remove').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const slot = btn.closest('.media-uploader__item');
      if (slot) removeExisting(slot);
    });
  });

  const fillSlot = (slot, file) => {
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
      const imgEl = document.createElement('img');
      imgEl.src = URL.createObjectURL(file);
      imgEl.alt = '';
      slot.appendChild(imgEl);
    }

    const check = document.createElement('span');
    check.className = 'media-uploader__check';
    check.textContent = '✓';
    slot.appendChild(check);

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

    if (!grid.querySelector('.media-uploader__item--add')) createAddSlot();
    updateCount();
  };

  const createAddSlot = () => {
    const total = existingCount + countNewFiles();
    if (total >= max) return;

    const slot = document.createElement('div');
    slot.className = 'media-uploader__item media-uploader__item--add';
    slot.innerHTML = `
      <label class="media-uploader__add-label">
        <input type="file" class="media-uploader__input" accept="image/*,video/mp4,video/webm,video/quicktime">
        <span class="media-uploader__plus">+</span>
        <span class="media-uploader__add-text">Добавить</span>
      </label>`;
    const input = slot.querySelector('input');
    input.addEventListener('change', () => handleFile(slot, input));
    grid.appendChild(slot);
  };

  const handleFile = async (slot, input) => {
    const file = input.files[0];
    if (!file) return;
    input.value = '';

    let finalFile = file;
    if (enableCrop && file.type.startsWith('image/')) {
      try {
        finalFile = await ImageCropper.open(file);
      } catch (_) {
        return;
      }
    }

    fillSlot(slot, finalFile);
  };

  createAddSlot();
  updateCount();

  form?.addEventListener('submit', (e) => {
    const total = existingCount + countNewFiles();
    if (min > 0 && total < min) {
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

  const showMenu = (x, y, msgId, hasAttachment) => {
    activeMsgId = msgId;
    const editBtn = menu.querySelector('[data-action="edit"]');
    if (editBtn) editBtn.hidden = hasAttachment;
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    menu.removeAttribute('hidden');
    menu.style.display = 'block';
  };

  const hideMenu = () => {
    menu.setAttribute('hidden', '');
    menu.style.display = 'none';
    activeMsgId = null;
    const editBtn = menu.querySelector('[data-action="edit"]');
    if (editBtn) editBtn.hidden = false;
  };

  const openMenuForMsg = (msg, x, y) => {
    if (!msg || msg.dataset.own !== '1') return;
    showMenu(x, y, msg.dataset.msgId, msg.dataset.hasAttachment === '1');
  };

  box.addEventListener('contextmenu', (e) => {
    const msg = e.target.closest('.chat-msg[data-own="1"]');
    if (!msg) return;
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
      const hasAttachment = box.querySelector('[data-msg-id="' + msgId + '"]')?.dataset.hasAttachment === '1';
      const label = hasAttachment ? 'Удалить фото/видео?' : 'Удалить сообщение?';
      if (!confirm(label)) return;
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

/* --- Профиль: режим редактирования --- */
(function initProfileEdit() {
  const view = document.getElementById('profile-view');
  const edit = document.getElementById('profile-edit');
  const openBtn = document.getElementById('profile-edit-open');
  const closeBtn = document.getElementById('profile-edit-close');
  if (!view || !edit) return;

  const showEdit = () => {
    view.hidden = true;
    edit.hidden = false;
    edit.classList.add('profile-edit--open');
    edit.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const showView = () => {
    edit.hidden = true;
    edit.classList.remove('profile-edit--open');
    view.hidden = false;
  };

  openBtn?.addEventListener('click', showEdit);
  closeBtn?.addEventListener('click', showView);

  if (edit.classList.contains('profile-edit--open')) {
    showEdit();
  }
})();

/* --- Профиль: якоря внутри вкладки «Мои заявки» --- */
(function initProfileRequestsNav() {
  const hash = (location.hash || '').replace('#', '');
  if (['offers', 'my-searches', 'sent'].includes(hash) && !location.search.includes('tab=requests')) {
    location.replace(`${location.pathname}?tab=requests#${hash}`);
    return;
  }

  const panel = document.getElementById('profile-panel-requests');
  if (!panel) return;

  const scrollToAnchor = (id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    panel.querySelectorAll('[data-requests-anchor]').forEach((link) => {
      link.classList.toggle('is-active', link.dataset.requestsAnchor === id);
    });
  };

  panel.querySelectorAll('[data-requests-anchor]').forEach((link) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      scrollToAnchor(link.dataset.requestsAnchor);
      history.replaceState(null, '', `?tab=requests#${link.dataset.requestsAnchor}`);
    });
  });

  const hash = (location.hash || '').replace('#', '');
  if (location.search.includes('tab=requests') && ['offers', 'my-searches', 'sent'].includes(hash)) {
    requestAnimationFrame(() => scrollToAnchor(hash));
  }
})();

/* --- Заглушка для битых картинок (только вне каталога) --- */
document.querySelectorAll('img[data-fallback]:not(.card__img)').forEach((img) => {
  img.addEventListener('error', () => {
    img.src = img.dataset.fallback;
  });
});

/* --- Уведомления: выпадающий список --- */
(function initNotifyDropdown() {
  const wrap = document.getElementById('nav-notify');
  const bell = document.getElementById('notify-bell');
  const dropdown = document.getElementById('notify-dropdown');
  if (!wrap || !bell || !dropdown) return;

  const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

  const positionDropdown = () => {
    const rect = bell.getBoundingClientRect();
    dropdown.style.top = `${rect.bottom + 8}px`;
    dropdown.style.right = `${Math.max(12, window.innerWidth - rect.right)}px`;
    dropdown.style.left = 'auto';
  };

  const close = () => {
    dropdown.setAttribute('hidden', '');
    dropdown.style.display = 'none';
    bell.setAttribute('aria-expanded', 'false');
  };

  const open = () => {
    positionDropdown();
    dropdown.removeAttribute('hidden');
    dropdown.style.display = 'flex';
    bell.setAttribute('aria-expanded', 'true');
    if (csrf) {
      const fd = new FormData();
      fd.append('csrfmiddlewaretoken', csrf);
      fetch('/accounts/notifications/read/', { method: 'POST', body: fd }).catch(() => {});
      document.getElementById('notify-badge')?.remove();
      dropdown.querySelectorAll('.nav-notify__item--new').forEach((el) => el.classList.remove('nav-notify__item--new'));
    }
  };

  bell.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (dropdown.hasAttribute('hidden')) open();
    else close();
  });

  window.addEventListener('resize', () => {
    if (!dropdown.hasAttribute('hidden')) positionDropdown();
  });

  document.addEventListener('click', (e) => {
    if (wrap.contains(e.target) || dropdown.contains(e.target)) return;
    close();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
  });

  dropdown.addEventListener('click', async (e) => {
    const btn = e.target.closest('.nav-notify__dismiss');
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    const id = btn.dataset.id;
    const row = btn.closest('.nav-notify__row');
    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', csrf);
    const res = await fetch('/accounts/notifications/' + id + '/delete/', { method: 'POST', body: fd });
    if (res.ok) {
      row?.remove();
      if (!dropdown.querySelector('.nav-notify__row')) {
        const list = document.getElementById('notify-list');
        if (list && !list.querySelector('.nav-notify__empty')) {
          const empty = document.createElement('p');
          empty.className = 'nav-notify__empty';
          empty.textContent = 'Нет уведомлений';
          list.appendChild(empty);
        }
      }
    }
  });
})();

/* --- Чат: всегда показывать последние сообщения --- */
(function initChatScroll() {
  const box = document.getElementById('chat-messages');
  if (!box) return;

  const scrollToBottom = (smooth) => {
    const top = box.scrollHeight - box.clientHeight;
    box.scrollTo({ top: Math.max(0, top), behavior: smooth ? 'smooth' : 'instant' });
  };

  scrollToBottom(false);
  requestAnimationFrame(() => scrollToBottom(false));

  window.addEventListener('load', () => scrollToBottom(false));

  box.querySelectorAll('img, video').forEach((el) => {
    el.addEventListener('load', () => scrollToBottom(false));
  });

  const markScrollBottom = () => sessionStorage.setItem('chat-scroll-bottom', '1');

  const form = document.getElementById('chat-form');
  form?.addEventListener('submit', markScrollBottom);

  if (sessionStorage.getItem('chat-scroll-bottom')) {
    sessionStorage.removeItem('chat-scroll-bottom');
    setTimeout(() => scrollToBottom(false), 0);
    setTimeout(() => scrollToBottom(false), 80);
    setTimeout(() => scrollToBottom(false), 250);
  }
})();

/* --- Поддержка: быстрые вопросы (без скачка вверх) --- */
(function initSupportQuick() {
  const grid = document.getElementById('support-quick');
  const form = document.getElementById('chat-form');
  if (!grid || !form) return;

  grid.addEventListener('click', async (e) => {
    const btn = e.target.closest('.support-quick__btn');
    if (!btn) return;
    e.preventDefault();
    const q = btn.dataset.question;
    if (!q) return;

    const csrf = form.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', csrf);
    fd.append('body', q);
    sessionStorage.setItem('chat-scroll-bottom', '1');
    btn.disabled = true;

    try {
      const res = await fetch(window.location.pathname, { method: 'POST', body: fd, credentials: 'same-origin' });
      if (res.ok || res.redirected) {
        window.location.reload();
        return;
      }
    } catch (err) {
      /* fallback */
    }

    const input = document.getElementById('chat-body');
    if (input) input.value = q;
    form.requestSubmit();
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

/* --- Слайдер фото/видео в объявлении --- */
(function initProductGallery() {
  const gallery = document.getElementById('product-gallery');
  if (!gallery) return;

  const slides = [...gallery.querySelectorAll('.gallery-slide')];
  const dots = [...gallery.querySelectorAll('.gallery-dot')];
  const thumbs = [...gallery.querySelectorAll('.gallery-thumb')];
  const prev = gallery.querySelector('.gallery-nav--prev');
  const next = gallery.querySelector('.gallery-nav--next');
  const counter = document.getElementById('gallery-current');
  if (slides.length <= 1) return;

  let idx = 0;

  const pauseVideos = () => {
    slides.forEach((s) => s.querySelector('video')?.pause());
    thumbs.forEach((t) => t.querySelector('video')?.pause());
  };

  const show = (i) => {
    pauseVideos();
    idx = (i + slides.length) % slides.length;
    slides.forEach((s, n) => s.classList.toggle('is-active', n === idx));
    dots.forEach((d, n) => d.classList.toggle('is-active', n === idx));
    thumbs.forEach((t, n) => t.classList.toggle('is-active', n === idx));
    if (counter) counter.textContent = String(idx + 1);
  };

  prev?.addEventListener('click', () => show(idx - 1));
  next?.addEventListener('click', () => show(idx + 1));
  dots.forEach((d) => d.addEventListener('click', () => show(parseInt(d.dataset.index, 10))));
  thumbs.forEach((t) => t.addEventListener('click', () => show(parseInt(t.dataset.index, 10))));

  let touchX = null;
  gallery.addEventListener('touchstart', (e) => { touchX = e.changedTouches[0].clientX; }, { passive: true });
  gallery.addEventListener('touchend', (e) => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) show(dx < 0 ? idx + 1 : idx - 1);
    touchX = null;
  }, { passive: true });

  document.addEventListener('keydown', (e) => {
    if (!gallery.matches(':hover') && document.activeElement !== document.body) return;
    if (e.key === 'ArrowLeft') show(idx - 1);
    if (e.key === 'ArrowRight') show(idx + 1);
  });
})();

/* --- Заявки покупателей: выбор объявления --- */
(function initLookingBoard() {
  const dataEl = document.getElementById('seller-listings-data');
  if (!dataEl) return;

  let listings = [];
  try {
    listings = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }
  if (!listings.length) return;

  const scoreListing = (title, query) => {
    const t = (title || '').toLowerCase();
    const q = (query || '').trim().toLowerCase();
    if (!q) return 0;
    let s = 0;
    if (t.includes(q)) s += 10;
    q.replace(/[,—]/g, ' ').split(/\s+/).forEach((w) => {
      if (w.length >= 3 && t.includes(w)) s += 3;
    });
    return s;
  };

  const formatPrice = (n) => `${Number(n).toLocaleString('ru-RU')} ₽`;

  const buildRows = (container, query) => {
    const sorted = [...listings].sort(
      (a, b) => scoreListing(b.title, query) - scoreListing(a.title, query),
    );
    container.innerHTML = '';
    sorted.forEach((item) => {
      const match = scoreListing(item.title, query) > 0;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'offer-row' + (match ? ' is-match' : '');
      btn.dataset.id = String(item.id);
      btn.dataset.title = (item.title || '').toLowerCase();

      const img = document.createElement('img');
      img.src = item.image;
      img.alt = '';
      img.className = 'offer-row__thumb';
      img.width = 56;
      img.height = 56;
      img.loading = 'lazy';
      img.decoding = 'async';

      const info = document.createElement('span');
      info.className = 'offer-row__info';

      const title = document.createElement('span');
      title.className = 'offer-row__title';
      title.textContent = item.title;

      const meta = document.createElement('span');
      meta.className = 'offer-row__meta';

      const price = document.createElement('span');
      price.className = 'offer-row__price';
      price.textContent = formatPrice(item.price);

      const stock = document.createElement('span');
      stock.textContent = `В наличии: ${item.quantity} шт.`;

      meta.append(price, stock);
      info.append(title, meta);

      const badge = document.createElement('span');
      badge.className = 'offer-row__badge';
      badge.setAttribute('aria-hidden', 'true');

      btn.append(img, info, badge);
      container.appendChild(btn);
    });
    return container.querySelectorAll('.offer-row');
  };

  let openCard = null;

  const closePanel = (card) => {
    if (!card) return;
    card.classList.remove('is-open');
    card.querySelector('.looking-picker')?.setAttribute('hidden', '');
    if (openCard === card) openCard = null;
  };

  const wirePanel = (card) => {
    const picker = card.querySelector('.looking-picker');
    const list = picker?.querySelector('.looking-picker__list');
    const search = picker?.querySelector('.looking-picker__search');
    const countEl = picker?.querySelector('.looking-picker__count');
    const form = picker?.querySelector('.looking-picker__footer');
    const hiddenId = form?.querySelector('[name=listing_id]');
    const selectedLabel = picker?.querySelector('.looking-picker__selected');
    const submitBtn = form?.querySelector('[type=submit]');
    const query = card.dataset.query || '';
    if (!picker || !list || !form) return;

    let rows = buildRows(list, query);
    let selected = null;

    const updateCount = () => {
      const visible = [...rows].filter((r) => !r.hidden).length;
      if (countEl) countEl.textContent = visible ? `${visible} из ${listings.length}` : 'Ничего не найдено';
    };

    const selectRow = (row) => {
      selected = row;
      rows.forEach((r) => r.classList.toggle('is-selected', r === row));
      const id = row.dataset.id || '';
      if (hiddenId) hiddenId.value = id;
      if (submitBtn) submitBtn.disabled = !id;
      const title = row.querySelector('.offer-row__title')?.textContent?.trim() || '';
      const price = row.querySelector('.offer-row__price')?.textContent?.trim() || '';
      if (selectedLabel) {
        selectedLabel.textContent = title ? `${title} · ${price}` : 'Выберите объявление';
      }
    };

    list.addEventListener('click', (e) => {
      const row = e.target.closest('.offer-row');
      if (!row || row.hidden) return;
      selectRow(row);
    });

    search?.addEventListener('input', () => {
      const q = (search.value || '').trim().toLowerCase();
      rows.forEach((row) => {
        const title = row.dataset.title || '';
        row.hidden = q ? !title.includes(q) : false;
      });
      updateCount();
    });

    picker.querySelector('[data-offer-close]')?.addEventListener('click', () => closePanel(card));
    updateCount();
  };

  document.querySelectorAll('.looking-request').forEach(wirePanel);

  document.querySelectorAll('[data-offer-open]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const card = btn.closest('.looking-request');
      const picker = card?.querySelector('.looking-picker');
      if (!card || !picker) return;

      if (openCard && openCard !== card) closePanel(openCard);

      const isOpen = !picker.hidden;
      if (isOpen) {
        closePanel(card);
        return;
      }

      card.classList.add('is-open');
      picker.removeAttribute('hidden');
      openCard = card;
      picker.querySelector('.looking-picker__search')?.focus();
      picker.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && openCard) closePanel(openCard);
  });
})();

/* --- Корзина: автосохранение количества --- */
(function initCartAutoSave() {
  const form = document.getElementById('cart-form');
  const checkoutBtn = document.getElementById('cart-checkout-btn');
  const hint = document.getElementById('cart-save-hint');
  if (!form) return;

  let timer = null;
  let saving = false;

  const setHint = (text, ok) => {
    if (!hint) return;
    hint.textContent = text;
    hint.classList.toggle('cart-save-hint--ok', !!ok);
  };

  const saveCart = async () => {
    if (saving) return true;
    saving = true;
    setHint('Сохранение...', false);
    const fd = new FormData(form);
    document.querySelectorAll('.cart-qty-input').forEach((input) => {
      if (input.name) fd.set(input.name, input.value);
    });
    try {
      const res = await fetch(form.action, { method: 'POST', body: fd, redirect: 'follow' });
      saving = false;
      if (res.ok || res.redirected) {
        setHint('Количество сохранено', true);
        return true;
      }
    } catch (e) {
      saving = false;
    }
    setHint('Не удалось сохранить — нажмите «Обновить»', false);
    return false;
  };

  document.querySelectorAll('.cart-qty-input').forEach((input) => {
    input.addEventListener('change', () => {
      clearTimeout(timer);
      timer = setTimeout(saveCart, 400);
    });
  });

  checkoutBtn?.addEventListener('click', async (e) => {
    e.preventDefault();
    const msg = checkoutBtn.dataset.confirm || 'Перейти к оформлению заказа?';
    if (!window.confirm(msg)) return;
    const ok = await saveCart();
    if (ok) window.location.href = checkoutBtn.href;
  });
})();
