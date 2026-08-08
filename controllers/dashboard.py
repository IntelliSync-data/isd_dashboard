import logging
import threading
import uuid
from datetime import date, timedelta

import odoo
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = """KCLICK PHOTOAPP - AI BUSINESS INTELLIGENCE SYSTEM

ROLE:
Bạn là AI Business Intelligence Advisor của hệ thống KClick PhotoApp.
Bạn KHÔNG phải là AI tạo báo cáo. Bạn là AI cố vấn chiến lược hỗ trợ CEO, CMO, COO, nhà đầu tư và ban điều hành đưa ra quyết định dựa trên dữ liệu thực tế.
Mục tiêu: chuyển dữ liệu thành quyết định kinh doanh.

MCP TOOL STRATEGY:
- get_statistics: tổng doanh thu, thực thu, số giao dịch, doanh thu trung bình, giá trị giao dịch trung bình
- get_group_statistics: chi tiết theo khu vực, máy, nhóm, ngày, tuần, tháng. Nếu cần dữ liệu từng ngày, gọi nhiều lần theo khoảng thời gian nhỏ
- get_apps_status: trạng thái online/offline/lỗi của máy
- KHÔNG dùng get_transactions (raw data quá lớn, dễ vượt giới hạn token)

DASHBOARD STRUCTURE (theo thứ tự):

1. BUSINESS HEALTH SCORE (0-100): AI tự đánh giá dựa trên tăng trưởng, offline, downtime, máy không doanh thu, hiệu suất. Hiển thị Excellent/Good/Warning/Critical. Dưới 70 = cảnh báo đỏ.

2. EXECUTIVE KPI: Tổng doanh thu, thực thu, giao dịch, giá trị TB, tổng máy, online/offline, máy không doanh thu, tỷ lệ offline. Hiển thị tăng/giảm so với kỳ trước nếu có.

3. EXECUTIVE ALERT (tối đa 5): AI tự sinh cảnh báo Critical/High/Medium/Low. VD: Offline vượt 10%, máy không doanh thu, doanh thu giảm, cuối tuần tăng mạnh.

4. BUSINESS GROWTH: WoW/MoM/QoQ/YoY nếu có dữ liệu. Phân tích doanh thu, giao dịch, ticket size. Ẩn section nếu không có dữ liệu lịch sử.

5. MARKET PERFORMANCE: Mỗi khu vực có doanh thu, tăng trưởng, tỷ trọng, hiệu suất, đánh giá. AI phân loại: Expand/Maintain/Improve/Watch/Relocate.

6. MACHINE PERFORMANCE: Máy hoạt động tốt, cần theo dõi, offline, cần bảo trì, không doanh thu, nên di dời. Đề xuất mở thêm máy ở khu vực tốt.

7. CUSTOMER & SALES TREND: Doanh thu theo ngày/tuần/thứ. AI nhận xét xu hướng (VD: cuối tuần cao hơn 35% = đề xuất marketing cuối tuần).

8. PARETO ANALYSIS: 20% máy/khu vực tạo bao nhiêu % doanh thu. Cảnh báo nếu phụ thuộc quá nhiều vào ít điểm bán.

9. MARKETING INSIGHT: AI tự phân tích và đề xuất cụ thể cho từng khu vực (expand, tăng marketing, đổi vị trí, relocate). Đề xuất Event/KOL/Voucher/Promotion nếu phù hợp.

10. OPERATION INSIGHT: Offline, lỗi, downtime, hiệu suất. Máy nào cần kiểm tra trước.

11. ACTION CENTER: Chỉ hiển thị việc cần làm theo Priority 1-5. Không hiển thị số.

12. AI STRATEGY ENGINE: Mỗi đề xuất đánh giá Impact x Effort. High Impact + Low Effort = Làm ngay. Mỗi đề xuất có Priority, Impact, Effort, Expected Result.

13. INVESTMENT OPPORTUNITY: Bảng khuyến nghị cho CEO/nhà đầu tư (mở thêm máy, tăng marketing, đổi vị trí, thu hồi).

14. EXECUTIVE SUMMARY: Kết thúc dashboard, tối đa 200 từ. Tình trạng doanh nghiệp, điểm mạnh/yếu, cơ hội/rủi ro, khuyến nghị. Giống báo cáo cho Hội đồng Quản trị.

RESPONSE FORMAT:
- Chỉ trả về HTML thuần túy, bắt đầu bằng <div class="container-fluid p-0">
- KHÔNG markdown, KHÔNG giải thích text bên ngoài HTML
- Chart.js từ CDN: <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
- Canvas chart PHẢI có id duy nhất
- Số tiền format: 1,234,567 VNĐ
- Inline script PHẢI bọc trong (function(){ ... })(); để tránh conflict biến

UI STYLE (ODOO 18):
- Bootstrap 5, card border, nền trắng, không gradient, không shadow đậm
- KPI: col-12 col-md-6 col-lg-3, card border, fs-2 fw-bold
- Charts: card border, card-header bg-light, canvas không giới hạn max-height, maintainAspectRatio: false, màu pastel
- Bảng: table table-sm table-hover mb-0, thead table-light, không table-striped
- Spacing: mb-3, không emoji trong tiêu đề
- Màu: Primary #714B67, Success #00A09D, Warning #E9A227, Danger #dc3545
- Chart colors: ['#714B67', '#00A09D', '#E9A227', '#2196F3', '#9C27B0', '#FF5722', '#607D8B', '#795548']
- Responsive: Desktop 4 KPI, Tablet 2 KPI, Mobile 1 KPI

Gọi MCP tools phù hợp TRƯỚC để lấy dữ liệu thực, sau đó tạo HTML."""


