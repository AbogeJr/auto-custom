from odoo import fields, models


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    supplier_type = fields.Selection(
        [("local", "Local"), ("international", "International")],
        string="Locality",
    )


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    supplier_type = fields.Selection(
        related="supplier_id.supplier_type", string="Locality"
    )

    _sql_constraints = [
        (
            "product_location_check",
            "unique (supplier_id, supplier_type)",
            "Two suppliers cannot be from the same locality. (i.e Local or International)",
        ),
    ]
