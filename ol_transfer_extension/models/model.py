
from odoo import models, api, fields, _
from odoo.exceptions import UserError
import json
import datetime

class transfer_extension(models.Model):

    _inherit = "stock.picking"
    order_date = fields.Datetime(string='Order Date')
    def create(self,val):
        res = super(transfer_extension, self).create(val)
        for rec in res:
            sale_order=self.env['sale.order'].search([('name','=',rec.origin)])
            if sale_order:
                res.order_date=sale_order.date_order
        return res
class sale_order_extension(models.Model):
    _inherit = "sale.order"
    @api.onchange('date_order')
    def _onchange_date_order(self):
        for rec in self:
            transfers=self.env['stock.picking'].search([('origin','=',rec.name)])
            for transfer in transfers:
                transfer.order_date=rec.date_order
                