# ─── Period helpers ───

def _week_range(year, week):
    """Return (start, end) dates for ISO week."""
    jan1 = date(year, 1, 1)
    start = jan1 + timedelta(days=(week - 1) * 7 - jan1.weekday())
    end = start + timedelta(days=6)
    return start, end


def _month_range(year, month):
    """Return (start, end) dates for a month."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def _quarter_range(year, quarter):
    """Return (start, end) dates for a quarter."""
    start_month = (quarter - 1) * 3 + 1
    start = date(year, start_month, 1)
    end_month = start_month + 2
    if end_month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, end_month + 1, 1) - timedelta(days=1)
    return start, end


def _year_range(year):
    return date(year, 1, 1), date(year, 12, 31)


MONTH_NAMES_VI = [
    '', 'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
    'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12',
]


def _parse_period(period_type, period_value):
    """Parse period_value string into (start, end, label).

    period_value formats:
      week:    "2026-W31"
      month:   "2026-08"
      quarter: "2026-Q3"
      year:    "2026"
    """
    if period_type == 'week':
        year, w = period_value.split('-W')
        start, end = _week_range(int(year), int(w))
        label = f'Tuần {w}/{year}'
    elif period_type == 'month':
        year, month = period_value.split('-')
        start, end = _month_range(int(year), int(month))
        label = f'{MONTH_NAMES_VI[int(month)]}/{year}'
    elif period_type == 'quarter':
        year, q = period_value.split('-Q')
        start, end = _quarter_range(int(year), int(q))
        label = f'Quý {q}/{year}'
    elif period_type == 'year':
        year = int(period_value)
        start, end = _year_range(year)
        label = f'Năm {year}'
    else:
        raise ValueError(f'Invalid period_type: {period_type}')

    # Cap end to today
    today = date.today()
    if end > today:
        end = today

    return start, end, label


def _build_revenue_prompt(period_label, date_from, date_to):
    return (
        f'Báo cáo doanh thu {period_label} '
        f'từ {date_from.strftime("%d/%m/%Y")} đến {date_to.strftime("%d/%m/%Y")}. '
        f'Lấy dữ liệu từ ngày {date_from.isoformat()} đến {date_to.isoformat()}. '
        'Hiển thị: tổng doanh thu, tổng thực thu, số giao dịch, '
        'barchart doanh thu theo từng ngày/tuần/tháng (tùy khoảng thời gian), '
        'pie chart theo khu vực, '
        'top 10 máy doanh thu cao nhất (tên máy, khu vực, doanh thu, thực thu, số giao dịch), '
        'bảng chi tiết doanh thu từng khu vực.'
    )


def _build_comparison_prompt(label1, from1, to1, label2, from2, to2):
    return (
        f'So sánh doanh thu giữa {label1} và {label2}. '
        f'Kỳ 1: {label1} từ {from1.strftime("%d/%m/%Y")} đến {to1.strftime("%d/%m/%Y")} '
        f'(lấy dữ liệu {from1.isoformat()} đến {to1.isoformat()}). '
        f'Kỳ 2: {label2} từ {from2.strftime("%d/%m/%Y")} đến {to2.strftime("%d/%m/%Y")} '
        f'(lấy dữ liệu {from2.isoformat()} đến {to2.isoformat()}). '
        'Hiển thị: bảng so sánh KPI (doanh thu, thực thu, giao dịch, giá trị TB), '
        'barchart so sánh doanh thu 2 kỳ theo khu vực, '
        'bảng chi tiết từng khu vực với % tăng/giảm, '
        'nhận xét xu hướng và đề xuất hành động.'
    )


# ─── Background Claude call ───

def _extract_html(text: str) -> str:
    text = text.strip()
    if text.startswith('```html'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()
    idx = text.find('<')
    if idx > 0:
        text = text[idx:]
    return text.strip()


def _call_claude_bg(db_name, task_id, report_id, api_key, claude_model, system_prompt, prompt, mcp_url, mcp_server_name):
    """Background thread: call Anthropic API, store result in DB."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        from datetime import datetime, timezone, timedelta as td
        now_vn = datetime.now(timezone(td(hours=7)))
        date_context = f"Hom nay la {now_vn.strftime('%A, %d/%m/%Y')} (gio VN: {now_vn.strftime('%H:%M')}). "

        create_kwargs = dict(
            model=claude_model,
            max_tokens=48000,
            system=system_prompt,
            messages=[{'role': 'user', 'content': date_context + prompt}],
        )

        if mcp_url:
            _logger.info('ISD Dashboard [%s]: calling Claude with MCP %s', task_id, mcp_url)
            create_kwargs['mcp_servers'] = [{
                'type': 'url',
                'url': mcp_url,
                'name': mcp_server_name,
            }]
            create_kwargs['tools'] = [{
                'type': 'mcp_toolset',
                'mcp_server_name': mcp_server_name,
            }]
            with client.beta.messages.stream(
                betas=['mcp-client-2025-11-20'],
                **create_kwargs,
            ) as stream:
                response = stream.get_final_message()
            html = ''
            for block in response.content:
                if hasattr(block, 'type') and block.type == 'text':
                    html = block.text
        else:
            _logger.info('ISD Dashboard [%s]: calling Claude without MCP', task_id)
            with client.messages.stream(**create_kwargs) as stream:
                response = stream.get_final_message()
            html = ''
            for block in response.content:
                if hasattr(block, 'type') and block.type == 'text':
                    html = block.text

        html = _extract_html(html)

        stop_reason = getattr(response, 'stop_reason', None)
        is_complete = stop_reason == 'end_turn' or html.rstrip().endswith('>')

        _logger.info(
            'ISD Dashboard [%s]: done model=%s in=%s out=%s complete=%s',
            task_id, claude_model,
            getattr(response.usage, 'input_tokens', '?'),
            getattr(response.usage, 'output_tokens', '?'),
            is_complete,
        )

        # Write result to DB
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            # Update task
            cr.execute(
                "UPDATE isd_dashboard_task SET status='done', result_html=%s WHERE task_id=%s",
                (html or '', task_id),
            )
            # Update report record
            if report_id and html and is_complete:
                cr.execute(
                    "UPDATE isd_dashboard_report SET state='done', result_html=%s, prompt_used=%s, write_date=NOW() AT TIME ZONE 'UTC' WHERE id=%s",
                    (html, prompt, report_id),
                )
            elif report_id and not is_complete:
                cr.execute(
                    "UPDATE isd_dashboard_report SET state='error', error_message='Response truncated', write_date=NOW() AT TIME ZONE 'UTC' WHERE id=%s",
                    (report_id,),
                )

    except Exception as e:
        _logger.exception('ISD Dashboard [%s]: error', task_id)
        try:
            registry = odoo.registry(db_name)
            with registry.cursor() as cr:
                cr.execute(
                    "UPDATE isd_dashboard_task SET status='error', error_message=%s WHERE task_id=%s",
                    (str(e), task_id),
                )
                if report_id:
                    cr.execute(
                        "UPDATE isd_dashboard_report SET state='error', error_message=%s, write_date=NOW() AT TIME ZONE 'UTC' WHERE id=%s",
                        (str(e), report_id),
                    )
        except Exception:
            _logger.exception('ISD Dashboard [%s]: failed to write error to DB', task_id)


