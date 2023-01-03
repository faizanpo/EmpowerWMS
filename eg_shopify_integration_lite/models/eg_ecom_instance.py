from odoo import models, fields, api


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

    def test_connection_of_instance(self):
        if self.provider != "eg_shopify":
            return super(EgEComInstance, self).test_connection_of_instance()
        shop_connection = self.env["product.template"].get_connection_from_shopify(instance_id=self)
        if shop_connection:
            # self.test_connection = True
            self.color = 10
            self.connection_message = "Connection is successful"
            # message = "Connection is successful"
        else:
            # self.test_connection = False
            self.color = 1
            self.connection_message = "Something is wrong !!! not connect to shopify"
            # message = "Something is wrong !!! not connect to shopify"

    @api.model
    def create_sequence_for_shopify_history(self):
        self.env["ir.sequence"].create({"name": "Shopify History Integration",
                                        "code": "eg.ecom.instance",
                                        "prefix": "SH",
                                        "padding": 3,
                                        "number_increment": 1})

    def ScheduledActionForShopify(self):
        shopify_instances=self.env["eg.ecom.instance"].search([('active','=',True)])
        for shopify_instance in shopify_instances:
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
