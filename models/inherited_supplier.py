from odoo import fields, models


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    supplier_type = fields.Selection(
        [("local", "Local"), ("international", "International")],
        string="Locality",
        default="local",
    )


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    supplier_type = fields.Selection(
        [("local", "Local"), ("international", "International")],
        string="Locality",
        default="local"
    )

    _sql_constraints = [
        (
            "supplier_locality_check",
            "unique (product_id, supplier_type)",
            "You can not have more than one supplier from the same locality!",
        ),
        (
            "product_location_check",
            "CHECK(1=1)",
            "A replenishment rule already exists.",
        ),
    ]