# ─── Controller ───

class IsdDashboardController(http.Controller):

    def _get_claude_config(self):
        ICP = request.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('isd_dashboard.api_key', '')
        claude_model = ICP.get_param('isd_dashboard.claude_model', 'claude-sonnet-4-6')
        mcp_server_name = ICP.get_param('isd_dashboard.mcp_server_name', 'KClickPhotoApp')
        system_prompt = ICP.get_param('isd_dashboard.system_prompt', _DEFAULT_SYSTEM_PROMPT)
        token_id_str = ICP.get_param('isd_dashboard.mcp_token_id', '')

        mcp_url = None
        if token_id_str and token_id_str.isdigit():
            token = request.env['isd.mcp.photoapp.token'].sudo().browse(int(token_id_str))
            if token.exists() and token.is_active and token.token:
                base_url = ICP.get_param('web.base.url', '')
                mcp_url = f"{base_url}/mcp/photoapp?token={token.token}"

        return api_key, claude_model, system_prompt, mcp_url, mcp_server_name

    def _spawn_claude(self, prompt, report_id=None):
        """Validate config, create task, spawn background thread."""
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return {'error': 'Thu vien anthropic chua duoc cai dat.'}

        api_key, claude_model, system_prompt, mcp_url, mcp_server_name = self._get_claude_config()
        if not api_key:
            return {'error': 'Chua cau hinh Anthropic API Key.'}

        task_id = str(uuid.uuid4())[:8]
        request.env['isd.dashboard.task'].sudo().create({
            'task_id': task_id,
            'status': 'pending',
        })
        request.env.cr.commit()

        db_name = request.env.cr.dbname
        thread = threading.Thread(
            target=_call_claude_bg,
            args=(db_name, task_id, report_id, api_key, claude_model, system_prompt, prompt, mcp_url, mcp_server_name),
            daemon=True,
        )
        thread.start()
        return {'task_id': task_id}

    # ── Period options ──

    @http.route('/isd_dashboard/period_options', type='json', auth='user', methods=['POST'], csrf=False)
    def period_options(self, period_type='month', **kwargs):
        """Return available period options for a given period type."""
        today = date.today()
        options = []

        if period_type == 'week':
            # Last 12 weeks
            for i in range(12):
                d = today - timedelta(weeks=i)
                iso = d.isocalendar()
                value = f'{iso[0]}-W{iso[1]:02d}'
                start, end = _week_range(iso[0], iso[1])
                label = f'Tuần {iso[1]} ({start.strftime("%d/%m")} - {end.strftime("%d/%m/%Y")})'
                options.append({'value': value, 'label': label})

        elif period_type == 'month':
            # Last 12 months
            year, month = today.year, today.month
            for _ in range(12):
                value = f'{year}-{month:02d}'
                label = f'{MONTH_NAMES_VI[month]}/{year}'
                options.append({'value': value, 'label': label})
                month -= 1
                if month == 0:
                    month = 12
                    year -= 1

        elif period_type == 'quarter':
            # Last 8 quarters
            year = today.year
            current_q = (today.month - 1) // 3 + 1
            q, y = current_q, year
            for _ in range(8):
                value = f'{y}-Q{q}'
                label = f'Quý {q}/{y}'
                options.append({'value': value, 'label': label})
                q -= 1
                if q == 0:
                    q = 4
                    y -= 1

        elif period_type == 'year':
            # Last 3 years
            for y in range(today.year, today.year - 3, -1):
                options.append({'value': str(y), 'label': f'Năm {y}'})

        return options

    # ── Submit report ──

    @http.route('/isd_dashboard/submit_report', type='json', auth='user', methods=['POST'], csrf=False)
    def submit_report(self, report_type='revenue', period_type='month', period_value='',
                      compare_period_value='', force_refresh=False, **kwargs):
        """Submit a report request. Returns existing report or spawns Claude."""
        if not period_value:
            return {'error': 'Chưa chọn kỳ báo cáo.'}

        Report = request.env['isd.dashboard.report'].sudo()

        try:
            start, end, label = _parse_period(period_type, period_value)
        except Exception as e:
            return {'error': f'Lỗi kỳ báo cáo: {e}'}

        if report_type == 'revenue':
            # Check existing
            domain = [
                ('report_type', '=', 'revenue'),
                ('period_type', '=', period_type),
                ('period_start', '=', start),
                ('state', '=', 'done'),
            ]
            existing = Report.search(domain, limit=1)

            if existing and not force_refresh:
                return {
                    'status': 'done',
                    'html': existing.result_html,
                    'report_id': existing.id,
                    'from_cache': True,
                    'period_label': label,
                }

            # Delete old if refreshing
            if existing and force_refresh:
                existing.unlink()

            prompt = _build_revenue_prompt(label, start, end)
            report = Report.create({
                'report_type': 'revenue',
                'period_type': period_type,
                'period_start': start,
                'period_end': end,
                'period_label': label,
                'prompt_used': prompt,
                'state': 'generating',
            })
            request.env.cr.commit()

            result = self._spawn_claude(prompt, report_id=report.id)
            result['report_id'] = report.id
            result['period_label'] = label
            return result

        elif report_type == 'comparison':
            if not compare_period_value:
                return {'error': 'Chưa chọn kỳ so sánh.'}

            try:
                start2, end2, label2 = _parse_period(period_type, compare_period_value)
            except Exception as e:
                return {'error': f'Lỗi kỳ so sánh: {e}'}

            # Check existing
            domain = [
                ('report_type', '=', 'comparison'),
                ('period_type', '=', period_type),
                ('period_start', '=', start),
                ('compare_period_start', '=', start2),
                ('state', '=', 'done'),
            ]
            existing = Report.search(domain, limit=1)

            if existing and not force_refresh:
                return {
                    'status': 'done',
                    'html': existing.result_html,
                    'report_id': existing.id,
                    'from_cache': True,
                    'period_label': f'{label} vs {label2}',
                }

            if existing and force_refresh:
                existing.unlink()

            prompt = _build_comparison_prompt(label, start, end, label2, start2, end2)
            report = Report.create({
                'report_type': 'comparison',
                'period_type': period_type,
                'period_start': start,
                'period_end': end,
                'period_label': label,
                'compare_period_start': start2,
                'compare_period_end': end2,
                'compare_period_label': label2,
                'prompt_used': prompt,
                'state': 'generating',
            })
            request.env.cr.commit()

            result = self._spawn_claude(prompt, report_id=report.id)
            result['report_id'] = report.id
            result['period_label'] = f'{label} vs {label2}'
            return result

        return {'error': 'Loại báo cáo không hợp lệ.'}

    # ── Saved reports list ──

    @http.route('/isd_dashboard/saved_reports', type='json', auth='user', methods=['POST'], csrf=False)
    def saved_reports(self, **kwargs):
        """Return list of saved reports for display."""
        reports = request.env['isd.dashboard.report'].sudo().search([
            ('state', '=', 'done'),
        ], order='create_date desc', limit=50)
        return [{
            'id': r.id,
            'report_type': r.report_type,
            'period_type': r.period_type,
            'period_label': r.period_label,
            'compare_period_label': r.compare_period_label or '',
            'create_date': r.create_date.strftime('%d/%m/%Y %H:%M') if r.create_date else '',
        } for r in reports]

    @http.route('/isd_dashboard/view_report', type='json', auth='user', methods=['POST'], csrf=False)
    def view_report(self, report_id=0, **kwargs):
        """Return HTML of a saved report."""
        report = request.env['isd.dashboard.report'].sudo().browse(int(report_id))
        if not report.exists() or report.state != 'done':
            return {'error': 'Báo cáo không tồn tại.'}
        return {'status': 'done', 'html': report.result_html, 'report_id': report.id}

    # ── Poll (unchanged) ──

    @http.route('/isd_dashboard/poll', type='json', auth='user', methods=['POST'], csrf=False)
    def poll(self, task_id='', **kwargs):
        if not task_id:
            return {'error': 'task_id is required'}
        task = request.env['isd.dashboard.task'].sudo().search([
            ('task_id', '=', task_id),
        ], limit=1)
        if not task:
            return {'error': 'Task not found'}
        if task.status == 'pending':
            return {'status': 'pending'}
        result = {'status': task.status}
        if task.status == 'done':
            result['html'] = task.result_html or ''
        elif task.status == 'error':
            result['error'] = task.error_message or 'Unknown error'
        task.unlink()
        return result

    # ── Legacy presets (keep for backward compat) ──

    @http.route('/isd_dashboard/presets', type='json', auth='user', methods=['POST'], csrf=False)
    def presets(self, **kwargs):
        return []

    @http.route('/isd_dashboard/ask_preset', type='json', auth='user', methods=['POST'], csrf=False)
    def ask_preset(self, preset_key='', **kwargs):
        return {'error': 'Deprecated. Use /isd_dashboard/submit_report instead.'}

    @http.route('/isd_dashboard/clear_cache', type='json', auth='user', methods=['POST'], csrf=False)
    def clear_cache(self, preset_key='', **kwargs):
        return {'ok': True}
