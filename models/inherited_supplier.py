from odoo import fields, models, api


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    supplier_type = fields.Selection(
        [("local", "Local"), ("international", "International")],
        string="Locality",
        default="local",
        store=True,
    )


class InheritStockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    supplier_type = fields.Selection(
        [("local", "Local"), ("international", "International")],
        string="Locality",
        default="local",
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

    @api.model
    def _procure_orderpoint_confirm(
        self, use_new_cursor=False, company_id=None, raise_user_error=True
    ):
        international_orderpoints = self.filtered(
            lambda op: op.supplier_type == "international"
        )
        local_orderpoints = self.filtered(lambda op: op.supplier_type == "local")

        if international_orderpoints:
            for orderpoint in international_orderpoints:
                if orderpoint.qty_available < orderpoint.product_min_qty:
                    # Trigger replenishment from international vendor
                    vendor = (
                        orderpoint.supplier_id
                    )  # Assuming you have a field named 'international_vendor_id' on the orderpoint model
                    if vendor:
                        # Create procurement for the international vendor
                        procurement_vals = {
                            "product_id": orderpoint.product_id.id,
                            "product_qty": orderpoint.qty_to_order,
                            "product_uom": orderpoint.product_uom.id,
                            "partner_id": vendor.id,
                            "origin": orderpoint.name,
                            "company_id": orderpoint.company_id.id,
                        }
                        self.env["procurement.group"].run(
                            [
                                self.env["procurement.group"].Procurement(
                                    **procurement_vals
                                )
                            ]
                        )

        if local_orderpoints:
            for orderpoint in local_orderpoints:
                if orderpoint.qty_available == 0:
                    # Cancel the previous replenishment (if any)
                    procurements = self.env["procurement.group"].search(
                        [
                            ("orderpoint_id", "=", orderpoint.id),
                            ("state", "not in", ["done", "cancel"]),
                        ]
                    )
                    if procurements:
                        procurements.sudo().cancel()

                    # Trigger replenishment from local vendor
                    vendor = orderpoint.supplier_id
                    if vendor:
                        # Create procurement for the local vendor
                        procurement_vals = {
                            "product_id": orderpoint.product_id.id,
                            "product_qty": orderpoint.qty_to_order,
                            "product_uom": orderpoint.product_uom.id,
                            "partner_id": vendor.id,
                            "origin": orderpoint.name,
                            "company_id": orderpoint.company_id.id,
                        }
                        self.env["procurement.group"].run(
                            [
                                self.env["procurement.group"].Procurement(
                                    **procurement_vals
                                )
                            ]
                        )

        return super(InheritStockWarehouseOrderpoint, self)._procure_orderpoint_confirm(
            use_new_cursor=use_new_cursor,
            company_id=company_id,
            raise_user_error=raise_user_error,
        )
