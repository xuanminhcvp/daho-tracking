// Chuyen may: xuat file .tlx (co the dat mat khau) va nhap file tu may khac (xem truoc, chon ghi de).
(function () {
  const { api, esc, toast, openModal, fmtDate } = window.TL;
  const API = '/api/transfer';
  const COUNT_LABEL = { accounts: 'tài khoản', members: 'thành viên', activity: 'dòng nhật ký' };
  const countText = (c) => Object.entries(COUNT_LABEL).map(([k, v]) => `${c[k] || 0} ${v}`).join(' · ');

  function open() {
    const m = openModal({
      title: 'Chuyển máy / sao lưu',
      wide: true,
      body: `
        <div class="grid-2">
          <div class="card">
            <div class="card__head"><h2>Xuất từ máy này</h2></div>
            <p class="muted small" style="margin-top:0">Tạo file <b>.tlx</b> chứa toàn bộ tài khoản (cả mật khẩu, mã 2FA), thành viên và nhật ký. File lưu vào thư mục Downloads — gửi file này sang máy kia rồi bấm "Nhập".</p>
            <div class="stack" style="gap:10px">
              <label class="field"><span>Mật khẩu file (nên đặt — trong file có mật khẩu tài khoản)</span><input class="input" type="password" data-x="pw" autocomplete="new-password" placeholder="Để trống = không mã hoá"></label>
              <label class="field"><span>Nhập lại mật khẩu</span><input class="input" type="password" data-x="pw2" autocomplete="new-password"></label>
              <div><button type="button" class="btn btn--primary" data-x="export">Xuất file</button></div>
              <div data-x="export-result"></div>
            </div>
          </div>
          <div class="card">
            <div class="card__head"><h2>Nhập từ máy khác</h2></div>
            <p class="muted small" style="margin-top:0">Gộp vào dữ liệu đang có, không xoá gì. Tài khoản trùng email bạn được chọn ghi đè hay giữ bản trên máy này.</p>
            <div class="stack" style="gap:10px">
              <label class="field"><span>File .tlx</span><input class="input" type="file" accept=".tlx" data-x="file"></label>
              <label class="field"><span>Mật khẩu file</span><input class="input" type="password" data-x="ipw" autocomplete="off" placeholder="Nếu file có mật khẩu"></label>
              <div><button type="button" class="btn" data-x="preview">Đọc file</button></div>
            </div>
          </div>
        </div>
        <div data-x="preview-result" style="margin-top:14px"></div>`,
    });
    const $ = (k) => m.el.querySelector(`[data-x="${k}"]`);

    $('export').addEventListener('click', async (e) => {
      const pw = $('pw').value;
      if (pw !== $('pw2').value) { toast('Hai lần nhập mật khẩu không khớp', 'bad'); return; }
      e.target.disabled = true;
      try {
        const r = await api('POST', `${API}/export`, { password: pw });
        $('export-result').innerHTML = `
          <div class="playbook">
            <div class="cell-main">${r.encrypted ? '🔒 ' : ''}${esc(r.name)}</div>
            <div class="cell-sub" style="overflow-wrap:anywhere">${esc(r.path)}</div>
            <div class="cell-sub">${countText(r.counts)}</div>
            ${r.encrypted ? '' : '<div class="cell-sub" style="color:var(--warn)">File không có mật khẩu — ai có file đều đọc được.</div>'}
            <button type="button" class="btn btn--sm" style="margin-top:8px" data-x="reveal">Hiện trong Finder</button>
          </div>`;
        $('reveal').addEventListener('click', () => api('POST', `${API}/reveal`, {}).catch((err) => toast(err.message, 'bad')));
        toast('Đã xuất file', 'ok');
      } catch (err) {
        toast(err.message, 'bad');
      } finally {
        e.target.disabled = false;
      }
    });

    $('preview').addEventListener('click', async (e) => {
      const f = $('file').files[0];
      if (!f) { toast('Chọn file .tlx', 'bad'); return; }
      const fd = new FormData();
      fd.append('file', f);
      fd.append('password', $('ipw').value);
      e.target.disabled = true;
      try {
        const res = await fetch(`${API}/preview`, { method: 'POST', body: fd });
        const r = await res.json();
        if (!res.ok) {
          if (r.need_password) $('ipw').focus();
          throw new Error(r.error || 'Không đọc được file');
        }
        showPreview(r);
      } catch (err) {
        toast(err.message, 'bad');
      } finally {
        e.target.disabled = false;
      }
    });

    function showPreview(r) {
      const dups = r.accounts.filter((a) => a.exists);
      const rows = r.accounts.map((a) => `
        <tr>
          <td><div class="cell-main">${esc(a.email)}</div></td>
          <td>${a.exists ? '<span class="badge badge--warn">Đã có trên máy này</span>' : '<span class="badge badge--ok">Mới</span>'}</td>
          <td class="small">${a.exists ? (a.diff.length ? a.diff.map(esc).join('<br>') : '<span class="muted">giống nhau</span>') : ''}
            ${a.exists ? `<div class="cell-sub">Máy này sửa lúc ${esc(a.local_updated.slice(0, 16))} · file: ${esc((a.incoming_updated || '').slice(0, 16))}</div>` : ''}</td>
          <td>${a.exists ? `<label class="check" style="padding:0"><input type="checkbox" data-ow="${esc(a.key)}" ${a.incoming_updated > a.local_updated ? 'checked' : ''}> Ghi đè</label>` : ''}</td>
        </tr>`).join('');
      $('preview-result').innerHTML = `
        <div class="card">
          <div class="card__head"><h2>Nội dung file</h2><span class="muted small">Xuất lúc ${esc(r.manifest.exported_at)}${r.manifest.machine ? ' từ máy ' + esc(r.manifest.machine) : ''}</span></div>
          <p class="small" style="margin-top:0">${countText(r.counts)}. Thành viên: ${r.members.new} người mới, ${r.members.matched} người đã có (khớp theo email/tên).</p>
          ${r.accounts.length ? `<div class="table-wrap"><table class="table"><thead><tr><th>Tài khoản</th><th></th><th>Khác nhau</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="muted">File không có tài khoản nào.</p>'}
          ${dups.length ? '<p class="muted small">Đã tích sẵn "Ghi đè" cho tài khoản mà bản trong file mới hơn. Bỏ tích = giữ nguyên bản trên máy này.</p>' : ''}
          <div style="display:flex;justify-content:flex-end"><button type="button" class="btn btn--primary" data-x="apply">Nhập vào máy này</button></div>
        </div>`;
      $('apply').addEventListener('click', async (e) => {
        e.target.disabled = true;
        try {
          const overwrite = [...m.el.querySelectorAll('[data-ow]')].filter((x) => x.checked).map((x) => x.dataset.ow);
          const out = await api('POST', `${API}/apply`, { token: r.token, overwrite });
          m.close();
          toast(`Đã nhập: +${out.accounts_added} tài khoản, ghi đè ${out.accounts_updated}, bỏ qua ${out.accounts_skipped}, +${out.members_added} thành viên`, 'ok');
          window.dispatchEvent(new Event('tl:data-changed'));
        } catch (err) {
          toast(err.message, 'bad');
          e.target.disabled = false;
        }
      });
    }
  }

  document.querySelectorAll('[data-open-transfer]').forEach((b) => b.addEventListener('click', open));
  document.querySelectorAll('[data-open-backups]').forEach((b) => b.addEventListener('click', () =>
    api('POST', '/api/backups/open', {}).catch((err) => toast(err.message, 'bad'))));
  window.TL.openTransfer = open;
})();
