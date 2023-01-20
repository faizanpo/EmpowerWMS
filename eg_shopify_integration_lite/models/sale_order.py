import logging
from datetime import datetime
import requests
from odoo import models, fields,api
from odoo.exceptions import Warning, UserError

try:
    import shopify
except ImportError:
    raise ImportError(
        'This module needs shopify library to connect with shopify. Please install ShopifyAPI on your system. (sudo pip3 install ShopifyAPI)')

_logger = logging.getLogger("==== Sale Order ====")


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    source_name=fields.Char('Order Source')
    shopify_instance_id=fields.Many2one('eg.ecom.instance','Shopify Instance')
    #Asir
    shopify_payment_gateway = fields.Char(String = "Shopify Payment Gateway")
    shopify_order_notes = fields.Char(String = "Shopify Order Notes")
    eg_account_journal_id = fields.Many2one(comodel_name="eg.account.journal", string="Payment Gateway")

    # Anique
    status_needs_to_be_updated = fields.Boolean(string='Status Needs To Be Updated',default=False)
    shopify_status_sync = fields.Char(string='Shopify Status Sync')


    def import_sale_order_from_shopify(self, instance_id=None, product_create=None, product_image=None, cron=None):
        instance_ids = [instance_id]
        for instance_id in instance_ids:
            status = "no"
            text = ""
            partial = False
            history_id_list = []
            line_partial_list = []

            shop_connection = self.get_connection_from_shopify(instance_id=instance_id)
            if shop_connection:
                next_page_url = None
                count = 1
                while count > 0:
                    try:
                        if next_page_url:
                            response = shopify.Order.find(from_=next_page_url)
                        elif cron == "yes" and instance_id.spf_last_order_date:
                            response = shopify.Order.find(limit=250,
                                                          created_at_min=instance_id.spf_last_order_date.strftime(
                                                              "%Y-%m-%dT%H:%M:%S"))
                        else:
                            response = shopify.draft_order.DraftOrder.find(limit=250)
                    except Exception as e:
                        raise Warning("{}".format(e))
                    
                    if response:
                        tax_add_by = instance_id.tax_add_by
                        if cron == "yes":  # TODO : New Changes by akash
                            last_date_order = datetime.strptime(response[0].created_at[0:19], "%Y-%m-%dT%H:%M:%S")
                            instance_id.write({"spf_last_order_date": last_date_order})
                        for order in response:
                            order = order.to_dict()
                            line_partial = False
                            sale_order_id = None
                            status = "no"
                            text = ""
                            if order.get("customer") and order.get("customer").get("default_address"):
                                eg_order_id = self.env["eg.sale.order"].search(
                                    [("inst_order_id", "=", str(order.get("id"))),
                                     ("instance_id", "=", instance_id.id)])
                                if not eg_order_id:  # TODO New Change
                                    order_id = self.search([("name", "=", order.get("name")),('company_id','=',instance_id.company_id.id)])
                                    eg_journal_id = None
                                    if order.get("gateway"):
                                        gateway = order.get("gateway").capitalize()
                                        if gateway:
                                            eg_journal_id = self.find_journal_account_id(gateway=gateway,
                                                                                         instance_id=instance_id)
                                    if order_id:
                                        eg_order_id = self.env["eg.sale.order"].create(
                                            {"odoo_order_id": order_id.id,
                                             "instance_id": instance_id.id,
                                             "shopify_order_notes": order_id.shopify_order_notes,
                                             "shopify_payment_gateway": order_id.shopify_payment_gateway,
                                             "eg_account_journal_id": eg_journal_id and eg_journal_id.id or None,
                                             "inst_order_id": str(
                                                 order.get("id")),
                                             "update_required": False})
                                        status = "yes"
                                        sale_order_id = order_id
                                    else:
                                        billing_partner_id = None
                                        shipping_partner_id = None
                                        partner_id = None
                                        #Asir
                                        notes = ''
                                        payment_gateway_names = ''
                                        if order.get("note"):
                                            notes = order.get("note")
                                        if order.get("payment_gateway_names"):
                                            for pgn in order.get("payment_gateway_names"):
                                                payment_gateway_names += pgn
                                        if order.get("billing_address"):
                                            billing_partner_id = self.env[
                                                "res.partner"].import_customer_from_shopify(
                                                billing_partner=True, instance_id=instance_id, order=order)
                                        if order.get("shipping_address"):
                                            shipping_partner_id = self.env[
                                                "res.partner"].import_customer_from_shopify(
                                                shipping_partner=True, instance_id=instance_id, order=order)
                                            # raise UserError(str(shipping_partner_id))
                                        if billing_partner_id and shipping_partner_id:
                                            partner_id = billing_partner_id.parent_id or billing_partner_id or ""
                                        
                                        if partner_id:
                                            create_date = order.get("created_at")
                                            create_date = create_date.replace("T", " ")
                                            create_date = create_date[0:19]
                                            create_date = datetime.strptime(create_date,
                                                                            "%Y-%m-%d %H:%M:%S")
                                              
                                            order_dict = {"partner_id": partner_id.id,
                                                          "date_order": create_date,
                                                          "shopify_order_notes": notes,
                                                          'state':'sale',
                                                          'source_name':"Shopify : "+instance_id.name,
                                                          'shopify_instance_id':instance_id.id,
                                                          'company_id':instance_id.company_id.id,
                                                          "shopify_payment_gateway": payment_gateway_names,
                                                          "partner_invoice_id": billing_partner_id.id,
                                                          "partner_shipping_id": shipping_partner_id.id,
                                                          "eg_account_journal_id": eg_journal_id and eg_journal_id.id or None}
                                            if instance_id.spf_order_name == "shopify":
                                                order_dict.update({"name": order.get("name")})

                                            # Order Payment Terms
                                            if order.get('payment_terms'):
                                                if order.get('payment_terms')['payment_terms_type'] == 'receipt':
                                                    payment_term = self.env['account.payment.term'].search([('name','=','On Receipt')])
                                                    if not payment_term:
                                                        payment_term = self.env['account.payment.term'].create({'name':"On Receipt"})
                                                    order_dict['payment_term_id'] = payment_term.id
                                                elif order.get('payment_terms')['payment_terms_type'] == 'fulfillment':
                                                    payment_term = self.env['account.payment.term'].search([('name','=','On Fulfillment')])
                                                    if not payment_term:
                                                        payment_term = self.env['account.payment.term'].create({'name':"On Fulfillment"})
                                                    order_dict['payment_term_id'] = payment_term.id
                                                elif order.get('payment_terms')['payment_terms_type'] == 'fixed':
                                                    payment_term = self.env['account.payment.term'].search([('name','=','{}'.format(order.get('payment_terms')['created_at'][:10]))])
                                                    if not payment_term:
                                                        payment_term = self.env['account.payment.term'].create({'name':'{}'.format(order.get('payment_terms')['created_at'][:10])})
                                                    order_dict['payment_term_id'] = payment_term.id
                                                elif order.get('payment_terms')['payment_terms_type'] == 'net':
                                                    payment_term_line = self.env['account.payment.term.line'].search([('days','=',order.get('payment_terms')['due_in_days'])])
                                                    if payment_term_line:
                                                        payment_term = payment_term_line.payment_id
                                                        order_dict['payment_term_id'] = payment_term[0].id
                                                    else:
                                                        payment_term = self.env['account.payment.term'].create({
                                                            'name':'{} Days'.format(str(order.get('payment_terms')['due_in_days']))
                                                            })
                                                        payment_term_line = self.env['account.payment.term.line'].create({
                                                            'days':order.get('payment_terms')['due_in_days'],
                                                            'payment_id':payment_term.id
                                                        })
                                                        order_dict['payment_term_id'] = payment_term.id

                                            order_id = self.create([order_dict])
                                            product_list = []

                                            """ Add Shipping Lines - Anique
                                            If we have a shipping line in the order then we add a shipping_product 
                                            in the order lines with the appropriate price coming from the shopify order"""

                                            if order.get('shipping_line'):
                                                shipping_product = self.env['product.product'].search([('name','=',order.get('shipping_line')['title'])])
                                                if not shipping_product:
                                                    shipping_product = self.env['product.product'].create({
                                                        "name":order.get('shipping_line')['title'],
                                                        'company_id':instance_id.company_id.id,
                                                          'source_name':"Shopify : "+instance_id.name,
                                                          'shopify_instance_id':instance_id.id,
                                                          'detailed_type':'service',
                                                    })
                                                order_line_id = self.env["sale.order.line"].create(
                                                            {"product_id": shipping_product.id,
                                                            "name": shipping_product.name,
                                                            "product_uom_qty": 1,
                                                            "price_unit": order.get('shipping_line')['price'],
                                                            "order_id": order_id.id, })

                                            """Add Discount Lines similiar to shipping lines"""
                                            if order.get('applied_discount'):
                                                discount_product = self.env['product.product'].search([('name','=',order.get('applied_discount')['description']),('company_id','=',instance_id.company_id.id)])
                                                if not discount_product:
                                                    discount_product = self.env['product.product'].create({
                                                        "name":order.get('applied_discount')['description'],
                                                        'company_id':instance_id.company_id.id,
                                                          'source_name':"Shopify : "+instance_id.name,
                                                          'shopify_instance_id':instance_id.id,
                                                          'detailed_type':'service',
                                                    })
                                                order_line_id = self.env["sale.order.line"].create(
                                                            {"product_id": discount_product.id,
                                                            "name": discount_product.name,
                                                            "product_uom_qty": 1,
                                                            "price_unit": -float(order.get('applied_discount')['amount']),
                                                            "order_id": order_id.id, })
                                            

                                            for line_item in order.get("line_items"):
                                                #Asir - adding company_id
                                                eg_product_id = self.env["eg.product.product"].search(
                                                    [("inst_product_id", "=", str(line_item.get("variant_id"))),
                                                     ("instance_id", "=", instance_id.id), ("company_id", "=", instance_id.company_id.id)])
                                                if not eg_product_id:
                                                    if not product_create:
                                                        order_id.unlink()
                                                        order_id = None  # TODO New Change
                                                        sale_order_id = None
                                                        line_partial = True
                                                        line_partial_list.append(line_partial)
                                                        text = "This product {} is not mapping so not create order".format(
                                                            line_item.get("name"))
                                                        _logger.info(
                                                            "This product {} is not mapping so not create order".format(
                                                                line_item.get("name")))
                                                        break
                                                    else:
                                                        if line_item.get("product_id"):
                                                            product_id = self.env[
                                                                "product.template"].import_product_from_shopify(
                                                                instance_id=instance_id,
                                                                product_image=product_image,
                                                                default_product_id=line_item.get("product_id"))
                                                            #Asir - adding company_id
                                                            eg_product_id = self.env["eg.product.product"].search(
                                                                [("inst_product_id", "=",
                                                                  str(line_item.get("variant_id"))),
                                                                 ("instance_id", "=", instance_id.id),("company_id", "=", instance_id.company_id.id)])
                                                if eg_product_id:
                                                    order_line_id = self.env["sale.order.line"].create(
                                                        {"product_id": eg_product_id.odoo_product_id.id,
                                                         "name": line_item.get("name"),
                                                         "product_uom_qty": line_item.get("quantity"),
                                                         "price_unit": line_item.get("price"),
                                                         "order_id": order_id.id, })
                                                    if tax_add_by and tax_add_by == "shopify":
                                                        tax_list = self.find_tax_for_product(line_item=line_item)
                                                        if tax_list:
                                                            order_line_id.write({"tax_id": [(6, 0, tax_list)]})
                                                    status = "yes"
                                                    sale_order_id = order_id
                                                else:
                                                    product_list.append(line_item.get("name"))
                                                    text = "This Sale order is create but this products {} is not" \
                                                           "mapping so not add in sale order line".format \
                                                        (product_list)
                                                    sale_order_id = order_id
                                                    line_partial = True
                                                    line_partial_list.append(line_partial)
                                            if order_id:
                                                eg_order_id = self.env["eg.sale.order"].create(
                                                    {"odoo_order_id": order_id.id,
                                                     "instance_id": instance_id.id,
                                                     "shopify_order_notes": order_id.shopify_order_notes,
                                                     "shopify_payment_gateway": order_id.shopify_payment_gateway,
                                                     "eg_account_journal_id": eg_journal_id and eg_journal_id.id
                                                                              or None,
                                                     "inst_order_id": str(
                                                         order.get("id")),
                                                     "update_required": False})
                                        else:
                                            text = "This sale order {} is not create because customer is not mapping".format(
                                                order.get("name"))
                                            partial = True
                                            status = "no"
                                            _logger.info(
                                                "This sale order {} is not create because customer is not mapping".format(
                                                    order.get("name")))
                                else:
                                    status = "yes"
                                    continue  # TODO New Change
                            else:
                                text = "This Sale order {} is not create because customer is guest".format(
                                    order.get("name"))
                                partial = True
                                status = "no"
                                _logger.info("This Sale order {} is not create because customer is guest")
                            if line_partial:
                                status = "partial"
                            elif not line_partial and status == "yes":
                                text = "This order is created"
                            eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                                "status": status,
                                                                                "process_on": "order",
                                                                                "process": "a",
                                                                                "instance_id": instance_id.id,
                                                                                "order_id": sale_order_id and sale_order_id.id or None,
                                                                                "child_id": True})
                            history_id_list.append(eg_history_id.id)
                        next_page_url = response.next_page_url
                        if not next_page_url:
                            break
                    else:
                        text = "Not get response from shopify"
                        break
            else:
                text = "Not Connect to store !!!"
            partial_value = True
            if partial or partial_value in line_partial_list:
                text = "Some order was created and some order is not create"
                status = "partial"
            if status == "yes" and not partial and partial_value not in line_partial_list:
                text = "All Order was successfully created"
            if not history_id_list:  # TODO New Change
                status = "yes"
                text = "All order was already mapped"
            eg_history_id = self.env["eg.sync.history"].create({"error_message": text,
                                                                "status": status,
                                                                "process_on": "order",
                                                                "process": "a",
                                                                "instance_id": instance_id.id,
                                                                "parent_id": True,
                                                                "eg_history_ids": [(6, 0, history_id_list)]})

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

    def find_journal_account_id(self, gateway=None, instance_id=None):
        eg_journal_id = None
        if gateway and instance_id:
            eg_journal_id = self.env["eg.account.journal"].search(
                [("name", "=", gateway), ("instance_id", "=", instance_id.id)])
            if not eg_journal_id:
                odoo_journal_id = self.env["account.journal"].search(
                    [("name", "=", gateway)])
                if not odoo_journal_id:
                    odoo_journal_id = self.env["account.journal"].create({"name": gateway,
                                                                          "type": "bank",
                                                                          "code": gateway[
                                                                                  0:3].upper()})
                if odoo_journal_id:
                    eg_journal_id = self.env["eg.account.journal"].create(
                        {"odoo_account_journal_id": odoo_journal_id.id,
                         "instance_id": instance_id.id})
        return eg_journal_id

    def find_tax_for_product(self, line_item=None):
        tax_list = []
        if line_item:
            for tax_line in line_item.get("tax_lines"):
                rate = tax_line.get("rate") * 100
                name = "{} {}%".format(tax_line.get("title"), int(rate))
                tax_id = self.env["account.tax"].search(
                    [("name", "=", name), ("amount", "=", rate), ("amount_type", "=", "percent"),
                     ("type_tax_use", "=", "sale")], limit=1)
                if not tax_id:
                    tax_group_id = self.env["account.tax.group"].search([("name", "=", tax_line.get("title"))], limit=1)
                    if not tax_group_id:
                        tax_group_id = self.env["account.tax.group"].create({"name": tax_line.get("title")})
                    tax_id = self.env["account.tax"].create({"name": name,
                                                             "amount": rate,
                                                             "amount_type": "percent",
                                                             "type_tax_use": "sale",
                                                             "tax_group_id": tax_group_id.id,
                                                             "description": name
                                                             })
                tax_list.append(tax_id.id)
        return tax_list
        
    def sync_status(self,instance_id):
        # # """The status of the order must sync with order status on shopify"""
        self.get_connection_from_shopify(instance_id=instance_id)
        payload={}
        headers = {
        'X-Shopify-Access-Token': str(instance_id.shopify_password),
        'Content-Type': 'application/json',
        'Cookie': 'request_method=POST'
        }

        sale_orders = self.env['sale.order'].search([('status_needs_to_be_updated','=',True)])
        for sale_order in sale_orders:
            eg_sale_order = self.env['eg.sale.order'].search([('odoo_order_id','=',sale_order.id)])
            try:
                shopify_order = shopify.Order.find(eg_sale_order.inst_order_id)
                if sale_order.state =='cancel':
                    url = '{0}/admin/api/{1}/orders/{2}/{3}.json'.format(instance_id.url,instance_id.shopify_version,shopify_order.id,'cancel')
                    requests.request("POST", url, headers=headers, data=payload)
                elif sale_order.state == 'done':
                    url = '{0}/admin/api/{1}/orders/{2}/{3}.json'.format(instance_id.url,instance_id.shopify_version,shopify_order.id,'close')
                    requests.request("POST", url, headers=headers, data=payload)
                sale_order.shopify_status_sync = 'Synced'
            except:
                sale_order.shopify_status_sync = 'Failed to Sync'
            sale_order.status_needs_to_be_updated = False


