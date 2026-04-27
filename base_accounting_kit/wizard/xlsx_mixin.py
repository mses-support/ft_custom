# -*- coding: utf-8 -*-
import base64
import io
import json

import xlsxwriter
from odoo.tools.json import json_default


class ReportXlsxMixin:
    """Small utility mixin to keep XLSX export behavior consistent."""

    def _xlsx_action(self, model_name, report_name, options):
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': model_name,
                'options': json.dumps(options, default=json_default),
                'output_format': 'xlsx',
                'report_name': report_name,
            },
            'report_type': 'xlsx',
        }

    def _get_formats(self, workbook):
        return {
            'title': workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'font_size': 14,
            }),
            'label': workbook.add_format({'bold': True}),
            'header': workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
            }),
            'text': workbook.add_format({'border': 1, 'text_wrap': True}),
            'num': workbook.add_format({
                'border': 1,
                'align': 'right',
                'num_format': '#,##0.00',
            }),
            'section': workbook.add_format({
                'bold': True,
                'border': 1,
                'bg_color': '#F2F2F2',
                'text_wrap': True,
            }),
            'section_num': workbook.add_format({
                'bold': True,
                'border': 1,
                'bg_color': '#F2F2F2',
                'align': 'right',
                'num_format': '#,##0.00',
            }),
        }

    def _insert_logo(self, sheet, logo_b64):
        if not logo_b64:
            return
        image_bytes = base64.b64decode(logo_b64)
        image_stream = io.BytesIO(image_bytes)
        sheet.insert_image(
            0, 0, 'logo.png',
            {'image_data': image_stream, 'x_scale': 0.35, 'y_scale': 0.35}
        )

    def _render_xlsx_table(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet_name = (data.get('sheet_name') or 'Report')[:31]
        sheet = workbook.add_worksheet(sheet_name)
        fmt = self._get_formats(workbook)

        for width_conf in data.get('column_widths', []):
            sheet.set_column(width_conf[0], width_conf[1], width_conf[2])

        self._insert_logo(sheet, data.get('company_logo'))

        title = data.get('title') or 'Report'
        if data.get('header_col_count'):
            col_end = max(0, int(data.get('header_col_count')) - 1)
        elif data.get('header_rows'):
            col_end = max(0, max((len(r) for r in data.get('header_rows', [])), default=1) - 1)
        else:
            col_end = max(0, len(data.get('headers', [])) - 1)
        title_row = 0
        if data.get('company_logo'):
            title_row = 2
        sheet.merge_range(title_row, 0, title_row, col_end, title, fmt['title'])

        row = title_row + 2
        for label, value in data.get('meta', []):
            sheet.write(row, 0, label, fmt['label'])
            sheet.write(row, 1, value or '')
            row += 1

        row += 1
        header_rows = data.get('header_rows')
        if header_rows:
            header_merges = data.get('header_merges', [])
            covered = set()
            for merge in header_merges:
                r1, c1, r2, c2, label = merge
                sheet.merge_range(row + r1, c1, row + r2, c2, label, fmt['header'])
                for rr in range(r1, r2 + 1):
                    for cc in range(c1, c2 + 1):
                        covered.add((rr, cc))
            for r_idx, headers in enumerate(header_rows):
                for col, head in enumerate(headers):
                    if head is None or (r_idx, col) in covered:
                        continue
                    sheet.write(row + r_idx, col, head, fmt['header'])
            row += len(header_rows)
        else:
            headers = data.get('headers', [])
            for col, head in enumerate(headers):
                sheet.write(row, col, head, fmt['header'])
            row += 1

        for line in data.get('rows', []):
            line_type = line.get('type', 'data')
            values = line.get('values', [])
            for col, value in enumerate(values):
                is_num = isinstance(value, (int, float))
                if line_type == 'section':
                    cell_fmt = fmt['section_num'] if is_num else fmt['section']
                else:
                    cell_fmt = fmt['num'] if is_num else fmt['text']
                if is_num:
                    sheet.write_number(row, col, value, cell_fmt)
                else:
                    sheet.write(row, col, value or '', cell_fmt)
            row += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
