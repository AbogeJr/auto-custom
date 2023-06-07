from odoo import fields, models, api


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    supplier_type = fields.Selection(
        [("local", "Local"), ("international", "International")],
        string="Locality",
        default="local",
        store=True,
    )


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    supplier_type = fields.Selection(
        related="supplier_id.supplier_type", string="Locality", store=True
    )

    _sql_constraints = [
        (
            "product_location_check",
            "unique (supplier_type)",
            "The supplier must be unique!",
        ),
    ]
