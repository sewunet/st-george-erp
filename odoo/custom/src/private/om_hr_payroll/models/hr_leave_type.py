from odoo import fields, models


class LeaveType(models.Model):
    _inherit = "hr.leave.type"

    code = fields.Char(string="Code")
