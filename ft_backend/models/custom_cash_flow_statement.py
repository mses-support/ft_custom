from odoo import api, fields, models
from odoo.addons.base_accounting_kit.wizard.xlsx_mixin import ReportXlsxMixin
from odoo.exceptions import ValidationError


class CustomCashFlowStatement(models.TransientModel, ReportXlsxMixin):
    _name = 'ft.custom.cash.flow.statement'
    _description = 'Custom Cash Flow Statement'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    target_move = fields.Selection(
        [('posted', 'All Posted Entries'), ('all', 'All Entries')],
        string='Target Moves',
        required=True,
        default='posted',
    )
    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals',
        required=True,
        domain="[('company_id', '=', company_id)]",
        default=lambda self: self.env['account.journal'].search([('company_id', '=', self.env.company.id)]),
    )
    analytic_plan_ids = fields.Many2many('account.analytic.plan', string='Analytic Plans')
    analytic_account_ids = fields.Many2many('account.analytic.account', string='Analytic Accounts')
    cash_flow_mode = fields.Selection(
        [('single', 'Standard'), ('three_year', '3-Year'), ('twelve_month', '12-Month')],
        string='Report Mode',
        default='single',
        required=True,
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError('Date From must be before or equal to Date To.')

    def _form_data(self):
        self.ensure_one()
        return self.read([
            'company_id', 'date_from', 'date_to', 'target_move', 'journal_ids',
            'analytic_plan_ids', 'analytic_account_ids', 'cash_flow_mode'
        ])[0]

    def action_print(self):
        data = {'form': self._form_data()}
        return self.env.ref('ft_backend.action_report_custom_cash_flow_statement').report_action(self, data=data)

    def action_view(self):
        data = {'form': self._form_data()}
        action = self.env.ref('ft_backend.action_report_custom_cash_flow_statement_html', raise_if_not_found=False)
        if not action:
            action = self.env.ref('ft_backend.action_report_custom_cash_flow_statement')
        return action.report_action(self, data=data)

    def check_report_xlsx(self):
        self.ensure_one()
        form = self._form_data()
        report_model = self.env['report.ft_backend.report_custom_cash_flow_statement']
        mode = form.get('cash_flow_mode') or 'single'
        if mode == 'single':
            prepared = report_model._prepare_statement(form)
            options = {
                'mode': mode,
                'company_name': prepared['company'].name or '',
                'company_logo': prepared['company'].logo,
                'date_to_text': prepared['date_to_text'],
                'opening_cash': prepared['opening_cash'],
                'closing_cash': prepared['closing_cash'],
                'mapped': prepared['mapped'],
            }
        else:
            prepared = report_model._prepare_multi_period_statement(form, mode)
            options = {
                'mode': mode,
                'company_name': prepared['company'].name or '',
                'company_logo': prepared['company'].logo,
                'period_labels': prepared['period_labels'],
                'opening_cash': prepared['opening_cash'],
                'closing_cash': prepared['closing_cash'],
                'rows': prepared['rows'],
            }
        return self._xlsx_action('ft.custom.cash.flow.statement', 'Cash Flow Statement (Custom)', options)

    def get_xlsx_report(self, data, response):
        if data.get('mode') in ('three_year', 'twelve_month'):
            headers = ['Particulars'] + (data.get('period_labels') or [])
            rows = []
            rows.append({'type': 'section', 'values': ['Cash at Beginning'] + [float(v or 0.0) for v in (data.get('opening_cash') or [])]})
            rows.extend(data.get('rows') or [])
            rows.append({'type': 'section', 'values': ['Cash at End'] + [float(v or 0.0) for v in (data.get('closing_cash') or [])]})
            table = {
                'sheet_name': 'Cash Flow Multi',
                'title': f"{data.get('company_name', '')}: Cash Flow Statement",
                'company_logo': data.get('company_logo'),
                'meta': [],
                'headers': headers,
                'column_widths': [(0, 0, 50)] + [(i, i, 14) for i in range(1, len(headers))],
                'rows': rows,
            }
            self._render_xlsx_table(table, response)
            return

        m = data.get('mapped', {})
        op = m.get('operations', {})
        inv = m.get('investing', {})
        fin = m.get('financing', {})

        rows = [
            {'type': 'section', 'values': ['For the Year Ending', data.get('date_to_text', '')]},
            {'values': ['Cash at Beginning of Year', float(data.get('opening_cash', 0.0))]},
            {'type': 'section', 'values': ['Operations', '']},
            {'values': ['Cash receipts from Customers', float(op.get('cash_receipts_customers', 0.0))]},
            {'values': ['Cash receipts from Other Operations', float(op.get('cash_receipts_other', 0.0))]},
            {'values': ['Cash paid for Inventory purchases', float(op.get('cash_paid_inventory', 0.0))]},
            {'values': ['Cash paid for General operating and administrative expenses', float(op.get('cash_paid_general_admin', 0.0))]},
            {'values': ['Cash paid for Wage expenses', float(op.get('cash_paid_wages', 0.0))]},
            {'values': ['Cash paid for Interest', float(op.get('cash_paid_interest', 0.0))]},
            {'values': ['Cash paid for Income taxes', float(op.get('cash_paid_income_taxes', 0.0))]},
            {'type': 'section', 'values': ['Net Cash Flow from Operations', float(op.get('net', 0.0))]},
            {'type': 'section', 'values': ['Investing Activities', '']},
            {'values': ['Cash receipts from Sale of property and equipment', float(inv.get('cash_receipts_sale_ppe', 0.0))]},
            {'values': ['Cash receipts from Collection of principal on loans', float(inv.get('cash_receipts_collection_loans', 0.0))]},
            {'values': ['Cash receipts from Sale of investment securities', float(inv.get('cash_receipts_sale_investments', 0.0))]},
            {'values': ['Cash paid for Purchase of property and equipment', float(inv.get('cash_paid_purchase_ppe', 0.0))]},
            {'values': ['Cash paid for Making loans to other entities', float(inv.get('cash_paid_loans_to_others', 0.0))]},
            {'values': ['Cash paid for Purchase of investment securities', float(inv.get('cash_paid_purchase_investments', 0.0))]},
            {'type': 'section', 'values': ['Net Cash Flow from Investing Activities', float(inv.get('net', 0.0))]},
            {'type': 'section', 'values': ['Financing Activities', '']},
            {'values': ['Cash receipts from Issuance of stock', float(fin.get('cash_receipts_issuance_stock', 0.0))]},
            {'values': ['Cash receipts from Borrowing', float(fin.get('cash_receipts_borrowing', 0.0))]},
            {'values': ['Cash paid for Repurchase of stock (treasury stock)', float(fin.get('cash_paid_treasury_stock', 0.0))]},
            {'values': ['Cash paid for Repayment of loans', float(fin.get('cash_paid_repayment_loans', 0.0))]},
            {'values': ['Cash paid for Dividends', float(fin.get('cash_paid_dividends', 0.0))]},
            {'type': 'section', 'values': ['Net Cash Flow from Financing Activities', float(fin.get('net', 0.0))]},
            {'type': 'section', 'values': ['Net Increase in Cash', float(m.get('net_increase', 0.0))]},
            {'type': 'section', 'values': ['Cash at End of Year', float(data.get('closing_cash', 0.0))]},
        ]

        table = {
            'sheet_name': 'Cash Flow Custom',
            'title': f"{data.get('company_name', '')}: Cash Flow Statement",
            'company_logo': data.get('company_logo'),
            'meta': [],
            'headers': ['Particulars', 'Amount'],
            'column_widths': [(0, 0, 72), (1, 1, 22)],
            'rows': rows,
        }
        self._render_xlsx_table(table, response)
