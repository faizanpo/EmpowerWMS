import datetime

from odoo import models, fields
from odoo.exceptions import UserError
import base64
import requests


class SaleOrder(models.Model):
    _inherit = "sale.order"
    source_ecommerce2 = fields.Char("Source Ecommerce")
    payment_method = fields.Char("Payment Method")


class ProductsWoo(models.Model):
    _name = 'woocommerce.main'
    name = fields.Char("Name")
    url = fields.Char("Url")
    consumer_key = fields.Char("Consumer Key")
    consumer_secret = fields.Char("Consumer Secret")
    company_id = fields.Many2one('res.company')
    warehouse_id = fields.Many2one('stock.warehouse')
    location_id = fields.Many2one('stock.location')

    color = fields.Integer(string='Color Index')
    # sub_instance_ids= fields.One2many("woocommerce.sub.instances","main_instances_id",string="Main Instence")

    product_w_o_active=fields.Boolean("Activate")
    product_w_o_dely = fields.Integer("Dely In Minutes")
    product_w_o_from_date = fields.Date("From Date")
    product_w_o_log_ids = fields.One2many("woocommerce.product.logs", "main_id", string="Logs", readonly="True")

    product_o_w_active=fields.Boolean("Activate")
    product_o_w_from_date = fields.Date("From Date")
    product_o_w_dely = fields.Integer("Dely In Minutes")
    product_o_w_log_ids = fields.One2many("woocommerce.product.down.logs", "main_id", string="Logs", readonly="True")

    orders_w_o_active = fields.Boolean("Activate")
    orders_w_o_from_date = fields.Date("From Date")
    orders_w_o_dely = fields.Integer("Delay In Minutes")
    orers_w_o_log_ids = fields.One2many("woocommerce.orders.logs", "main_id", string="Logs", readonly="True")

    produpdate_o_w_active=fields.Boolean("Activate")
    produpdate_o_w_from_date = fields.Date("From Date")
    produpdate_o_w_price = fields.Boolean("Update Price")
    produpdate_o_w_inventory = fields.Boolean("Update Inventory")
    produpdate_o_w_dely = fields.Integer("Dely In Minutes")
    produpdate_o_w_log_ids = fields.One2many("woocommerce.product.update.logs", "main_id", string="Logs", readonly="True")
    Schedule_actions=fields.Many2one('ir.cron',"Schedule Action")

    orders_status_w_o_active = fields.Boolean("Activate")
    orers_w_o_status_log_ids = fields.One2many("woocommerce.orders.status.logs", "main_id", string="Logs", readonly="True")
    orers_w_o_status_from_date = fields.Date(string="From Date",required=True)
    categoryUpdate_w_o_active = fields.Boolean("Activate")
    def upload_product(self):
        try:
            if self.product_w_o_active:
                wcapi = API(
                    url=self.url,
                    consumer_key=self.consumer_key,
                    consumer_secret=self.consumer_secret,
                    version="wc/v3",
                    query_string_auth=True,
                    verify_ssl=False
                )
                prodobj = self.env['product.product']
                page = 1
                woo_products=[]
                r = wcapi.get("products/", params={"per_page": 100, "page": page}).json()
                woo_products.extend(r)
                if woo_products[0] != 'code':
                    while r != []:
                        page += 1
                        r = wcapi.get("products/",
                                      params={"per_page": 10, "page": page, "after": DN + "T00:00:00"}).json()
                        woo_products.extend(r)

                    skuslist = []
                    for wd in r:
                        skuslist.append(wd['sku'])
                    for op in prodobj.search([("company_id",'=',self.company_id.id)]):
                        if not op.default_code in skuslist:
                            prodcreate = {
                                'name': op['name'],
                                'status': 'draft',
                                'description': op['description'] if op['description'] else '',
                                'sku': op['default_code'],
                                'manage_stock': True,
                                'stock_quantity': str(op['qty_available']),
                            }
                            created = wcapi.post("products", prodcreate).json()
                            # raise UserError(str(created))
                            if 'id' in created.keys():
                                # self.env.cr.execute("INSERT INTO woocommerce_product_logs (odoo_id,woo_id,sku,status,details,sub_instances_id) VALUES ("+str(op.id)+","+str(created['id'])+",'"+created['sku']+"','complete','Order Has Been Created Scussfully',"+str(self.id)+")")
                                create_log = {
                                    'odoo_id': op.id,
                                    'woo_id': created['id'],
                                    'sku': created['sku'],
                                    'status': 'complete',
                                    'details': "Order Has Been Created Scussfully",
                                    'sub_instances_id': self.id
                                }

                                woocommcreate = self.env['woocommerce.product.logs'].create(create_log)
                            else:
                                self.env['woocommerce.product.logs'].create({
                                    'odoo_id': op.id,
                                    'sku': created['sku'],
                                    'status': 'error',
                                    'details': str(created),
                                    'sub_instances_id': self.id
                                })
                else:
                    raise UserError("Activate it first!!")
        except:
            return 0

    def download_product(self):
        self.update_categories()
        try:
            if self.product_o_w_active:
                if self.product_o_w_from_date:
                    DN = str(self.product_o_w_from_date.strftime("%Y-%m-%d"))
                    wcapi = API(
                        url=self.url,
                        consumer_key=self.consumer_key,
                        consumer_secret=self.consumer_secret,
                        version="wc/v3",
                        query_string_auth=True,
                        verify_ssl=False
                    )
                    prodobj=self.env['product.product']
                    page=1
                    woo_products=[]
                    r = wcapi.get("products/", params={"per_page": 10, "page": page,"after":DN + "T00:00:00"}).json()
                    woo_products.extend(r)
                    if woo_products[0] != 'code':
                        while r != []:
                            page+=1
                            r = wcapi.get("products/", params={"per_page": 10, "page": page,"after":DN + "T00:00:00"}).json()
                            woo_products.extend(r)
                        skuslist=[]
                        allodooproduct=prodobj.search([('company_id','=',self.company_id.id)])
                        for wo in allodooproduct:
                            skuslist.append(wo.default_code)
                        for wo in woo_products:
                            try:
                                # print(wo)
                                # raise UserError(wo)
                                def pass_image(image_url):                                 
                                    bin = base64.b64encode(requests.get(image_url.strip()).content).replace(b"\n", b"")
                                    return bin  # or you could print it
                                if not wo['sku'] in skuslist:
                                    categ_id=self.env["product.category"].search([('id','=',1)]) ##selecting default category as 1
                                    ##if Id provided, we select the first one
                                    for category in wo["categories"]:
                                        categ_id = self.env["product.category"].search([('name','=',category['name'])])
                                        break
                                    prodcreate={
                                        'name': wo['name'],
                                        'description': wo['description'] if wo['description'] else '',
                                        'default_code': wo['sku'],
                                        'type':'product',
                                        "company_id": self.company_id.id,
                                        "categ_id":categ_id.id,
                                        # 'qty_available': float(wo['stock_quantity']),
                                        # 'price': float(wo['regular_price']),
                                        'list_price': float(wo['regular_price']) if wo['regular_price'] else 0,
                                        'image_1920':pass_image(wo['images'][0]['src']) if wo['images'] else False
                                    }
                                    created= prodobj.create(prodcreate)

                                    create_quant=self.env['stock.quant'].sudo().create({
                                        'product_id':created.id,
                                        'location_id':self.location_id.id,
                                        'quantity':0 ## special requirement of empower. Quantity will be zero for the first time. Quantity will be put in manually be user later. 
                                    })

                                    create_log={
                                        'odoo_id':created.id,
                                        'woo_id':wo['id'],
                                        'sku':wo['sku'],
                                        'status':'complete',
                                        'details':"Product Has Been Created Scussfully",
                                        'main_id':self.id
                                    }

                                    woocommcreate=self.env['woocommerce.product.down.logs'].create(create_log)
                                    self.product_o_w_from_date = datetime.datetime.now().date()

                            except Exception as e:
                                print(e)
                                created=self.env['woocommerce.product.down.logs'].create({
                                    'woo_id': wo['id'],
                                    'sku': wo['sku'],
                                    'status': 'error',
                                    'details': str(e),
                                    'main_id': self.id
                                })
                    else:
                        raise UserError("Date Field Not Set")
                else:
                    raise UserError("Activate it first!!")
                self.update_product()
            return 1
        except:
            return 0
    def update_status(self):
        DN=str(self.orers_w_o_status_from_date.strftime("%Y-%m-%d"))
        anyError=False
        # write_date
        # 2022-02-19 08:18:02
        # raise UserError(str(self.orers_w_o_status_from_date))
        if self.orders_status_w_o_active:
            orders=self.env['sale.order'].search([("company_id",'=',self.company_id.id),('source_ecommerce2', '=', self.name)])
            wcapi = API(
                url=self.url,
                consumer_key= self.consumer_key,
                consumer_secret= self.consumer_secret,
                version="wc/v3",
                query_string_auth=True,
                verify_ssl=False
                )
            page=1
            r=False
            try:
                r = wcapi.get("orders", params={"per_page": 100,"page":page}).json()
            except Exception as e:
                anyError=True

            while r:
                for odo in orders:
                    for woo in r:
                        if str(woo['id'])==odo['origin']:

                            status=None

                            if str(odo['state'])=="sale":
                                if str(odo['invoice_status'])=="invoiced":

                                    odoo_invoice=self.env['account.move'].search([('id', '=', odo['invoice_ids'][0].id)])

                                    odo_invoice_status=odoo_invoice[0]['payment_state']

                                    # print(odo_invoice_status)

                                    if odo_invoice_status=="paid" and woo['status'] != "completed":
                                        status="completed"
                                    elif odo_invoice_status=="canceled" and woo['status'] != "canceled":
                                        status="canceled"
                                    elif odo_invoice_status=="not_paid" and woo['status'] != "processing":
                                        status="processing"
                                else:
                                    status="processing"
                            
                            elif str(odo['state'])=="draft" and woo['status'] != 'processing':
                                status="processing"
                            
                            elif (str(odo['state'])=="canceled" and woo['status'] != 'canceled'):
                                status="canceled"

                            if status:
                                data = {"status": status}
                                try:
                                    response_woo=wcapi.put("orders/"+str(woo['id']), data).json()
                                    updated = response_woo
                                except Exception as e:
                                    create_log = {
                                                    'odoo_id': odo['origin'],
                                                    'woo_id': woo['id'],
                                                    'status': 'error',
                                                    'details': e,
                                                    'main_id': self.id
                                                }
                                    anyError=True
                                if 'id' in updated.keys():
                                    print("Odoo Status : "+str(odo['state']) + " - Woo Old status : "+woo['status'] + " - New Status : "+status)
                                    create_log = {
                                                    'odoo_id': odo['origin'],
                                                    'woo_id': woo['id'],
                                                    'status': 'complete',
                                                    'details': "Status Updated from " + woo['status'] +" to " + status ,
                                                    'main_id': self.id
                                                }
                                else:
                                    create_log = {
                                                    'odoo_id': odo['origin'],
                                                    'woo_id': woo['id'],
                                                    'status': 'error',
                                                    'details': "Error",
                                                    'main_id': self.id
                                                }
                                    anyError=True
                                self.env['woocommerce.orders.status.logs'].create(create_log)

                try:
                    page+=1
                    r = wcapi.get("orders", params={"per_page": 100,"page":page}).json()
                    
                    if r:
                        pass
                    else:
                        break
                    
                except Exception as e:
                    anyError=True
                
                if not anyError:
                    self.orers_w_o_status_from_date = datetime.datetime.now().date()

            

            # raise UserError(str(self.name))
        else:
            raise UserError("Active First");
    
    def recursive_add_category_with_parent(self,woocategory,woocategories):
        category_found = self.env['product.category'].search([('name','=',woocategory['name'])])
        if category_found:
            return category_found[0]
        if woocategory['parent'] == 0:
            all_parent_category = self.env['product.category'].search([('name','=','All')])
            category_id = self.env['product.category'].create({'name':woocategory['name'],'parent_id':all_parent_category.id})
            return category_id
        for checkingCategory in woocategories:
            if checkingCategory['id']==woocategory['parent']:
                parent_id = self.recursive_add_category_with_parent(checkingCategory,woocategories)
                category_id = self.env['product.category'].create({'name':woocategory['name'],'parent_id':parent_id.id})
                
                return category_id

        

    def update_categories(self):
        if self.categoryUpdate_w_o_active:
            wcapi = API(
                    url=self.url,
                    consumer_key=self.consumer_key,
                    consumer_secret=self.consumer_secret,
                    version="wc/v3",
                    query_string_auth=True,
                    verify_ssl=False
                    )
            categories = []
            page=1
            while True:
                response = wcapi.get('products/categories',params={"per_page":10,"page":page}).json()
                if response==[]:
                        break
                categories.extend(response)
                page=page+1

            for category in categories:
                self.recursive_add_category_with_parent(category,categories)
            return categories
        return



    def update_product(self):
        
        try:
            
            if self.produpdate_o_w_active:

                wcapi = API(
                    url=self.url,
                    consumer_key=self.consumer_key,
                    consumer_secret=self.consumer_secret,
                    version="wc/v3",
                    query_string_auth=True,
                    verify_ssl=False
                )
                prodobj=self.env['product.product']
                page=1
                woo_products=[]
                r = wcapi.get("products/", params={"per_page": 10, "page": page}).json()
                woo_products.extend(r)
                
                if woo_products[0] != 'code':
                    while r != []:

                        page+=1
                        r = wcapi.get("products/", params={"per_page": 10, "page": page}).json()
                        woo_products.extend(r)

                    skuslist=[]
                    price_list=[]
                    inventory_list=[]
                    odoo_ids=[]

                    allodooproduct=prodobj.search([('company_id',"=",self.company_id.id)])
                    for wo in allodooproduct:
                        qty_inv=self.env['stock.quant'].search([('product_id','=',wo.id),('quantity','>=',0),('location_id','=',self.location_id.id)])
                        skuslist.append(wo.default_code)
                        price_list.append(wo.lst_price)
                        inventory_list.append(qty_inv.available_quantity)
                        odoo_ids.append(wo.id)
                    for wo in woo_products:
                        try:
                            update={}
                            details=""
                            for i,sku in enumerate(skuslist):
                                if sku == wo['sku']:
                                    if wo['regular_price'] != str(price_list[i]) and self.produpdate_o_w_price:
                                        details="Updated Price Woocommerce="+wo['regular_price']+", Odoo="+str(price_list[i])
                                        update['regular_price']=str(price_list[i])
                                        
                                        
                                    if float(wo['stock_quantity']) != float(inventory_list[i]) and self.produpdate_o_w_inventory:
                                        
                                        update['stock_quantity'] = str(inventory_list[i])
                                        if details:
                                            details =details + "<br></br>Updated Stock Woocommerce=" + str(wo['stock_quantity']) + ", Odoo=" + str(inventory_list[i])
                                        else:
                                            details="Updated Stock Woocommerce=" + str(wo['stock_quantity']) + ", Odoo=" + str(inventory_list[i])

                                    if update:
                                        response_woo=wcapi.put("products/" + str(wo['id']), update)
                                        updated = response_woo.json()
                                        if 'id' in updated.keys():
                                            create_log = {
                                                'odoo_id': odoo_ids[i],
                                                'woo_id': updated['id'],
                                                'sku': updated['sku'],
                                                'status': 'complete',
                                                'details': details,
                                                'main_id': self.id
                                            }
                                            self.env['woocommerce.product.update.logs'].create(create_log)
                                        else:
                                            create_log = {
                                                'odoo_id': odoo_ids[i],
                                                'sku': sku,
                                                'status': 'error',
                                                'details': updated['message'],
                                                'main_id': self.id
                                            }
                                            self.env['woocommerce.product.update.logs'].create(create_log)
                        except Exception as e:
                            print(e)
                            created=self.env['woocommerce.product.update.logs'].create({
                                'woo_id': wo['id'],
                                'sku': wo['sku'],
                                'status': 'error',
                                'details': str(e),
                                'main_id': self.id
                            })
                else:
                    raise UserError("Activate it first!!")
            return 1
        except Exception as e:
            return 0
    def download_orders(self):
        try:
            self.orders_w_o_dely = 1
            if self.orders_w_o_active:
                if self.orders_w_o_from_date:
                    print("orders Function")

                    wcapi = API(
                        url=self.url,
                        consumer_key=self.consumer_key,
                        consumer_secret=self.consumer_secret,
                        version="wc/v3",
                        query_string_auth=True,
                        verify_ssl=False
                    )

                    def findIDbyEmail(data,type):
                        address2=data['address_2'] + ' ' + data['city'] + ' ' + data['country']
                        customer = self.env['res.partner'].search([
                            ('street', '=',data['address_1']),
                            ('street2', '=', address2),
                            ('zip', '=', data['postcode']),
                            ('mobile', '=', data['phone']),
                        ])
                        if customer:
                            return customer
                        else:
                            d_customer = {
                                'name': data['first_name'] + ' ' + data['last_name'],
                                'street': data['address_1'],
                                'street2': address2,
                                'zip': data['postcode'],
                                'commercial_company_name': data['company'],
                                'company_type': 'person',
                                'company_id':self.company_id.id,
                                'mobile': data['phone'],
                                'email': data['email'] if 'email' in data.keys() else '',
                                'type': type
                            }

                            created_customer=self.env['res.partner'].create(d_customer)
                            return created_customer

                    woo_orders = []
                    page=1
                    DN=str(self.orders_w_o_from_date.strftime("%Y-%m-%d"))
                    # Schedule_actions = fields.Many2one(comodel_name='ir.cron', string="Cron Job")
                    r = wcapi.get("orders/", params={"per_page": 100, "page": page,"after":DN + "T00:00:00"}).json()
                    woo_orders.extend(r)
                    if woo_orders[0] != 'code':
                        while r != []:
                            page += 1
                            r = wcapi.get("orders/", params={"per_page": 100, "page": page,"after":DN + "T00:00:00"}).json()
                            woo_orders.extend(r)
                        print(woo_orders)
                        for wo in woo_orders:
                            try:
                                billing_customer=0
                                shipping_customer=0
                                billing_obj=0
                                if 'billing' in wo.keys():
                                    billing_obj=findIDbyEmail(wo['billing'],'invoice')
                                    billing_customer=billing_obj.id
                                if 'shipping' in wo.keys():
                                    ship=wo['shipping']
                                    if ship['address_1'] or ship['address_2']:
                                        shipping_customer=findIDbyEmail(wo['shipping'],'delivery').id
                                    else:
                                        if 'phone' not in ship.keys():
                                            wo['shipping']['phone']='0'
                                        wo['shipping']['first_name']="Not Set"
                                        wo['shipping']['address_1'] = "Not Set"
                                        wo['shipping']['address_1'] = "Not Set"
                                        shipping_customer = findIDbyEmail(wo['shipping'], 'delivery').id
                                else:
                                    shipping_customer=billing_customer

                                products = []
                                product_found=True
                                for item in wo['line_items']:
                                    product_id = self.env['product.product'].search([("company_id",'=',self.company_id.id),('default_code', '=', item['sku'])])
                                    taxes=product_id.taxes_id.ids
                                    t_inseertt=[]
                                    for t in taxes:
                                        t_inseertt.append((4,t))
                                    # raise UserError(str(t_inseertt))
                                    if product_id:
                                        x = {
                                            'tax_id':t_inseertt if t_inseertt else False,
                                            'product_id': product_id.id,
                                            'product_uom_qty': item['quantity'],
                                            'price_unit': float(item['subtotal'])/int(item['quantity']),
                                            'tax_id':False
                                        }
                                        products.append((0, 0, x))
                                    else:
                                        product_found=False
                                ## add shipping lines
                                for item in wo['shipping_lines']:
                                    product_id = self.env['product.product'].search([("company_id","=",self.company_id.id),('default_code','=',item['method_id'])])
                                    if not product_id:
                                        product_data={
                                            "name":item["method_title"],
                                            "default_code": item['method_id'],
                                            "detailed_type":"service",
                                            "purchase_ok":False,
                                            "company_id":self.company_id.id,
                                            "price_unit":0

                                        
                                        }
                                        product_id = self.env['product.product'].create(product_data)
                                    x = {
                                            'product_id': product_id.id,
                                            'product_uom_qty': 1,
                                            'price_unit': item['total'],
                                        }
                                    products.append((0, 0, x))
                                if product_found:
                                    exisit=self.env['sale.order'].search([('origin','=',wo['id']),('company_id','=',self.company_id.id),('source_ecommerce2','=',self.name)])
                                    if not exisit:
                                        order = {
                                            'partner_id': billing_customer,
                                            'partner_invoice_id': billing_customer,
                                            'partner_shipping_id': shipping_customer,
                                            # 'pricelist_id': 2,
                                            'state':'sale',
                                            'payment_method':wo.get('payment_method_title',""),
                                            'date_order': wo['date_created'].replace('T', ' '),
                                            'order_line': products,
                                            'origin': wo['id'],
                                            'company_id':self.company_id.id,
                                            #'origin':wo['status'],
                                            'source_ecommerce2':self.name
                                        }
                                        
                                        order['internal_note']=wo["customer_note"]
                                        ##

                                        created=self.env['sale.order'].create(order)
                                        if wo['status']== 'failed':
                                            created.action_cancel()
                                        order_lines=self.env['sale.order.line'].search([('order_id','=',created.id)])
                                        for ol in order_lines:
                                            taxes=[]
                                            for t in ol.product_id.taxes_id.ids:
                                                taxes.append((4,t))
                                            ol.write({'tax_id': taxes if taxes else False})

                                        created_log=self.env['woocommerce.orders.logs'].create({
                                                'odoo_id':created.id,
                                                'woo_id': wo['id'],
                                                'customer_name': billing_obj.name,
                                                'status': 'complete',
                                                'details': "Order Has Been Created Successfully",
                                                'main_id': self.id
                                            })
                                        self.orders_w_o_from_date=datetime.datetime.now().date()
                                else:
                                    created_log = self.env['woocommerce.orders.logs'].create({
                                        'woo_id': wo['id'],
                                        'status': 'error',
                                        'details': "Product Not Found In Odoo",
                                        'main_id': self.id
                                    })

                            except Exception as e:
                                print(e)
                                created_log = self.env['woocommerce.orders.logs'].create({
                                    'woo_id': wo['id'],
                                    'status': 'error',
                                    'details': str(e),
                                    'main_id': self.id
                                })

                else:
                    raise UserError("Date Field Not Set")
            else:
                raise UserError("Activate it first!!")
            return 0
        except:
            return 0
    def run_product_download(self):
        print("inside run_product_download")
        products=self.env['woocommerce.main'].search([])
        Notrun = True
        for o in products:
            if o.product_w_o_dely == 0:
                o.product_w_o_dely=1
                Notrun = False
                o.download_product()
        if Notrun:
            for o in products:
                o.product_w_o_dely = 0

    def run_product_upload(self):
        print("inside run_product_upload")
        products=self.env['woocommerce.main'].search([])
        Notrun = True
        for o in products:
            if o.product_o_w_dely == 0:
                o.product_o_w_dely=1
                Notrun = False
                o.upload_product()
        if Notrun:
            for o in products:
                o.product_o_w_dely = 0

    def run_product_update(self):
        print("inside run_product_update")
        products=self.env['woocommerce.main'].search([])
        Notrun = True
        for o in products:
            if o.produpdate_o_w_dely == 0:
                o.produpdate_o_w_dely=1
                Notrun = False
                o.update_product()
        if Notrun:
            for o in products:
                o.produpdate_o_w_dely = 0

    def run_order_download(self):
        print("inside run_order_download")
        orders = self.env['woocommerce.main'].search([])
        Notrun=True
        for o in orders:
            if o.orders_w_o_dely == 0:
                o.write({'orders_w_o_dely': 1})
                Notrun=False
                o.download_orders()
        if Notrun:
            for o in orders:
                o.orders_w_o_dely= 0

    def run_order_update(self):
        print("inside run_order_update")
        orders = self.env['woocommerce.main'].search([])
        for o in orders:
            o.update_status()

















