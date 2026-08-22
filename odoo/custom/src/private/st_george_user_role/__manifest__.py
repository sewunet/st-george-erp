# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "St George - User Roles",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "Customized",
    "author": "ATLAS Computer",
    "depends": [
        "base_user_role_restrict_update",
        "contract",
        "hr_contract",
        "queue_job",
    ],
    "data": [
        "data/general_role.xml",
        "data/accounting_role.xml",
        "data/procurement_role.xml",
        "data/sale_role.xml",
        "data/super_user_role.xml",
        "data/audit_role.xml",
    ],
    "installable": True,
}
