{
    "name": "Autolamps Custom Module",
    "version": "1.0",
    "depends": ["base", "sale_management", "stock", "product", "hr"],
    "data": [
        "views/product_supplierinfo_views.xml",
        "views/inherited_supplier_views.xml",
        "views/inherited_employee_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": True,
    "license": "LGPL-3",
}