###############API#######################




from requests import request
from json import dumps as jsonencode
from time import time
from requests.auth import HTTPBasicAuth
from urllib.parse import urlencode
from time import time
from random import randint
from hmac import new as HMAC
from hashlib import sha1, sha256
from base64 import b64encode
from collections import OrderedDict
from urllib.parse import urlencode, quote, unquote, parse_qsl, urlparse


class OAuth(object):
    """ API Class """

    def __init__(self, url, consumer_key, consumer_secret, **kwargs):
        self.url = url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.version = kwargs.get("version", "v3")
        self.method = kwargs.get("method", "GET")
        self.timestamp = kwargs.get("oauth_timestamp", int(time()))

    def get_oauth_url(self):
        """ Returns the URL with OAuth params """
        params = OrderedDict()

        if "?" in self.url:
            url = self.url[:self.url.find("?")]
            for key, value in parse_qsl(urlparse(self.url).query):
                params[key] = value
        else:
            url = self.url

        params["oauth_consumer_key"] = self.consumer_key
        params["oauth_timestamp"] = self.timestamp
        params["oauth_nonce"] = self.generate_nonce()
        params["oauth_signature_method"] = "HMAC-SHA256"
        params["oauth_signature"] = self.generate_oauth_signature(params, url)

        query_string = urlencode(params)

        return f"{url}?{query_string}"

    def generate_oauth_signature(self, params, url):
        """ Generate OAuth Signature """
        if "oauth_signature" in params.keys():
            del params["oauth_signature"]

        base_request_uri = quote(url, "")
        params = self.sorted_params(params)
        params = self.normalize_parameters(params)
        query_params = ["{param_key}%3D{param_value}".format(param_key=key, param_value=value)
                        for key, value in params.items()]

        query_string = "%26".join(query_params)
        string_to_sign = f"{self.method}&{base_request_uri}&{query_string}"

        consumer_secret = str(self.consumer_secret)
        if self.version not in ["v1", "v2"]:
            consumer_secret += "&"

        hash_signature = HMAC(
            consumer_secret.encode(),
            str(string_to_sign).encode(),
            sha256
        ).digest()

        return b64encode(hash_signature).decode("utf-8").replace("\n", "")

    @staticmethod
    def sorted_params(params):
        ordered = OrderedDict()
        base_keys = sorted(set(k.split('[')[0] for k in params.keys()))

        for base in base_keys:
            for key in params.keys():
                if key == base or key.startswith(base + '['):
                    ordered[key] = params[key]

        return ordered

    @staticmethod
    def normalize_parameters(params):
        """ Normalize parameters """
        params = params or {}
        normalized_parameters = OrderedDict()

        def get_value_like_as_php(val):
            """ Prepare value for quote """
            try:
                base = basestring
            except NameError:
                base = (str, bytes)

            if isinstance(val, base):
                return val
            elif isinstance(val, bool):
                return "1" if val else ""
            elif isinstance(val, int):
                return str(val)
            elif isinstance(val, float):
                return str(int(val)) if val % 1 == 0 else str(val)
            else:
                return ""

        for key, value in params.items():
            value = get_value_like_as_php(value)
            key = quote(unquote(str(key))).replace("%", "%25")
            value = quote(unquote(str(value))).replace("%", "%25")
            normalized_parameters[key] = value

        return normalized_parameters

    @staticmethod
    def generate_nonce():
        """ Generate nonce number """
        nonce = ''.join([str(randint(0, 9)) for i in range(8)])
        return HMAC(
            nonce.encode(),
            "secret".encode(),
            sha1
        ).hexdigest()




