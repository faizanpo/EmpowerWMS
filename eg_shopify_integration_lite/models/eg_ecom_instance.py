from odoo import models, fields, api
import logging
from odoo.exceptions import UserError
try:
    import shopify
except ImportError:
    raise ImportError(
        'This module needs shopify library to connect with shopify. Please install ShopifyAPI on your system. (sudo pip3 install ShopifyAPI)')
_logger = logging.getLogger("=== Import Product Template ===")

class EgEComInstance(models.Model):
    _inherit = "eg.ecom.instance"

    provider = fields.Selection(selection_add=[("eg_shopify", "Shopify")])
    shopify_api_key = fields.Char(string="Api Key")
    shopify_password = fields.Char(string="Password")
    shopify_version = fields.Char(string="Version", default="2020-01")
    shopify_shop = fields.Char(string="Shop Name")
    spf_order_name = fields.Selection([("odoo", "By Odoo"), ("shopify", "By Shopify")], string="Sale Order Name")
    tax_add_by = fields.Selection([("odoo", "By Odoo"), ("shopify", "By Shopify")], string="Add Tax")
    spf_last_order_date = fields.Datetime(string="Last Order Date", readonly=True)
    export_stock_date = fields.Datetime(string="Last update stock", readonly=True)
    #Asir
    company_id = fields.Many2one("res.company", String = "Company")
    warehouse_id = fields.Many2one("stock.warehouse", String = "Warehouse")
    location_id = fields.Many2one("stock.location", String = "Location")
    import_products_in_scheduler=fields.Boolean("Import Product Scheduler Active")
    export_products_in_scheduler=fields.Boolean("Export Product Scheduler Active")
    import_customers_in_scheduler=fields.Boolean("Import Customers Scheduler Active")
    import_orders_in_scheduler=fields.Boolean("Import Orders Scheduler Active")
    sync_inventory_to_shopify=fields.Boolean("Inventory Sync Active")
    
    def get_connection_from_shopify(self, instance_id=None):
        shop_url = "https://{}:{}@{}.myshopify.com/admin/api/{}".format(instance_id.shopify_api_key,
                                                                        instance_id.shopify_password,
                                                                        instance_id.shopify_shop,
                                                                        instance_id.shopify_version)
        try:
            shopify.ShopifyResource.set_site(shop_url)
            connection = True
        except Exception as e:
            _logger.info("{}".format(e))
            connection = False
        return connection
    def test_connection_of_instance(self):
        if self.provider != "eg_shopify":
            return super(EgEComInstance, self).test_connection_of_instance()
        shop_connection = self.get_connection_from_shopify(instance_id=self)
        if not shop_connection:
            # self.test_connection = False
            self.color = 1
            self.connection_message = "Something is wrong !!! could not connect to shopify"
            # message = "Something is wrong !!! not connect to shopify"
        
        else:
            try:

                shopify_locations=shopify.Location.find()
                # self.test_connection = True
                self.color = 10
                self.connection_message = "Connection is successful"
            except Exception as e:
                # self.test_connection = False
                self.color = 1
                if hasattr(e, 'message'):
                    self.connection_message=e.message
                else:
                    self.connection_message="Something is wrong !!! could not connect to shopify"
            
                
    @api.model
    def create_sequence_for_shopify_history(self):
        self.env["ir.sequence"].create({"name": "Shopify History Integration",
                                        "code": "eg.ecom.instance",
                                        "prefix": "SH",
                                        "padding": 3,
                                        "number_increment": 1})
    def runSync(self):
        
        for shopify_instance in self:
            if self.active:
                if shopify_instance.import_products_in_scheduler:
                    self.env["product.template"].import_product_from_shopify(shopify_instance)
                if shopify_instance.export_products_in_scheduler:
                    self.env["product.template"].export_product_in_shopify(instance_id=shopify_instance)
                if shopify_instance.import_products_in_scheduler:
                    self.env["res.partner"].import_customer_from_shopify(instance_id=shopify_instance)
                if shopify_instance.import_products_in_scheduler:
                    self.env["sale.order"].import_sale_order_from_shopify(instance_id=shopify_instance,
                                                                    product_create=True)
                if shopify_instance.sync_inventory_to_shopify:
                    self.env["product.template"].SyncInventory(instance_id=shopify_instance)

    def ScheduledActionForShopify(self):
        shopify_instances=self.env["eg.ecom.instance"].search([('active','=',True)])
        shopify_instances.runSync()   

    def get_connection_from_shopify(self, instance_id=None):
        shop_url = "https://{}:{}@{}.myshopify.com/admin/api/{}".format(instance_id.shopify_api_key,
                                                                        instance_id.shopify_password,
                                                                        instance_id.shopify_shop,
                                                                        instance_id.shopify_version)
        try:
            shopify.ShopifyResource.set_site(shop_url)
            connection = True
        except Exception as e:
            _logger.info("{}".format(e))
            connection = False
        return connection

    def update_shopify_locations(self):
        connection = self.get_connection_from_shopify(instance_id=self)
        if not connection:
            return
        shopify_locations = shopify.Location.find()

        for location in shopify_locations:
            existing_location = self.env['eg.inventory.location'].search([('location_id','=',location.id)])
            if not existing_location:
                location = location.to_dict()
                data={}
                data['location_id'] = location['id']
                data['instance_id'] = self.id
                data['name'] = location['name']
                data['city'] = location['city']
                self.env['eg.inventory.location'].create(data)
        # raise UserError(str(shopify_locations))
        # raise UserError(str("Button Clicked"))