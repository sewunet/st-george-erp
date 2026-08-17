[![Odoo](https://img.shields.io/badge/odoo-v19.0-a3478a)](https://github.com/odoo/odoo/tree/19.0)
[![AGPL-3.0 license](https://img.shields.io/badge/license-AGPL--3.0-success)](LICENSE)

# St. George Football Club — ERP

**ቅዱስ ጊዮርጊስ ስፖርት ክለብ · Saint George S.C. — Addis Ababa, Ethiopia**

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This project delivers an Enterprise Resource Planning (ERP) system for St. George Football Club, built entirely on open source software using **Odoo 19**. It is designed as a working template for football clubs and sporting organisations that need to plan and manage their resources — people, money, contracts, equipment and stock — from a single system.

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The base package can be installed as-is, then configured with the club's own chart of accounts, departments, approval rules and fiscal calendar. It covers the full administrative workflow of the club end to end, and is structured to stay consistent with the club's internal regulations and with Ethiopian statutory reporting requirements. The system is made up of 7 modules:

1. **Organization Structure** — club departments, first team and youth academy staff, roles and approval hierarchy
2. **Budgeting Module** — season budgets, departmental allocations, commitment control and variance tracking
3. **Procurement Module** — purchase requests, tendering, vendor management and purchase orders
4. **Finance & Accounting Module** — general ledger, payables and receivables, gate receipts, sponsorship income and financial reporting
5. **Agreement and Contract Module** — player and coaching staff contracts, transfer agreements, sponsorship and broadcast deals, renewal and expiry alerts
6. **Assets Module** — stadium and training ground facilities, vehicles, gym and medical equipment, depreciation schedules
7. **Inventory Module** — match kit, training wear, merchandise, medical and grounds-keeping supplies

# Installation

1. Download the source code
    ```
    git clone https://github.com/sewunet/st-george-erp.git
    ```
2. Move into the downloaded folder
    ```
    cd st-george-erp
    ```
3. Start the Docker images
    ```
    docker compose -f st-george-prod.yaml up -d
    ```
    If you need to rebuild the images, use:
    ```
    docker compose -f st-george-prod-build.yaml up -d
    ```
4. Once the installation finishes, verify it by opening http://localhost/ or http://127.0.0.1/ in your browser.

> **Note:** change the default master password and the administrator credentials before exposing the instance to your network.

# Credits

Copyright © St. George Football Club. All rights reserved.

Licensed under [AGPL-3.0 license](LICENSE)