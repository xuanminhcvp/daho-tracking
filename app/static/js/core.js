// Tien ich chung cho moi module: goi API, escape HTML, modal, toast, dinh dang.
(function () {
  async function api(method, url, body) {
    const opt = { method, headers: {} };
    if (body !== undefined) {
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(body);
    }
    const res = await fetch(url, opt);
    let data = null;
    try { data = await res.json(); } catch (e) { /* khong co body */ }
    if (!res.ok) throw new Error((data && data.error) || `Lỗi ${res.status}`);
    return data;
  }

  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');

  function toast(msg, kind) {
    const el = document.createElement('div');
    el.className = 'toast' + (kind ? ' toast--' + kind : '');
    el.textContent = msg;
    document.getElementById('toastRoot').appendChild(el);
    setTimeout(() => el.remove(), kind === 'bad' ? 5000 : 2600);
  }

  // openModal({title, body, submitLabel, onSubmit(form) -> truthy de dong, extraFoot, wide, onMount(root)})
  function openModal(o) {
    const root = document.getElementById('modalRoot');
    const wrap = document.createElement('div');
    wrap.className = 'modal-backdrop';
    wrap.innerHTML = `
      <form class="modal ${o.wide ? 'modal--wide' : ''}" novalidate>
        <div class="modal__head"><h2>${esc(o.title)}</h2><button type="button" class="x-btn" data-close aria-label="Đóng">×</button></div>
        <div class="modal__body">${o.body}</div>
        <div class="modal__foot">
          ${o.extraFoot || ''}
          <button type="button" class="btn btn--ghost" data-close>${o.onSubmit ? 'Huỷ' : 'Đóng'}</button>
          ${o.onSubmit ? `<button type="submit" class="btn btn--primary">${esc(o.submitLabel || 'Lưu')}</button>` : ''}
        </div>
      </form>`;
    const form = wrap.querySelector('form');
    const close = () => { wrap.remove(); document.removeEventListener('keydown', onKey); };
    const onKey = (e) => { if (e.key === 'Escape' && root.lastElementChild === wrap) close(); };
    document.addEventListener('keydown', onKey);
    wrap.addEventListener('mousedown', (e) => { if (e.target === wrap) close(); });
    wrap.querySelectorAll('[data-close]').forEach((b) => b.addEventListener('click', close));
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!o.onSubmit) return;
      const btn = form.querySelector('button[type=submit]');
      btn.disabled = true;
      try {
        const done = await o.onSubmit(form);
        if (done !== false) close();
      } catch (err) {
        toast(err.message, 'bad');
      } finally {
        btn.disabled = false;
      }
    });
    root.appendChild(wrap);
    if (o.onMount) o.onMount(form, close);
    const first = form.querySelector('.modal__body input, .modal__body select, .modal__body textarea');
    if (first) first.focus();
    return { el: form, close };
  }

  function confirmBox(message, okLabel) {
    return new Promise((resolve) => {
      let ok = false;
      const m = openModal({
        title: 'Xác nhận',
        body: `<p style="margin:0">${esc(message)}</p>`,
        submitLabel: okLabel || 'Đồng ý',
        onSubmit: () => { ok = true; },
      });
      const obs = new MutationObserver(() => {
        if (!m.el.isConnected) { obs.disconnect(); resolve(ok); }
      });
      obs.observe(document.getElementById('modalRoot'), { childList: true });
    });
  }

  // Doc form: checkbox -> 1/0, input[type=number] -> so.
  function readForm(form) {
    const out = {};
    form.querySelectorAll('[name]').forEach((el) => {
      if (el.type === 'checkbox') out[el.name] = el.checked ? 1 : 0;
      else if (el.type === 'number') out[el.name] = el.value === '' ? '' : Number(el.value);
      else out[el.name] = el.value;
    });
    return out;
  }

  const options = (map, selected, labelOf) => Object.entries(map)
    .map(([k, v]) => `<option value="${esc(k)}" ${String(k) === String(selected) ? 'selected' : ''}>${esc(labelOf ? labelOf(v) : v)}</option>`)
    .join('');

  function money(amount, currency) {
    const n = Number(amount || 0);
    const cur = currency || 'USD';
    try {
      return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: cur, maximumFractionDigits: cur === 'VND' ? 0 : 2 }).format(n);
    } catch (e) {
      return `${n.toLocaleString('vi-VN')} ${cur}`;
    }
  }

  function fmtDate(s) {
    if (!s) return '—';
    const [y, m, d] = s.slice(0, 10).split('-');
    return `${d}/${m}/${y}`;
  }

  const today = () => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  };

  window.TL = { api, esc, toast, openModal, confirmBox, readForm, options, money, fmtDate, today };
})();
