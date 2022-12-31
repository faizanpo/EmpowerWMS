from odoo import models


class EgProductTemplate(models.Model):
    _inherit = "eg.product.template"

    def export_product_shopify_server(self):
        self.env["product.template"].export_product_in_shopify()