__title__ = "woocommerce-api"
__version__ = "3.0.0"
__author__ = "Claudio Sanches @ Automattic"
__license__ = "MIT"


class API(object):
    """ API Class """

    def __init__(self, url, consumer_key, consumer_secret, **kwargs):
        self.url = url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.wp_api = kwargs.get("wp_api", True)
        self.version = kwargs.get("version", "wc/v3")
        self.is_ssl = self.__is_ssl()
        self.timeout = kwargs.get("timeout", 5)
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self.query_string_auth = kwargs.get("query_string_auth", False)
        self.user_agent = kwargs.get("user_agent", f"WooCommerce-Python-REST-API/{__version__}")

    def __is_ssl(self):
        """ Check if url use HTTPS """
        return self.url.startswith("https")

    def __get_url(self, endpoint):
        """ Get URL for requests """
        url = self.url
        api = "wc-api"

        if url.endswith("/") is False:
            url = f"{url}/"

        if self.wp_api:
            api = "wp-json"

        return f"{url}{api}/{self.version}/{endpoint}"

    def __get_oauth_url(self, url, method, **kwargs):
        """ Generate oAuth1.0a URL """
        oauth = OAuth(
            url=url,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            version=self.version,
            method=method,
            oauth_timestamp=kwargs.get("oauth_timestamp", int(time()))
        )

        return oauth.get_oauth_url()

    def __request(self, method, endpoint, data, params=None, **kwargs):
        """ Do requests """
        if params is None:
            params = {}
        url = self.__get_url(endpoint)
        auth = None
        headers = {
            "user-agent": f"{self.user_agent}",
            "accept": "application/json"
        }

        if self.is_ssl is True and self.query_string_auth is False:
            auth = HTTPBasicAuth(self.consumer_key, self.consumer_secret)
        elif self.is_ssl is True and self.query_string_auth is True:
            params.update({
                "consumer_key": self.consumer_key,
                "consumer_secret": self.consumer_secret
            })
        else:
            encoded_params = urlencode(params)
            url = f"{url}?{encoded_params}"
            url = self.__get_oauth_url(url, method, **kwargs)

        if data is not None:
            data = jsonencode(data, ensure_ascii=False).encode('utf-8')
            headers["content-type"] = "application/json;charset=utf-8"

        return request(
            method=method,
            url=url,
            verify=self.verify_ssl,
            auth=auth,
            params=params,
            data=data,
            timeout=self.timeout,
            headers=headers,
            **kwargs
        )

    def get(self, endpoint, **kwargs):
        """ Get requests """
        return self.__request("GET", endpoint, None, **kwargs)

    def post(self, endpoint, data, **kwargs):
        """ POST requests """
        return self.__request("POST", endpoint, data, **kwargs)

    def put(self, endpoint, data, **kwargs):
        """ PUT requests """
        return self.__request("PUT", endpoint, data, **kwargs)

    def delete(self, endpoint, **kwargs):
        """ DELETE requests """
        return self.__request("DELETE", endpoint, None, **kwargs)

    def options(self, endpoint, **kwargs):
        """ OPTIONS requests """
        return self.__request("OPTIONS", endpoint, None, **kwargs)
