from odoo import fields, models


class InheritedEmployee(models.AbstractModel):
    _inherit = "hr.employee.base"

    # Selection to indicate employment state
    state = fields.Selection(
        [("draft", "Draft"), ("employee", "Employee"), ("resigned", "Resigned")],
        string="State",
        default="draft",
    )
    active = fields.Boolean(default=True)

    def set_employee(self):
        for record in self:
            if record.state == "draft":
                record.state = "employee"
