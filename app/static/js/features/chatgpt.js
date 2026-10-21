// Module: Tai khoan ChatGPT — tai khoan, thanh vien, nhat ky.
(function () {
  const { api, esc, toast, openModal, confirmBox, readForm, options, fmtDate, today } = window.TL;
  const root = document.getElementById('mod-chatgpt');
  const API = '/api/gpt';
  const S = {
    tab: 'accounts', status: {}, accounts: [], members: [],
    filter: { q: '', view: 'live', member: '' }, selected: new Set(), logQ: '',
  };
  const badge = (text, tone) => `<span class="badge ${tone ? 'badge--' + tone : ''}">${esc(text)}</span>`;
  const empty = (msg) => `<div class="empty">${esc(msg)}</div>`;

  // ---------- sao chep ----------
  async function copy(text, label) {
    try {
      await navigator.clipboard.writeText(text);
    } catch (e) {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    toast(`Đã sao chép ${label || ''}`.trim(), 'ok');
  }

  // ---------- tai du lieu ----------
  async function loadAll() {
    const [accounts, members] = await Promise.all([api('GET', `${API}/accounts`), api('GET', `${API}/members`)]);
    S.accounts = accounts;
    S.members = members;
    const ids = new Set(accounts.map((a) => a.id));
    S.selected.forEach((id) => { if (!ids.has(id)) S.selected.delete(id); });
    root.querySelector('[data-count=accounts]').textContent = accounts.filter((a) => a.status !== 'deleted').length || '';
    root.querySelector('[data-count=members]').textContent = members.filter((m) => m.active).length || '';
    render();
  }
  const refresh = () => loadAll().catch((e) => toast(e.message, 'bad'));

  function render() {
    const panel = root.querySelector(`[data-panel=${S.tab}]`);
    if (S.tab === 'accounts') panel.innerHTML = accountsTab();
    else if (S.tab === 'members') panel.innerHTML = membersTab();
    else renderActivity(panel);
  }

  // ---------- tai khoan ----------
  const VIEWS = () => [
    ['live', 'Tất cả', (a) => a.status !== 'deleted'],
    ['active', S.status.active, (a) => a.status === 'active'],
    ['unassigned', 'Chưa phân', (a) => a.status !== 'deleted' && !a.member_id],
    ['pending', S.status.pending, (a) => a.status === 'pending'],
    ['warrantied', S.status.warrantied, (a) => a.status === 'warrantied'],
    ['refunded', S.status.refunded, (a) => a.status === 'refunded'],
    ['deleted', S.status.deleted, (a) => a.status === 'deleted'],
  ];

  function filtered() {
    const f = S.filter;
    const view = VIEWS().find((v) => v[0] === f.view)[2];
    const q = f.q.toLowerCase();
    return S.accounts.filter((a) => view(a) &&
      (!f.member || String(a.member_id || '') === f.member) &&
      (!q || [a.email, a.member_name, a.note, a.supplier].join(' ').toLowerCase().includes(q)));
  }

  const memberOptions = (selected, emptyLabel, excludeId) => `<option value="">${esc(emptyLabel || '— Chưa phân —')}</option>` +
    S.members.filter((m) => (m.active || m.id === selected) && m.id !== excludeId)
      .map((m) => `<option value="${m.id}" ${m.id === selected ? 'selected' : ''}>${esc(m.name)}${m.active ? '' : ' (đã ngưng)'}</option>`).join('');

  function accountsTab() {
    const f = S.filter;
    const list = filtered();
    const chips = VIEWS().map(([k, label, fn]) => {
      const n = S.accounts.filter(fn).length;
      return `<button class="btn btn--sm ${f.view === k ? 'btn--primary' : ''}" data-view="${k}">${esc(label)} <b>${n}</b></button>`;
    }).join('');
    const sel = S.selected.size;
    const allOn = list.length && list.every((a) => S.selected.has(a.id));
    const rows = list.map((a) => `
      <tr class="${a.status === 'deleted' ? 'is-faded' : ''}">
        <td><input type="checkbox" data-sel="${a.id}" ${S.selected.has(a.id) ? 'checked' : ''}></td>
        <td>${a.email ? `<button class="copy-cell cell-main" data-copy="email" data-id="${a.id}" title="Bấm để sao chép">${esc(a.email)}</button>
          ${a.note ? `<div class="cell-sub">${esc(a.note)}</div>` : ''}` : `<span class="cell-main">${esc(a.note || '(không tên)')}</span> ${badge('không có email')}`}</td>
        <td>${a.password ? `<button class="copy-cell mono" data-copy="password" data-id="${a.id}" title="Bấm để sao chép">••••••••</button>` : '<span class="muted">—</span>'}</td>
        <td>${a.totp_secret ? (a.totp_ok ? `<button class="btn btn--sm" data-totp="${a.id}">Lấy mã</button>` : badge('mã lỗi', 'bad')) : '<span class="muted">—</span>'}</td>
        <td><select class="input input--inline" data-set-member="${a.id}">${memberOptions(a.member_id)}</select></td>
        <td><select class="input input--inline status--${a.status}" data-set-status="${a.id}">${options(S.status, a.status)}</select></td>
        <td><input class="input input--inline input--date" type="date" data-set-date="${a.id}" value="${esc(a.bought_at)}">${a.supplier ? `<div class="cell-sub">${esc(a.supplier)}</div>` : ''}</td>
        <td class="actions">${a.email ? `<button class="btn btn--sm" data-copy-line="${a.id}" title="Copy email|mật khẩu|2FA">Copy</button>` : ''}
          <button class="btn btn--sm btn--ghost" data-edit="${a.id}">Sửa</button>
          ${a.status === 'deleted'
    ? `<button class="btn btn--sm" data-restore="${a.id}">Khôi phục</button><button class="btn btn--sm btn--danger" data-purge="${a.id}">Xoá hẳn</button>`
    : `<button class="btn btn--sm btn--ghost btn--danger" data-soft-del="${a.id}" title="Chuyển vào mục Đã xoá (khôi phục được)">Xoá</button>`}</td>
      </tr>`).join('');
    return `
      <div class="toolbar">${chips}</div>
      <div class="toolbar">
        <input class="input grow" placeholder="Tìm email, người dùng, ghi chú…" data-filter="q" value="${esc(f.q)}">
        <select class="input" data-filter="member"><option value="">Mọi người</option>${S.members.map((m) => `<option value="${m.id}" ${String(m.id) === f.member ? 'selected' : ''}>${esc(m.name)}</option>`).join('')}</select>
        <button class="btn" data-act="copy-list" title="Copy dạng email|mật khẩu|2FA, mỗi tài khoản một dòng — để gửi cho nhân sự">Copy ${sel ? `${sel} đã chọn` : `${list.filter((a) => a.email).length} tài khoản đang lọc`}</button>
      </div>
      ${sel ? `<div class="bulkbar">
        <b>Đã chọn ${sel}</b>
        <select class="input" data-bulk-member>${memberOptions(null, '— Giao cho… —')}<option value="__none">(Thu hồi về chưa phân)</option></select>
        <select class="input" data-bulk-status><option value="">— Đổi trạng thái… —</option>${options(S.status, '')}</select>
        <button class="btn btn--primary btn--sm" data-act="bulk-apply">Áp dụng</button>
        <button class="btn btn--danger btn--sm" data-act="bulk-delete">Xoá ${sel}</button>
        <button class="btn btn--ghost btn--sm" data-act="bulk-clear">Bỏ chọn</button>
      </div>` : ''}
      <div class="card table-wrap">${list.length ? `
        <table class="table"><thead><tr>
          <th><input type="checkbox" data-sel-all ${allOn ? 'checked' : ''}></th><th>Email</th><th>Mật khẩu</th><th>2FA</th><th>Người dùng</th><th>Trạng thái</th><th>Ngày</th><th></th>
        </tr></thead><tbody>${rows}</tbody></table>` : empty(S.accounts.length ? 'Không có tài khoản nào khớp' : 'Chưa có tài khoản — bấm "Dán tài khoản" để thêm')}
      </div>`;
  }

  async function setAccount(id, data, okMsg) {
    try {
      await api('PUT', `${API}/accounts/${id}`, data);
      if (okMsg) toast(okMsg, 'ok');
    } catch (e) {
      toast(e.message, 'bad');
    }
    refresh();
  }

  async function showTotp(btn, id) {
    try {
      const r = await api('GET', `${API}/accounts/${id}/totp`);
      copy(r.code, 'mã 2FA');
      let left = r.seconds_left;
      const show = () => { btn.innerHTML = `<span class="mono">${r.code.slice(0, 3)} ${r.code.slice(3)}</span> <span class="muted">${left}s</span>`; };
      show();
      clearInterval(btn._t);
      btn._t = setInterval(() => {
        left -= 1;
        if (left <= 0 || !btn.isConnected) { clearInterval(btn._t); btn.textContent = 'Lấy mã'; return; }
        show();
      }, 1000);
    } catch (e) {
      toast(e.message, 'bad');
    }
  }

  // dinh dang gui nhan su: email|mat khau|2FA, moi tai khoan mot dong (giong luc dan vao)
  const accountLine = (a) => [a.email, a.password, a.totp_secret].join('|').replace(/\|+$/, '');

  function copyAccounts(list, who) {
    const withEmail = list.filter((a) => a.email);
    if (!withEmail.length) return toast('Không có tài khoản nào có email để copy', 'bad');
    const skipped = list.length - withEmail.length;
    return copy(withEmail.map(accountLine).join('\n'),
      `${withEmail.length} tài khoản${who ? ' của ' + who : ''}${skipped ? ` (bỏ qua ${skipped} cái không có email)` : ''}`);
  }

  function accountForm(a) {
    a = a || { status: 'active', bought_at: today() };
    return `<div class="form-grid">
      <label class="field full"><span>Email</span><input class="input" name="email" value="${esc(a.email || '')}" placeholder="Để trống nếu chưa có tài khoản cụ thể (VD: 1 tk ưu đãi) — ghi vào Ghi chú"></label>
      <label class="field"><span>Mật khẩu</span><input class="input mono" name="password" value="${esc(a.password || '')}"></label>
      <label class="field"><span>Mã 2FA (secret)</span><input class="input mono" name="totp_secret" value="${esc(a.totp_secret || '')}"></label>
      <label class="field"><span>Người dùng</span><select class="input" name="member_id">${memberOptions(a.member_id)}</select></label>
      <label class="field"><span>Trạng thái</span><select class="input" name="status">${options(S.status, a.status)}</select></label>
      <label class="field"><span>Nguồn / bên bán</span><input class="input" name="supplier" value="${esc(a.supplier || '')}"></label>
      <label class="field"><span>Ngày</span><input class="input" type="date" name="bought_at" value="${esc(a.bought_at || '')}"></label>
      <label class="field full"><span>Ghi chú</span><textarea class="input" name="note" placeholder="VD: đã báo bảo hành ngày 20/10, được đổi sang tài khoản …">${esc(a.note || '')}</textarea></label>
    </div>`;
  }

  async function openAccount(a) {
    const log = a ? await api('GET', `${API}/accounts/${a.id}/log`) : [];
    openModal({
      title: a ? (a.email || a.note || 'Tài khoản không có email') : 'Thêm 1 tài khoản',
      wide: !!a,
      body: accountForm(a) + (a ? `
        <h3 class="section-title">Lịch sử</h3>
        <div class="timeline">${log.map((x) => `<div class="timeline__item"><div class="timeline__at">${esc(x.at)}</div>${esc(x.message)}</div>`).join('') || '<div class="muted small">Chưa có</div>'}</div>` : ''),
      onSubmit: async (form) => {
        const d = readForm(form);
        if (a) await api('PUT', `${API}/accounts/${a.id}`, d);
        else await api('POST', `${API}/accounts`, d);
        toast(a ? 'Đã lưu' : 'Đã thêm', 'ok');
        await refresh();
      },
    });
  }

  // ---------- dan tu sheet ----------
  function openImport() {
    const m = openModal({
      title: 'Dán tài khoản',
      wide: true,
      body: `
        <p class="muted" style="margin-top:0">Mỗi dòng một tài khoản: <span class="mono">email|mật khẩu|mã 2FA</span>. Dòng không có email (VD <span class="mono">1 tk ưu đãi</span>) vẫn được thêm, chữ đó làm tên gọi. Có cột tên người dùng bên cạnh thì bỏ tích ô dưới để giao luôn.</p>
        <textarea class="input mono" name="text" rows="12" placeholder="abc@gmail.com|matkhau|MA2FA"></textarea>
        <div class="toolbar" style="margin:10px 0 0">
          <label class="check" style="padding:0"><input type="checkbox" name="ignore_members" checked> Bỏ qua tên, thêm hết vào Chưa phân</label>
          <span class="spacer"></span>
          <label class="field" style="flex-direction:row;align-items:center;gap:6px"><span>Ngày</span><input class="input" type="date" name="bought_at" value="${today()}" style="width:auto"></label>
          <input class="input" name="supplier" placeholder="Nguồn / bên bán (tuỳ chọn)" style="max-width:220px">
        </div>
        <div data-x="result"></div>`,
      submitLabel: 'Thêm',
      onSubmit: async (form) => {
        const d = readForm(form);
        if (!d.text.trim()) throw new Error('Dán danh sách vào ô trên');
        const r = await api('POST', `${API}/import`, d);
        await refresh();
        const notes = [];
        if (r.existing.length) notes.push(`<b>${r.existing.length}</b> email đã có sẵn — bỏ qua, không sửa gì: <span class="mono small">${r.existing.map(esc).join(', ')}</span>`);
        if (r.duplicate.length) notes.push(`<b>${r.duplicate.length}</b> dòng bị lặp trong danh sách dán — chỉ thêm 1 lần`);
        if (r.bad_2fa.length) notes.push(`<b>${r.bad_2fa.length}</b> tài khoản có mã 2FA sai định dạng: <span class="mono small">${r.bad_2fa.map(esc).join(', ')}</span>`);
        if (r.invalid_lines.length) notes.push(`<b style="color:var(--bad)">${r.invalid_lines.length} dòng có dấu | nhưng email sai, chưa thêm</b> — sửa lại rồi dán lại:<br>${r.invalid_lines.map((x) => `<span class="mono small">${esc(x)}</span>`).join('<br>')}`);
        toast(`Đã thêm ${r.added} tài khoản`, 'ok');
        if (!notes.length) return true;
        // co dong can xem lai: giu hop thoai mo de hien ket qua
        form.querySelector('[name=text]').value = '';
        form.querySelector('[data-x=result]').innerHTML = `<div class="playbook" style="margin-top:12px">Đã thêm <b>${r.added}</b> tài khoản.<br>${notes.join('<br>')}</div>`;
        return false;
      },
    });
    m.el.querySelector('[name=text]').focus();
  }

  // ---------- thanh vien ----------
  function membersTab() {
    const rows = S.members.map((m) => {
      const c = m.count;
      const live = Object.entries(c).filter(([k]) => k !== 'deleted').reduce((s, [, v]) => s + v, 0);
      return `<tr class="${m.active ? '' : 'is-faded'}">
        <td class="cell-main">${esc(m.name)}${m.active ? '' : ' ' + badge('đã ngưng')}${m.note ? `<div class="cell-sub">${esc(m.note)}</div>` : ''}</td>
        <td class="num">${c.active || 0}</td><td class="num">${c.pending || 0}</td>
        <td class="num">${(c.warrantied || 0) + (c.refunded || 0)}</td><td class="num">${c.deleted || 0}</td>
        <td class="actions">
          ${c.active ? `<button class="btn btn--sm" data-copy-member="${m.id}" title="Copy các tài khoản đang Hoạt động của ${esc(m.name)}">Copy ${c.active} tk</button>` : ''}
          <button class="btn btn--sm" data-view-member="${m.id}">Xem tài khoản</button>
          ${live ? `<button class="btn btn--sm" data-move="${m.id}">Chuyển hết sang…</button>` : ''}
          <button class="btn btn--sm btn--ghost" data-edit-member="${m.id}">Sửa</button>
        </td></tr>`;
    }).join('');
    return `
      <div class="toolbar"><span class="spacer"></span><button class="btn btn--primary" data-act="new-member">＋ Thêm thành viên</button></div>
      <div class="card table-wrap">${S.members.length ? `<table class="table"><thead><tr><th>Tên</th><th class="num">Hoạt động</th><th class="num">Chờ BH</th><th class="num">Đã BH / hoàn tiền</th><th class="num">Đã xoá</th><th></th></tr></thead><tbody>${rows}</tbody></table>` : empty('Chưa có thành viên — dán tài khoản kèm tên là tự có')}</div>`;
  }

  function openMember(m) {
    openModal({
      title: m ? 'Sửa thành viên' : 'Thêm thành viên',
      body: `<div class="form-grid">
        <label class="field full"><span>Tên *</span><input class="input" name="name" value="${esc(m ? m.name : '')}"></label>
        <label class="field full"><span>Ghi chú</span><input class="input" name="note" value="${esc(m ? m.note : '')}"></label>
        <label class="check full"><input type="checkbox" name="active" ${!m || m.active ? 'checked' : ''}> Đang làm (bỏ tích = ngưng, tài khoản vẫn giữ nguyên)</label>
      </div>`,
      extraFoot: m ? '<button type="button" class="btn btn--danger left" data-del>Xoá</button>' : '',
      onSubmit: async (form) => {
        const d = readForm(form);
        if (m) await api('PUT', `${API}/members/${m.id}`, d);
        else await api('POST', `${API}/members`, d);
        toast('Đã lưu', 'ok');
        await refresh();
      },
      onMount: (form, close) => {
        const del = form.querySelector('[data-del]');
        if (del) del.addEventListener('click', async () => {
          const n = Object.values(m.count).reduce((s, v) => s + v, 0);
          if (!n) {
            if (!(await confirmBox(`Xoá thành viên ${m.name}?`, 'Xoá'))) return;
            try {
              await api('DELETE', `${API}/members/${m.id}`, {});
              close(); toast('Đã xoá'); refresh();
            } catch (e) { toast(e.message, 'bad'); }
            return;
          }
          close();
          openModal({
            title: `Xoá thành viên ${m.name}`,
            body: `<p style="margin-top:0">${esc(m.name)} đang có <b>${n}</b> tài khoản (tính cả tài khoản đã xoá). Chuyển các tài khoản này sang:</p>
              <select class="input" name="move_to">${memberOptions(null, '— Chưa phân —', m.id)}</select>
              <p class="muted small">Tài khoản không bị mất; nhật ký vẫn ghi ${esc(m.name)} từng cầm.</p>`,
            submitLabel: 'Chuyển & xoá',
            onSubmit: async (f2) => {
              const r = await api('DELETE', `${API}/members/${m.id}`, readForm(f2));
              toast(`Đã xoá ${m.name}, chuyển ${r.moved} tài khoản`, 'ok');
              await refresh();
            },
          });
        });
      },
    });
  }

  function openMove(m) {
    openModal({
      title: `Chuyển tài khoản của ${m.name}`,
      body: `<p class="muted" style="margin-top:0">Chuyển mọi tài khoản (trừ tài khoản đã xoá) đang ở ${esc(m.name)} sang:</p>
        <select class="input" name="to_member_id">${memberOptions(null, '— Chưa phân (thu hồi) —', m.id)}</select>`,
      submitLabel: 'Chuyển',
      onSubmit: async (form) => {
        const r = await api('POST', `${API}/members/${m.id}/move`, readForm(form));
        toast(`Đã chuyển ${r.count} tài khoản`, 'ok');
        await refresh();
      },
    });
  }

  // ---------- nhat ky ----------
  async function renderActivity(panel) {
    const rows = await api('GET', `${API}/activity?q=${encodeURIComponent(S.logQ)}`);
    panel.innerHTML = `
      <div class="toolbar"><input class="input grow" placeholder="Tìm trong nhật ký (email, tên…) rồi Enter" data-log-q value="${esc(S.logQ)}"></div>
      <div class="card">${rows.length ? rows.map((x) => `<div class="log-line"><span class="log-line__at">${esc(x.at)}</span><span>${esc(x.message)}</span></div>`).join('') : empty('Chưa có gì')}</div>`;
    const inp = panel.querySelector('[data-log-q]');
    inp.addEventListener('change', () => { S.logQ = inp.value; render(); });
  }

  // ---------- su kien ----------
  root.addEventListener('click', async (e) => {
    const t = e.target.closest('button, input[type=checkbox]');
    if (!t || !root.contains(t)) return;
    const ds = t.dataset;
    const acc = (id) => S.accounts.find((a) => a.id === +id);
    if (ds.tab) {
      S.tab = ds.tab;
      root.querySelectorAll('.tab').forEach((b) => b.classList.toggle('is-active', b === t));
      root.querySelectorAll('.panel').forEach((p) => { p.hidden = p.dataset.panel !== S.tab; });
      return render();
    }
    if (ds.view) { S.filter.view = ds.view; return render(); }
    if (ds.sel) { if (t.checked) S.selected.add(+ds.sel); else S.selected.delete(+ds.sel); return render(); }
    if ('selAll' in ds) {
      const list = filtered();
      list.forEach((a) => (t.checked ? S.selected.add(a.id) : S.selected.delete(a.id)));
      return render();
    }
    if (ds.copyLine) return copy(accountLine(acc(ds.copyLine)), 'tài khoản');
    if (ds.copyMember) {
      const m = S.members.find((x) => x.id === +ds.copyMember);
      return copyAccounts(S.accounts.filter((a) => a.member_id === m.id && a.status === 'active'), m.name);
    }
    if (ds.copy) return copy(acc(ds.id)[ds.copy], ds.copy === 'email' ? 'email' : 'mật khẩu');
    if (ds.totp) return showTotp(t, +ds.totp);
    if (ds.edit) return openAccount(acc(ds.edit));
    if (ds.softDel) {
      const a = acc(ds.softDel);
      return setAccount(a.id, { status: 'deleted' }, `Đã chuyển ${a.email || a.note} vào mục Đã xoá`);
    }
    if (ds.restore) return setAccount(+ds.restore, { status: 'active' }, 'Đã khôi phục (Hoạt động)');
    if (ds.purge) {
      const a = acc(ds.purge);
      if (!(await confirmBox(`Xoá hẳn ${a.email || a.note}? Không khôi phục lại được (nhật ký vẫn ghi lại email).`, 'Xoá hẳn'))) return;
      try {
        await api('DELETE', `${API}/accounts/${a.id}`);
        toast('Đã xoá hẳn');
      } catch (err) { toast(err.message, 'bad'); }
      return refresh();
    }
    if (ds.editMember) return openMember(S.members.find((m) => m.id === +ds.editMember));
    if (ds.move) return openMove(S.members.find((m) => m.id === +ds.move));
    if (ds.viewMember) {
      S.filter = { q: '', view: 'live', member: ds.viewMember };
      return root.querySelector('[data-tab=accounts]').click();
    }
    const act = ds.act;
    if (act === 'new-account') return openAccount(null);
    if (act === 'import') return openImport();
    if (act === 'new-member') return openMember(null);
    if (act === 'copy-list') {
      const list = S.selected.size ? S.accounts.filter((a) => S.selected.has(a.id)) : filtered();
      const m = S.members.find((x) => String(x.id) === S.filter.member);
      return copyAccounts(list, !S.selected.size && m ? m.name : '');
    }
    if (act === 'bulk-clear') { S.selected.clear(); return render(); }
    if (act === 'bulk-delete') {
      const ids = [...S.selected];
      if (!(await confirmBox(`Chuyển ${ids.length} tài khoản vào mục Đã xoá? (khôi phục được)`, 'Xoá'))) return;
      try {
        await api('POST', `${API}/accounts/bulk`, { ids, status: 'deleted' });
        toast(`Đã chuyển ${ids.length} tài khoản vào mục Đã xoá`, 'ok');
        S.selected.clear();
      } catch (err) { toast(err.message, 'bad'); }
      return refresh();
    }
    if (act === 'bulk-apply') {
      const mem = root.querySelector('[data-bulk-member]').value;
      const st = root.querySelector('[data-bulk-status]').value;
      if (!mem && !st) return toast('Chọn người nhận hoặc trạng thái', 'bad');
      const body = { ids: [...S.selected] };
      if (mem) body.member_id = mem === '__none' ? null : mem;
      if (st) body.status = st;
      try {
        const r = await api('POST', `${API}/accounts/bulk`, body);
        toast(`Đã cập nhật ${r.count} tài khoản`, 'ok');
        S.selected.clear();
      } catch (err) { toast(err.message, 'bad'); }
      return refresh();
    }
  });

  root.addEventListener('change', (e) => {
    const ds = e.target.dataset;
    if (ds.setMember) {
      const name = e.target.selectedOptions[0].textContent;
      return setAccount(+ds.setMember, { member_id: e.target.value || null }, e.target.value ? `Đã giao cho ${name}` : 'Đã thu hồi');
    }
    if (ds.setStatus) return setAccount(+ds.setStatus, { status: e.target.value }, `Đã đổi: ${S.status[e.target.value]}`);
    if (ds.setDate) return setAccount(+ds.setDate, { bought_at: e.target.value }, `Đã đổi ngày: ${fmtDate(e.target.value)}`);
    if (ds.filter === 'member') { S.filter.member = e.target.value; render(); }
  });

  // o tim kiem: ve lai bang nhung giu con tro trong o nhap
  root.addEventListener('input', (e) => {
    if (e.target.dataset.filter !== 'q') return;
    S.filter.q = e.target.value;
    const pos = e.target.selectionStart;
    render();
    const el = root.querySelector('[data-filter=q]');
    el.focus();
    el.setSelectionRange(pos, pos);
  });

  window.addEventListener('tl:data-changed', refresh);

  (async function init() {
    try {
      S.status = (await api('GET', `${API}/meta`)).status;
      await loadAll();
    } catch (e) {
      root.querySelector('[data-panel=accounts]').innerHTML = `<div class="card">${empty('Không tải được dữ liệu: ' + e.message)}</div>`;
    }
  })();
})();
