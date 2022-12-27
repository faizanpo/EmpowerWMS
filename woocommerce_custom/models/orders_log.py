from odoo import models, fields
from woocommerce import API
from odoo.exceptions import UserError

class ProductsWooLogs(models.Model):
    _name = 'woocommerce.orders.logs'
    odoo_id = fields.Integer("Odoo Order ID")
    woo_id = fields.Integer("Woocommerce Order ID")
    status_select = [
        ('complete', 'Completed'),
        ('error', 'Error'),
    ]
    status = fields.Selection(selection=status_select,string='Status')
    details=fields.Char("Details")
    customer_name = fields.Char("Customer Name")
    main_id = fields.Many2one(comodel_name='woocommerce.main',relation='orers_w_o_log_ids', string="Product Logs")


