# ISD AI Dashboard — Ghi chú triển khai

## Tổng quan kiến trúc

```
User nhập prompt (OWL Component)
    ↓ POST /isd_dashboard/ask (JSON-RPC)
Python Controller (dashboard.py)
    ↓ Anthropic Python SDK
Claude API (claude-sonnet-4-6)
    ↓ gọi MCP tools qua SSE
MCP Server (Odoo /mcp/photoapp/sse)
    ↓ lấy data từ PhotoApp backend
Claude → trả về HTML string
    ↓
Controller → {html: "..."}
    ↓
OWL Component → inject vào iframe
    ↓
User thấy báo cáo có bảng + biểu đồ
```

## Files quan trọng

| File | Mục đích |
|------|----------|
| `models/isd_dashboard_config.py` | Model config: API key, model, MCP token, system prompt |
| `controllers/dashboard.py` | Endpoint `/isd_dashboard/ask` — gọi Anthropic API |
| `static/src/js/dashboard_component.js` | OWL component + iframe injection |
| `static/src/xml/dashboard_component.xml` | OWL template (UI) |
| `views/isd_dashboard_views.xml` | Override `web.action_client_dashboard` → tag `isd_ai_dashboard` |

## Config model (`isd.dashboard.config`)

| Field | Mô tả |
|-------|-------|
| `anthropic_api_key` | API key từ console.anthropic.com (chỉ admin thấy) |
| `claude_model` | Mặc định `claude-sonnet-4-6` |
| `mcp_token_id` | Many2one → `isd.mcp.photoapp.token` |
| `mcp_server_name` | Tên server trong prompt (default: `KClickPhotoApp`) |
| `system_prompt` | Hướng dẫn Claude: chỉ trả HTML, dùng Bootstrap 5, Chart.js |

## Cách hoạt động — Anthropic API với MCP

```python
# controller gọi beta API với mcp_servers
response = client.beta.messages.create(
    betas=["mcp-client-2025-11-20"],
    model="claude-sonnet-4-6",
    max_tokens=8096,
    system=system_prompt,
    messages=[{"role": "user", "content": prompt}],
    mcp_servers=[{
        "type": "url",
        "url": "https://workplace.intellisyncdata.com/mcp/photoapp/sse?token=TOKEN",
        "name": "KClickPhotoApp",
    }],
)
```

**Quan trọng:** Anthropic servers (không phải Odoo server) sẽ gọi MCP URL.
→ URL trong `mcp_token.mcp_url` phải là URL public có thể truy cập từ internet.

## OWL Component — iframe injection

Dùng iframe sandbox thay vì innerHTML vì Claude trả về HTML có `<script>` (Chart.js).
- `innerHTML` KHÔNG execute `<script>` tags
- `<iframe sandbox="allow-scripts allow-same-origin">` + `document.write()` hoạt động đúng
- Auto-resize iframe sau 1s và 2.5s để Chart.js kịp render

## System Prompt thiết kế

Prompt yêu cầu Claude:
1. Gọi MCP tools TRƯỚC để lấy data thực
2. Chỉ trả về HTML (không markdown, không text ngoài HTML)
3. Dùng Bootstrap 5 (đã có sẵn trong Odoo backend)
4. Dùng Chart.js từ CDN
5. Canvas chart phải có unique ID
6. Container `<div class="container-fluid p-3">`

## Timeout

Claude + MCP tools có thể mất 15–60 giây.
- Anthropic SDK timeout: 600s (OK)
- Browser: hiển thị spinner với message "15–60 giây"
- Không cần streaming ở V1

## Cài đặt sau install

1. Vào **Cài đặt > AI Dashboard**
2. Nhập Anthropic API Key
3. Chọn MCP Token (từ module `isd_mcp_photoapp`)
4. Lưu → xong

## Lỗi thường gặp

| Lỗi | Nguyên nhân | Fix |
|-----|-------------|-----|
| `anthropic chưa được cài` | Package chưa install | Xem INSTALL.md |
| `API key không hợp lệ` | Key sai hoặc expired | Vào console.anthropic.com |
| `MCP URL không reach được` | URL nội bộ / Odoo ngừng | Kiểm tra token + URL public |
| Chart không hiện | Canvas ID trùng | System prompt đã handle; nếu vẫn lỗi, clear rồi hỏi lại |
| HTML bị thiếu | Claude trả ```html``` fence | `_strip_markdown_fences()` đã xử lý |
