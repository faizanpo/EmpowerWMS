from odoo import models, fields
from woocommerce import API
from odoo.exceptions import UserError

class ProductsWoo(models.Model):
    _name = 'woocommerce.products'
    name=fields.Char("name")

    # def create_product(self):
    #     wcapi = API(
    #         url="https://tableschairs.co.uk/",
    #         consumer_key='ck_c0c0e255cb3a395ee2b460b6a172d05b02a0ab70',
    #         consumer_secret='cs_d85c100706c25e0eb36173de257fe55bf7f20dc7',
    #         version="wc/v3",
    #         query_string_auth=True
    #     )
    #     prodobj=self.env['product.product']
    #     page=1
    #     r = wcapi.get("products/", params={"per_page": 100, "page": page}).json()
    #     # raise UserError(str(r))
    #     while(r):
    #         skuslist=[]
    #         for wd in r:
    #             skuslist.append(wd['sku'])
    #         for op in prodobj.search([('id','=',18)]):
    #             if not op.default_code in skuslist:
    #                 prodcreate={
    #                     'name': op['name'],
    #                     'status': 'draft',
    #                     'description': op['description'] if op['description'] else '',
    #                     'sku': op['default_code'],
    #                     'manage_stock': True,
    #                     'price_price_list':op['regular_price'],
    #                     'list_price':op['regular_price'],
    #                     'stock_quantity': str(op['qty_available']),
    #                 }
    #                 created = wcapi.post("products", prodcreate).json()
    #                 raise UserError(created)
    #         page += 1
    #         r = wcapi.get("products/", params={"per_page": 10, "page": 1}).json()


