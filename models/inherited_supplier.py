from odoo import fields, models, api, tools, registry, SUPERUSER_ID, exceptions
from dateutil import relativedelta
import logging

_logger = logging.getLogger(__name__)


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

    def _prepare_procurement_values(self, date=False, group=False):
        # Add the supplier_type to the procurement values
        procurement_values = super()._prepare_procurement_values(date=date, group=group)
        procurement_values["supplier_type"] = self.supplier_type

        return procurement_values

    def _procure_orderpoint_confirm(
        self, use_new_cursor=False, company_id=None, raise_user_error=True
    ):
        orderpoints = self.filtered(lambda op: op.qty_on_hand < op.product_min_qty)
        print(len(orderpoints))

        # Filter orderpoints based on matching product_ids and select minimum product_min_qty

        orderpoints_by_product = {}
        for orderpoint in orderpoints:
            product_id = orderpoint.product_id
            if product_id in orderpoints_by_product:
                existing_orderpoint = orderpoints_by_product[product_id]
                if orderpoint.product_min_qty < existing_orderpoint.product_min_qty:
                    orderpoints_by_product[product_id] = orderpoint
            else:
                orderpoints_by_product[product_id] = orderpoint

        for orderpoint in orderpoints_by_product.values():
            print("=============ORDERPOINT=============")
            print(orderpoint.name)
            print(orderpoint.qty_on_hand)
            print(orderpoint.product_min_qty)
            print(orderpoint.group_id)
            print(orderpoint.product_id.name)
            print("=============ORDERPOINT=============")

            values = orderpoint._prepare_procurement_values()

            procurement_vals = {
                "product_id": orderpoint.product_id.id,
                "product_qty": orderpoint.qty_to_order,
                "product_uom": orderpoint.product_uom.id,
                "location_id": orderpoint.location_id.id,
                "name": orderpoint.name,
                "origin": orderpoint.name,
                "company_id": orderpoint.company_id.id,
                "values": values,
            }
            self.env["procurement.group"].Procurement(**procurement_vals)

        return super(InheritStockWarehouseOrderpoint, self)._procure_orderpoint_confirm(
            use_new_cursor=use_new_cursor,
            company_id=company_id,
            raise_user_error=raise_user_error,
        )
