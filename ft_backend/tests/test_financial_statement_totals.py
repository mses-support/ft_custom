from unittest.mock import patch

from odoo.tests.common import SavepointCase

from odoo.addons.ft_backend.reports.report_financial_statement import FinancialStatementReportMixin


class TestFinancialStatementTotals(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.config = cls.env["ft.financial.report.config"].create({
            "name": "Test Balance Sheet Config",
            "statement_type": "balance_sheet",
            "company_id": cls.company.id,
        })

        cls.acc_cur = cls.env["account.account"].create({
            "name": "Test Current Asset",
            "code": "TCA001",
            "account_type": "asset_current",
            "company_ids": [(6, 0, [cls.company.id])],
        })
        cls.acc_non_cur = cls.env["account.account"].create({
            "name": "Test Non Current Asset",
            "code": "TNCA001",
            "account_type": "asset_non_current",
            "company_ids": [(6, 0, [cls.company.id])],
        })

        mk = cls.env["ft.financial.report.config.line"].create
        mk({"config_id": cls.config.id, "sequence": 10, "code": "BS_ASSETS", "name": "Assets", "level": 0})
        mk({
            "config_id": cls.config.id,
            "sequence": 20,
            "code": "BS_CUR_ASSET",
            "name": "Current Assets",
            "parent_code": "BS_ASSETS",
            "level": 1,
            "account_ids": [(6, 0, [cls.acc_cur.id])],
        })
        mk({
            "config_id": cls.config.id,
            "sequence": 30,
            "code": "BS_CUR_ASSET_TOTAL",
            "name": "Total current assets",
            "parent_code": "BS_CUR_ASSET",
            "level": 2,
            "is_total": True,
        })
        mk({
            "config_id": cls.config.id,
            "sequence": 40,
            "code": "BS_NON_CUR_ASSET",
            "name": "Non Current Assets",
            "parent_code": "BS_ASSETS",
            "level": 1,
            "account_ids": [(6, 0, [cls.acc_non_cur.id])],
        })
        mk({
            "config_id": cls.config.id,
            "sequence": 50,
            "code": "BS_NON_CUR_ASSET_TOTAL",
            "name": "Total fixed assets",
            "parent_code": "BS_NON_CUR_ASSET",
            "level": 2,
            "is_total": True,
        })
        mk({
            "config_id": cls.config.id,
            "sequence": 60,
            "code": "BS_TOTAL_ASSET",
            "name": "Total Assets",
            "parent_code": "BS_ASSETS",
            "level": 0,
            "is_total": True,
        })

    def test_parent_section_totals_are_not_zero(self):
        report = self.env["report.ft_backend.report_balance_sheet_custom"]

        with patch.object(FinancialStatementReportMixin, "_sum_accounts", autospec=True) as mocked_sum:
            def _impl(_self, account_ids, company_id, target_move, date_from=None, date_to=None, **kwargs):
                if account_ids == [self.acc_cur.id]:
                    return 14254.15
                if account_ids == [self.acc_non_cur.id]:
                    return 5000.0
                return 0.0
            mocked_sum.side_effect = _impl

            rows = report._build_lines(
                self.config,
                self.company.id,
                "posted",
                date_to="2026-05-05",
                journal_ids=[],
                analytic_plan_ids=[],
                analytic_account_ids=[],
                comparison_date_to="2026-05-05",
            )

        by_code = {row["code"]: row for row in rows}
        self.assertAlmostEqual(by_code["BS_CUR_ASSET"]["amount"], 14254.15, places=2)
        self.assertAlmostEqual(by_code["BS_CUR_ASSET_TOTAL"]["amount"], 14254.15, places=2)
        self.assertAlmostEqual(by_code["BS_NON_CUR_ASSET_TOTAL"]["amount"], 5000.0, places=2)
        self.assertAlmostEqual(by_code["BS_TOTAL_ASSET"]["amount"], 19254.15, places=2)

    def test_cash_flow_investing_mapping(self):
        report = self.env["report.ft_backend.report_custom_cash_flow_statement"]
        lines = [
            {"type": "report", "level": 1, "name": "Investing Activities", "balance": 700.0},
            {"type": "account", "level": 4, "name": "1100 Sale of investment securities", "balance": 1200.0},
            {"type": "account", "level": 4, "name": "1200 Purchase of investment securities", "balance": -500.0},
        ]

        mapped = report._build_lookup(lines)
        self.assertAlmostEqual(mapped["investing"]["cash_receipts_sale_investments"], 1200.0, places=2)
        self.assertAlmostEqual(mapped["investing"]["cash_paid_purchase_investments"], -500.0, places=2)
        self.assertAlmostEqual(mapped["investing"]["net"], 700.0, places=2)
