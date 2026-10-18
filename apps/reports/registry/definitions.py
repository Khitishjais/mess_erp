"""The 23 reports: one registration line each."""
from .core import reg
from .items import hourly_items, item_group, item_rows, tag_wise
from .orders import order_rows
from .sales import outlet_performance, sales_report

reg('all_sales', 'All Restaurant Sales Report', 'Total sales of all your restaurant', sales_report({'restaurants': 'outlet__name'}))


reg('outlet_item_row', 'Outlet-Item Wise Report (Row)', 'Consolidated summary of item sales with outlets in row format',
    item_group({'restaurant': 'order__outlet__name', 'item': 'name'}))


reg('invoice', 'Invoice Report: All Restaurants', 'Total invoice of all your restaurants', order_rows())


reg('pax_biller', 'Pax Sales Report: Biller Wise', 'Sales per pax made by each biller', sales_report({'biller': 'biller__name'}))


reg('sub_order', 'Order Report: Sub-Order Wise', 'Bifurcation of orders based on sub-order type', sales_report({'sub_order_type': 'sub_order_type'}))


reg('day_wise', 'All Restaurant Report: Day Wise', 'Total sales of all your restaurant per day',
    sales_report({'restaurant': 'outlet__name', 'date': 'created_at__date'}))


reg('corporate', 'Order Summary: Corporate Customers', 'Order summary of corporate customers',
    sales_report({'customer': 'customer_name'}, filt=lambda q: q.exclude(customer_name='')))


reg('cancel_orders', 'Cancel Order Report: All Restaurants', 'Quantity and cost of cancelled orders', order_rows(force_status='cancelled'))


reg('discount', 'Discount Report', 'Complete list of discounts on your online and offline orders', order_rows(filt=lambda q: q.filter(discount__gt=0)))


reg('hourly_item', 'All Restaurants Sales: Hourly Item Wise', 'Total hourly sales at your restaurant', hourly_items)


reg('category', 'Category Wise Report: All Restaurants', 'Total sales from each category', item_group({'category': 'category_name'}))


reg('orders_master', 'Orders Master Report: All Restaurants', 'All orders with customer information & charges', order_rows())


reg('order_item', 'Order Report: Item Wise All Restaurants', 'Item wise orders with customer information', item_rows())


reg('cancel_item', 'Cancel Order Report: Item Wise All Restaurants', 'Item wise cancelled orders', item_rows(cancelled_only=True))


reg('locality', 'Locality Wise Report: All Restaurants', 'Total orders grouped by locality', sales_report({'locality': 'locality'}))


reg('item_invoice', 'Item Report: Invoice Details', 'Items sold under each invoice', item_rows())


reg('item_wise', 'Item Wise Report: All Restaurants', 'Total sales from each item', item_group({'item': 'name'}))


reg('item_brand', 'Item Wise Report (Brand Wise): All Restaurants', 'Item sales by brand',
    item_group({'brand': 'order__outlet__brand', 'item': 'name'}))


reg('online_orders', 'Online Order Report: All Restaurants', 'Track online order details and activities',
    order_rows(filt=lambda q: q.filter(is_online=True)))


reg('discount_reason', 'Discounted Orders: All Restaurants (With Reason)', 'Orders with discount and the reason',
    order_rows(filt=lambda q: q.filter(discount__gt=0)))


reg('tag_wise', 'Tag Wise Report: All Restaurants', 'Total sales from each tag', tag_wise)


reg('advance', 'Advance Order Summary Report', 'Advance orders with customer information',
    order_rows(filt=lambda q: q.filter(sub_order_type__iexact='advance')))


reg('outlet_performance', 'Outlet Performance', 'Outlets ranked above and below the group average', outlet_performance)
