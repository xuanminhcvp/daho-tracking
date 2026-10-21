# Task Lead

App desktop quản lý tài khoản ChatGPT cho team. Cùng kiến trúc với NXM DZS1TG:
Flask (server nội bộ 127.0.0.1) + pywebview (cửa sổ app) + HTML/CSS/JS thuần + SQLite.

## Chạy

Bấm đúp `run.command` (lần đầu tự cài môi trường), hoặc:

```bash
.venv/bin/python desktop.py
```

## Dùng

- **Dán tài khoản:** dán các dòng `email|mật khẩu|mã 2FA` rồi bấm Thêm là xong. Có cột tên người dùng bên cạnh (copy 2 cột từ sheet) thì giao luôn, không có thì vào "Chưa phân" để phân sau. Email đã có sẵn thì bỏ qua (không sửa gì). Dòng không có email (VD `1 tk ưu đãi`) vẫn được thêm thành tài khoản "không có email", chữ đó làm tên gọi; khi có tài khoản thật thì mở Sửa điền email vào.
- **Tài khoản:** lọc theo người ở ô "Mọi người"; bấm email/mật khẩu để sao chép, "Lấy mã" ra mã 2FA 6 số (tự sao chép). Đổi người dùng / trạng thái ngay trên bảng, hoặc tích nhiều dòng để giao hàng loạt.
- **Trạng thái:** Hoạt động · Chờ bảo hành · Đã bảo hành · Đã hoàn tiền · Đã xoá. Ghi chú để ghi chi tiết (đổi sang tài khoản nào, báo bảo hành ngày nào…).
- **Thành viên:** số tài khoản từng người theo trạng thái, "Chuyển hết sang…" khi có người nghỉ.
- **Nhật ký:** mọi lần giao, đổi trạng thái, sửa mật khẩu/2FA đều được ghi lại; trang Sửa của từng tài khoản có lịch sử riêng.
- **Copy để gửi nhân sự:** dạng `email|mật khẩu|2FA`, mỗi tài khoản một dòng. Nút Copy ở từng dòng; nút "Copy … tài khoản" trên bảng copy các dòng đã tích, hoặc cả danh sách đang lọc (VD lọc theo một người); tab Thành viên có "Copy N tk" copy các tài khoản đang Hoạt động của người đó.

## Không để mất tài khoản

- Nút "Xoá" chỉ chuyển tài khoản vào mục "Đã xoá" (khôi phục được). Muốn xoá vĩnh viễn (VD dán nhầm) thì vào bộ lọc "Đã xoá" → "Xoá hẳn" (hỏi xác nhận); nhật ký vẫn ghi lại email.
- Xoá thành viên: app bắt chọn người nhận (hoặc Chưa phân) cho mọi tài khoản của họ trước, kể cả tài khoản đã xoá.
- Mỗi lần dữ liệu thay đổi, app tự chép DB ra `backups/tasklead-YYYY-MM-DD.db` (giữ 30 ngày) — nút "Mở thư mục sao lưu" ở sidebar.
- **Chuyển máy:** nút "⇅ Chuyển máy / sao lưu" xuất file `.tlx` (nên đặt mật khẩu — file được mã hoá AES-256-GCM) vào Downloads; máy kia nhập file, xem trước, chọn ghi đè hay giữ bản trên máy. Nhập là gộp thêm, không xoá gì.

Dữ liệu (kể cả mật khẩu, mã 2FA) lưu trên máy tại `data/tasklead.db` khi chạy từ mã nguồn, hoặc `~/Library/Application Support/TaskLead/` với bản đóng gói. Ai mở được máy là xem được — giữ máy có mật khẩu đăng nhập.

## Build bản cài (.app / .dmg)

Bấm đúp `build_app.command` (hoặc chạy trong Terminal). Script chạy test, tạo icon, đóng gói bằng PyInstaller, ký ad-hoc và tạo
`ban-build/TaskLead-v<phiên bản>-<ngày giờ>.dmg`. Muốn ra bản mới thì tăng `VERSION` trong `app/version.py` rồi build lại.
Mở DMG, kéo "Task Lead" vào Applications; lần đầu mở: chuột phải → Open. Dữ liệu bản cài nằm ở
`~/Library/Application Support/TaskLead`, gỡ hay cài lại app không mất dữ liệu.

## Test

```bash
.venv/bin/python -m pytest -q
```
