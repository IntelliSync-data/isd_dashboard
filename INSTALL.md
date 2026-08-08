# Hướng dẫn cài đặt dependency — ISD AI Dashboard

## 1. Cài Anthropic Python SDK

Module này cần package `anthropic >= 0.40.0` để gọi Claude API với MCP support.

### Cách 1: Cài vào virtualenv của Odoo (khuyến nghị)

```bash
# Kích hoạt virtualenv của Odoo
source /path/to/odoo/venv/bin/activate

# Cài anthropic
pip install "anthropic>=0.40.0"

# Kiểm tra
pip show anthropic
```

### Cách 2: Cài trực tiếp vào Python system (nếu Odoo chạy không có venv)

```bash
pip3 install "anthropic>=0.40.0"
# hoặc
pip3 install --upgrade anthropic
```

### Cách 3: Dùng requirements.txt của Odoo

Thêm vào file `requirements.txt` của project Odoo:

```
anthropic>=0.40.0
```

Rồi chạy:
```bash
pip install -r requirements.txt
```

## 2. Lấy Anthropic API Key

1. Vào [console.anthropic.com](https://console.anthropic.com)
2. Đăng nhập → **API Keys** → **Create Key**
3. Copy key (dạng `sk-ant-api03-...`)
4. Key chỉ hiện 1 lần, lưu lại ngay

## 3. Restart Odoo sau khi cài

```bash
# Nếu dùng service
sudo systemctl restart odoo

# Nếu chạy tay
python odoo-bin -c odoo.conf --dev=all
```

## 4. Cài đặt module trong Odoo

1. Vào **Settings > Apps > Update Apps List**
2. Tìm **ISD AI Dashboard**
3. Nhấn **Install**

## 5. Cấu hình sau install

1. Vào **Cài đặt > AI Dashboard** (menu xuất hiện khi là admin)
2. Điền:
   - **Anthropic API Key**: key vừa lấy ở bước 2
   - **Claude Model**: `claude-sonnet-4-6` (mặc định)
   - **MCP Token**: chọn token đang active từ module `isd_mcp_photoapp`
   - **Tên MCP Server**: `KClickPhotoApp` (mặc định)
3. **Lưu**

## 6. Kiểm tra

Vào **My Dashboard** (trang chủ Odoo), nhập câu hỏi:

> Báo cáo doanh thu tháng này

→ Nếu thấy HTML với bảng và biểu đồ = thành công ✅

## Yêu cầu phiên bản

| Package | Phiên bản tối thiểu | Lý do |
|---------|---------------------|-------|
| `anthropic` | `0.40.0` | Hỗ trợ `mcp_servers` trong `beta.messages.create()` |
| Odoo | `18.0` | OWL 2, `registry.category("actions")` |
| Python | `3.10+` | Type hints |

## Lưu ý về MCP URL

Anthropic servers (từ US/EU) sẽ gọi MCP URL. URL phải:
- Là domain public (không phải `localhost` hay IP nội bộ)
- HTTPS
- Ví dụ: `https://workplace.intellisyncdata.com/mcp/photoapp/sse?token=...`

Kiểm tra `web.base.url` trong Odoo:
**Settings > Technical > Parameters > System Parameters** → `web.base.url`
Phải là URL public, không phải `http://localhost:8069`.
