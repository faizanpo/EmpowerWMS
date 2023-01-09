from odoo import fields, models, api


class EgSaleOrder(models.Model):
    _name = "eg.sale.order"

    odoo_order_id = fields.Many2one(comodel_name="sale.order", string="Odoo Sale Order", required=True)
    name = fields.Char(related="odoo_order_id.name", string="Name", store=True, readonly=True)
    instance_id = fields.Many2one(comodel_name="eg.ecom.instance", string="Instance", required=True)
    provider = fields.Selection(related="instance_id.provider", store=True)
    inst_order_id = fields.Char(string="Instance Sale", required=True)
    eg_account_journal_id = fields.Many2one(comodel_name="eg.account.journal", string="Payment Gateway")
    update_required = fields.Boolean(string="Update Required")
    #Asir
    shopify_payment_gateway = fields.Char(String = "Shopify Payment Gateway")
    shopify_order_notes = fields.Char(String = "Shopify Order Notes")

    def test(self):
        self.env["sale.order"].sync_status(instance_id=self)
