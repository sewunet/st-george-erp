# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "EGOV - Expense",
    "version": "19.0.1.0.0",
    "author": "ATLAS COMPUTER",
    "category": "Customized",
    "license": "AGPL-3",
    "depends": [
        "base_tier_validation_check_budget",
        "base_tier_validation_server_action",
        "hr_expense_tier_validation",
        "hr_expense_advance_clearing"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_actions_server.xml",
        "data/hr_expense_tier_definition.xml",
        "views/hr_expense_views.xml",
    ],
    "installable": True,
}
