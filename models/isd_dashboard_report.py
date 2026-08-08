from odoo import fields, models


class IsdDashboardReport(models.Model):
    _name = 'isd.dashboard.report'
    _description = 'Dashboard Report'
    _order = 'create_date desc'

    report_type = fields.Selection([
        ('revenue', 'Báo cáo doanh thu'),
        ('comparison', 'So sánh doanh thu'),
    ], string='Loại báo cáo', required=True, index=True)

    period_type = fields.Selection([
        ('week', 'Tuần'),
        ('month', 'Tháng'),
        ('quarter', 'Quý'),
        ('year', 'Năm'),
    ], string='Loại kỳ', required=True)

    period_start = fields.Date(string='Từ ngày', required=True, index=True)
    period_end = fields.Date(string='Đến ngày', required=True)
    period_label = fields.Char(string='Kỳ báo cáo')

    # For comparison reports
    compare_period_start = fields.Date(string='So sánh từ ngày')
    compare_period_end = fields.Date(string='So sánh đến ngày')
    compare_period_label = fields.Char(string='Kỳ so sánh')

    result_html = fields.Text(string='Kết quả HTML')
    prompt_used = fields.Text(string='Prompt')
    state = fields.Selection([
        ('generating', 'Đang tạo'),
        ('done', 'Hoàn thành'),
        ('error', 'Lỗi'),
    ], string='Trạng thái', default='done', required=True)
    error_message = fields.Text(string='Lỗi')
