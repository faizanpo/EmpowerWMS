from odoo import models, fields
from woocommerce import API
from odoo.exceptions import UserError

class ProductsWooLogs(models.Model):
    _name = 'woocommerce.product.update.logs'
    odoo_id = fields.Integer("Odoo Product ID")
    woo_id = fields.Integer("Woocommerce Product ID")
    status_select = [
        ('complete', 'Completed'),
        ('error', 'Error'),
    ]
    status = fields.Selection(selection=status_select,string='Status')
    details=fields.Html("Details")
    sku = fields.Char("Sku")
    main_id = fields.Many2one(comodel_name='woocommerce.main',relation='produpdate_o_w_log_ids', string="Product Logs")


