# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "St George - Accounting",
    "version": "19.0.1.0.0",
    "category": "Accounting & Finance",
    "summary": "Chart of Accounts for St George FC.",
    "author": "ATLAS Computer",
    "website": "https://act.com.et",
    "depends": ["account"],
    "license": "AGPL-3",
    "data": [
        "data/st_george_chart_data.xml",
        "data/account.chart.template.csv",
        "data/account.account.template.csv",
        "data/st_george_chart_post_data.xml",
        "data/account_tax_template_data.xml",
    ],
    "post_init_hook": "post_init_hook",
}
