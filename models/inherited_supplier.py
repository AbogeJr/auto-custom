from odoo import fields, models, api, tools, registry, SUPERUSER_ID, exceptions
from odoo.addons.stock.models.stock_rule import ProcurementException
from dateutil import relativedelta
from psycopg2 import OperationalError

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
        """Prepare specific key for moves or other components that will be created from a stock rule
        comming from an orderpoint. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """

        res = super()._prepare_procurement_values(date=date, group=group)
        print("====PREPARE PROCUREMENT VALUES OVERRIDE=====")
        print(self.supplier_type)
        print(self.product_id.id)
        print(self.product_id.seller_ids)
        # print(self.product_id.seller_ids)
        print(self.id)
        supplier = self.product_id.seller_ids.filtered(
            lambda s: s.supplier_type == self.supplier_type
        )
        if supplier:
            print(supplier)
        else:
            print("No supplier found")

        res["supplierinfo_id"] = supplier
        return res

    def _procure_orderpoint_confirm(
        self, use_new_cursor=False, company_id=None, raise_user_error=True
    ):
        """Create procurements based on orderpoints.
        :param bool use_new_cursor: if set, use a dedicated cursor and auto-commit after processing
            1000 orderpoints.
            This is appropriate for batch jobs only.
        """
        self = self.with_company(company_id)

        for orderpoints_batch_ids in tools.split_every(1000, self.ids):
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            try:
                orderpoints_batch = self.env["stock.warehouse.orderpoint"].browse(
                    orderpoints_batch_ids
                )
                all_orderpoints_exceptions = []
                while orderpoints_batch:
                    procurements = []
                    orderpoints_by_product = {}
                    for orderpoint in orderpoints_batch:
                        product_id = orderpoint.product_id
                        if product_id in orderpoints_by_product:
                            existing_orderpoint = orderpoints_by_product[product_id]
                            if (
                                orderpoint.qty_on_hand < orderpoint.product_min_qty
                                and orderpoint.product_min_qty
                                < existing_orderpoint.product_min_qty
                            ):
                                orderpoints_by_product[product_id] = orderpoint
                        else:
                            orderpoints_by_product[product_id] = orderpoint

                    for orderpoint in orderpoints_by_product.values():
                        print("=============ORDERPOINT BY PRODUCT=============")
                        print(orderpoint.name)
                        print(orderpoint.supplier_type)
                        # print(orderpoint.supplier_type)
                        print(orderpoint.qty_on_hand)
                        print(orderpoint.product_min_qty)
                        print(orderpoint.group_id)
                        print(orderpoint.product_id.name)
                        # print(orderpoint.origin)
                        print("=============ORDERPOINT BY PRODUCT=============")
                        origins = orderpoint.env.context.get("origins", {}).get(
                            orderpoint.id, False
                        )
                        if origins:
                            origin = "%s - %s" % (
                                orderpoint.display_name,
                                ",".join(origins),
                            )
                        else:
                            origin = orderpoint.name
                        if (
                            tools.float_compare(
                                orderpoint.qty_to_order,
                                0.0,
                                precision_rounding=orderpoint.product_uom.rounding,
                            )
                            == 1
                        ):
                            date = orderpoint._get_orderpoint_procurement_date()
                            global_visibility_days = (
                                self.env["ir.config_parameter"]
                                .sudo()
                                .get_param("stock.visibility_days")
                            )
                            if global_visibility_days:
                                date -= relativedelta.relativedelta(
                                    days=int(global_visibility_days)
                                )
                            values = orderpoint._prepare_procurement_values(date=date)
                            # values["supplierinfo_id"] = orderpoint.supplier_id.id
                            print(values)
                            procurements.append(
                                self.env["procurement.group"].Procurement(
                                    orderpoint.product_id,
                                    orderpoint.qty_to_order,
                                    orderpoint.product_uom,
                                    orderpoint.location_id,
                                    orderpoint.name,
                                    origin,
                                    orderpoint.company_id,
                                    values,
                                )
                            )

                    try:
                        with self.env.cr.savepoint():
                            self.env["procurement.group"].with_context(
                                from_orderpoint=True
                            ).run(procurements, raise_user_error=raise_user_error)
                    except ProcurementException as errors:
                        orderpoints_exceptions = []
                        for procurement, error_msg in errors.procurement_exceptions:
                            orderpoints_exceptions += [
                                (procurement.values.get("orderpoint_id"), error_msg)
                            ]
                        all_orderpoints_exceptions += orderpoints_exceptions
                        failed_orderpoints = self.env[
                            "stock.warehouse.orderpoint"
                        ].concat(*[o[0] for o in orderpoints_exceptions])
                        if not failed_orderpoints:
                            _logger.error("Unable to process orderpoints")
                            break
                        orderpoints_batch -= failed_orderpoints

                    except OperationalError:
                        if use_new_cursor:
                            cr.rollback()
                            continue
                        else:
                            raise
                    else:
                        orderpoints_batch._post_process_scheduler()
                        break

                # Log an activity on product template for failed orderpoints.
                for orderpoint, error_msg in all_orderpoints_exceptions:
                    existing_activity = self.env["mail.activity"].search(
                        [
                            ("res_id", "=", orderpoint.product_id.product_tmpl_id.id),
                            (
                                "res_model_id",
                                "=",
                                self.env.ref("product.model_product_template").id,
                            ),
                            ("note", "=", error_msg),
                        ]
                    )
                    if not existing_activity:
                        orderpoint.product_id.product_tmpl_id.sudo().activity_schedule(
                            "mail.mail_activity_data_warning",
                            note=error_msg,
                            user_id=orderpoint.product_id.responsible_id.id
                            or SUPERUSER_ID,
                        )

            finally:
                if use_new_cursor:
                    try:
                        cr.commit()
                    finally:
                        cr.close()
                    _logger.info(
                        "A batch of %d orderpoints is processed and committed",
                        len(orderpoints_batch_ids),
                    )

        return {}
