from odoo import fields, models


class InheritedEmployee(models.AbstractModel):
    _inherit = "hr.employee.base"

    # Added selection field to indicate employment state
    state = fields.Selection(
        [("draft", "Draft"), ("employee", "Employee"), ("resigned", "Resigned")],
        string="State",
        default="draft",
    )
    bank = fields.Many2one("res.bank", string="Bank")

    # For button to confirm employee in draft status
    def set_employee(self):
        for record in self:
            if record.state == "draft":
                record.state = "employee"
