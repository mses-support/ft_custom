from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import UserError


class ReportCustomCashFlowStatement(models.AbstractModel):
    _name = 'report.ft_backend.report_custom_cash_flow_statement'
    _description = 'Custom Cash Flow Statement Report'

    @api.model
    def _to_date_string(self, value):
        if not value:
            return ''
        return fields.Date.to_date(value).strftime('%m/%d/%Y')

    @api.model
    def _as_id(self, value):
        if isinstance(value, (list, tuple)):
            return value[0]
        return value

    @api.model
    def _build_used_context(self, form):
        analytic_ids = set(form.get('analytic_account_ids') or [])
        if form.get('analytic_plan_ids'):
            plan_accounts = self.env['account.analytic.account'].search([('plan_id', 'in', form.get('analytic_plan_ids'))]).ids
            analytic_ids.update(plan_accounts)
        return {
            'company_id': self._as_id(form.get('company_id')) or self.env.company.id,
            'date_from': form.get('date_from'),
            'date_to': form.get('date_to'),
            'strict_range': True,
            'state': form.get('target_move') or 'posted',
            'journal_ids': form.get('journal_ids') or [],
            'analytic_account_ids': list(analytic_ids),
        }

    @api.model
    def _format_amount(self, amount):
        if not amount:
            return '0'
        return '{:,.2f}'.format(abs(amount))

    @api.model
    def _get_base_lines(self, form):
        cash_flow_root = self.env.ref('base_accounting_kit.account_financial_report_cash_flow0')
        line_engine = self.env['report.base_accounting_kit.report_cash_flow']
        data = {
            'account_report_id': (cash_flow_root.id, cash_flow_root.name),
            'target_move': form.get('target_move') or 'posted',
            'debit_credit': False,
            'enable_filter': False,
            'used_context': self._build_used_context(form),
        }
        return line_engine.get_account_lines(data)

    @api.model
    def _build_lookup(self, lines):
        # Account detail rows are level >= 4 and look like "CODE Name".
        account_rows = [l for l in lines if l.get('type') == 'account' and l.get('level', 0) >= 4]

        def find(keyword_list):
            total = 0.0
            for row in account_rows:
                name = (row.get('name') or '').lower()
                if any(key in name for key in keyword_list):
                    total += row.get('balance', 0.0)
            return total

        def section_total(section_name):
            for row in lines:
                if row.get('type') == 'report' and (row.get('name') or '').strip().lower() == section_name.lower():
                    return row.get('balance', 0.0)
            return 0.0

        mapped = {
            'operations': {
                'cash_receipts_customers': find(['customer']),
                'cash_receipts_other': find(['other']),
                'cash_paid_inventory': find(['inventory']),
                'cash_paid_general_admin': find(['general', 'administrative', 'admin']),
                'cash_paid_wages': find(['wage', 'salary', 'payroll']),
                'cash_paid_interest': find(['interest']),
                'cash_paid_income_taxes': find(['tax']),
                'net': section_total('Operations'),
            },
            'investing': {
                'cash_receipts_sale_ppe': find(['property', 'equipment', 'fixed asset']),
                'cash_receipts_collection_loans': find(['loan', 'principal']),
                'cash_receipts_sale_investments': find(['investment', 'security']),
                'cash_paid_purchase_ppe': find(['purchase of property', 'equipment', 'fixed asset']),
                'cash_paid_loans_to_others': find(['making loans', 'loan to']),
                'cash_paid_purchase_investments': find(['purchase of investment', 'security']),
                'net': section_total('Investing Activities'),
            },
            'financing': {
                'cash_receipts_issuance_stock': find(['issuance of stock', 'share capital', 'capital']),
                'cash_receipts_borrowing': find(['borrowing', 'loan payable']),
                'cash_paid_treasury_stock': find(['treasury stock', 'repurchase']),
                'cash_paid_repayment_loans': find(['repayment of loans', 'loan repayment']),
                'cash_paid_dividends': find(['dividend']),
                'net': section_total('Financing Activities'),
            },
        }
        net_increase = mapped['operations']['net'] + mapped['investing']['net'] + mapped['financing']['net']
        mapped['net_increase'] = net_increase
        return mapped

    @api.model
    def _cash_balance(self, company_id, date_to, state, journal_ids=None, analytic_plan_ids=None, analytic_account_ids=None):
        # Cash & bank balances till date_to for opening/ending presentation.
        aml = self.env['account.move.line']
        domain = [
            ('company_id', '=', company_id),
            ('date', '<=', date_to),
            ('account_id.account_type', '=', 'asset_cash'),
        ]
        if state == 'posted':
            domain.append(('parent_state', '=', 'posted'))
        if journal_ids:
            domain.append(('journal_id', 'in', journal_ids))
        analytic_ids = set(analytic_account_ids or [])
        if analytic_plan_ids:
            plan_accounts = self.env['account.analytic.account'].search([('plan_id', 'in', analytic_plan_ids)]).ids
            analytic_ids.update(plan_accounts)
        if analytic_ids:
            for analytic_id in analytic_ids:
                domain.append(('analytic_distribution', 'ilike', f'"{analytic_id}"'))
        lines = aml.search(domain)
        return sum((line.debit - line.credit) for line in lines)

    @api.model
    def _prepare_statement(self, form):
        company_id = self._as_id(form.get('company_id')) or self.env.company.id
        company = self.env['res.company'].browse(company_id)
        lines = self._get_base_lines(form)
        mapped = self._build_lookup(lines)

        date_from = fields.Date.to_date(form.get('date_from'))
        opening_date = date_from - timedelta(days=1)
        opening_cash = self._cash_balance(
            company_id, opening_date, form.get('target_move') or 'posted',
            form.get('journal_ids') or [], form.get('analytic_plan_ids') or [], form.get('analytic_account_ids') or []
        )
        closing_cash = opening_cash + mapped['net_increase']
        return {
            'company': company,
            'date_to_text': self._to_date_string(form.get('date_to')),
            'opening_cash': opening_cash,
            'closing_cash': closing_cash,
            'mapped': mapped,
        }

    @api.model
    def _prepare_multi_period_statement(self, form, mode):
        company_id = self._as_id(form.get('company_id')) or self.env.company.id
        company = self.env['res.company'].browse(company_id)
        end_date = fields.Date.to_date(form.get('date_to'))
        periods = []
        if mode == 'three_year':
            for year in range(end_date.year - 2, end_date.year + 1):
                p_from = end_date.replace(year=year, month=1, day=1)
                p_to = end_date.replace(year=year)
                periods.append((p_from, p_to, str(year)))
        else:
            for month in range(1, 13):
                p_from = end_date.replace(month=month, day=1)
                if month == 12:
                    p_to = end_date.replace(month=12, day=31)
                else:
                    p_to = (end_date.replace(month=month + 1, day=1) - timedelta(days=1))
                periods.append((p_from, p_to, p_from.strftime('%b-%y')))

        defs = [
            ('section', 'Operations', None),
            ('data', 'Cash receipts from Customers', ('operations', 'cash_receipts_customers')),
            ('data', 'Cash receipts from Other Operations', ('operations', 'cash_receipts_other')),
            ('data', 'Cash paid for Inventory purchases', ('operations', 'cash_paid_inventory')),
            ('data', 'Cash paid for General operating and administrative expenses', ('operations', 'cash_paid_general_admin')),
            ('data', 'Cash paid for Wage expenses', ('operations', 'cash_paid_wages')),
            ('data', 'Cash paid for Interest', ('operations', 'cash_paid_interest')),
            ('data', 'Cash paid for Income taxes', ('operations', 'cash_paid_income_taxes')),
            ('total', 'Net Cash Flow from Operations', ('operations', 'net')),
            ('section', 'Investing Activities', None),
            ('data', 'Sale of property and equipment', ('investing', 'cash_receipts_sale_ppe')),
            ('data', 'Collection of principal on loans', ('investing', 'cash_receipts_collection_loans')),
            ('data', 'Sale of investment securities', ('investing', 'cash_receipts_sale_investments')),
            ('data', 'Purchase of property and equipment', ('investing', 'cash_paid_purchase_ppe')),
            ('data', 'Making loans to other entities', ('investing', 'cash_paid_loans_to_others')),
            ('data', 'Purchase of investment securities', ('investing', 'cash_paid_purchase_investments')),
            ('total', 'Net Cash Flow from Investing Activities', ('investing', 'net')),
            ('section', 'Financing Activities', None),
            ('data', 'Issuance of stock', ('financing', 'cash_receipts_issuance_stock')),
            ('data', 'Borrowing', ('financing', 'cash_receipts_borrowing')),
            ('data', 'Repurchase of stock (treasury stock)', ('financing', 'cash_paid_treasury_stock')),
            ('data', 'Repayment of loans', ('financing', 'cash_paid_repayment_loans')),
            ('data', 'Dividends', ('financing', 'cash_paid_dividends')),
            ('total', 'Net Cash Flow from Financing Activities', ('financing', 'net')),
            ('final', 'Net Cash Flow', ('root', 'net_increase')),
        ]

        rows = []
        openings = []
        closings = []
        labels = []
        cols = []
        for p_from, p_to, label in periods:
            form_p = dict(form)
            form_p['date_from'] = fields.Date.to_string(p_from)
            form_p['date_to'] = fields.Date.to_string(p_to)
            prepared = self._prepare_statement(form_p)
            cols.append(prepared)
            labels.append(label)
            openings.append(prepared['opening_cash'])
            closings.append(prepared['closing_cash'])

        for line_type, name, keydef in defs:
            values = []
            if keydef:
                for col in cols:
                    if keydef[0] == 'root':
                        values.append(col['mapped'].get(keydef[1], 0.0))
                    else:
                        values.append(col['mapped'].get(keydef[0], {}).get(keydef[1], 0.0))
            rows.append({'type': line_type, 'name': name, 'values': values})

        return {'company': company, 'period_labels': labels, 'opening_cash': openings, 'closing_cash': closings, 'rows': rows}

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get('form'):
            raise UserError('Form content is missing, this report cannot be printed.')

        form = data['form']
        mode = form.get('cash_flow_mode') or 'single'
        if mode == 'single':
            prepared = self._prepare_statement(form)
            return {
                'mode': mode,
                'company': prepared['company'],
                'report_name': 'Cash Flow Statement',
                'date_to_text': prepared['date_to_text'],
                'opening_cash': prepared['opening_cash'],
                'closing_cash': prepared['closing_cash'],
                'mapped': prepared['mapped'],
                'fmt': self._format_amount,
            }
        prepared = self._prepare_multi_period_statement(form, mode)
        return {
            'mode': mode,
            'company': prepared['company'],
            'report_name': '3-Year Cash Flow' if mode == 'three_year' else '12-Month Cash Flow',
            'period_labels': prepared['period_labels'],
            'opening_cash': prepared['opening_cash'],
            'closing_cash': prepared['closing_cash'],
            'rows': prepared['rows'],
            'fmt': self._format_amount,
        }
