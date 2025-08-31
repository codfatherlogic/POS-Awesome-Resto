# -*- coding: utf-8 -*-
# Copyright (c) 2025, Youssef Restom and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime
from posawesome.posawesome.api.sales_orders import submit_sales_order, update_sales_order

@frappe.whitelist()
def get_restaurant_order_types():
	"""Get all enabled restaurant order types"""
	return frappe.get_all(
		"Restaurant Order Type",
		filters={"enabled": 1},
		fields=["name", "order_type_name", "requires_table", "default_preparation_time"],
		order_by="order_type_name"
	)

@frappe.whitelist()
def get_available_tables():
	"""Get all available tables for dine-in orders"""
	return frappe.get_all(
		"Restaurant Table",
		filters={"enabled": 1, "status": "Available"},
		fields=["name", "table_number", "table_name", "capacity", "location"],
		order_by="table_number"
	)

@frappe.whitelist()
def create_restaurant_order(order_data):
	"""Create a restaurant order (Sales Order) with order type and table info"""
	if isinstance(order_data, str):
		order_data = json.loads(order_data)
	
	# Validate order type
	order_type = order_data.get("restaurant_order_type")
	if not order_type:
		frappe.throw(_("Restaurant Order Type is required"))
	
	order_type_doc = frappe.get_doc("Restaurant Order Type", order_type)
	if not order_type_doc.enabled:
		frappe.throw(_("Selected order type is not enabled"))
	
	# Validate table if required
	table_number = order_data.get("table_number")
	if order_type_doc.requires_table and not table_number:
		frappe.throw(_("Table number is required for {0} orders").format(order_type_doc.order_type_name))
	
	# Check table availability if table is specified
	if table_number:
		table_doc = frappe.get_doc("Restaurant Table", {"table_number": table_number})
		if table_doc.status != "Available":
			frappe.throw(_("Table {0} is not available").format(table_number))
	
	# Set order type specific fields
	order_data["doctype"] = "Sales Order"
	order_data["restaurant_order_type"] = order_type
	order_data["order_date"] = nowdate()
	order_data["delivery_date"] = order_data.get("delivery_date") or nowdate()
	
	if table_number:
		order_data["table_number"] = table_number
	
	# Set preparation time
	if order_type_doc.default_preparation_time:
		order_data["expected_preparation_time"] = order_type_doc.default_preparation_time
	
	# Create the sales order
	sales_order = update_sales_order(json.dumps(order_data))
	
	# Occupy table if it's a dine-in order
	if table_number and sales_order:
		try:
			table_doc = frappe.get_doc("Restaurant Table", {"table_number": table_number})
			table_doc.occupy_table(sales_order.name)
		except Exception as e:
			frappe.log_error(f"Failed to occupy table {table_number}: {str(e)}")
			# Don't fail the order creation if table occupation fails
	
	return sales_order

@frappe.whitelist()
def submit_restaurant_order(order_data):
	"""Submit a restaurant order and handle table occupation"""
	if isinstance(order_data, str):
		order_data = json.loads(order_data)
	
	# If only order name is provided, get the full order
	if "name" in order_data and len(order_data) == 1:
		order_name = order_data["name"]
		
		# Validate that this is actually a Sales Order name, not a Sales Invoice
		if not order_name or not order_name.startswith("SAL-ORD-"):
			frappe.throw(_("Invalid Sales Order name format: {0}. Expected format: SAL-ORD-XXXX").format(order_name))
		
		try:
			order = frappe.get_doc("Sales Order", order_name)
			if order.docstatus == 0:  # Only submit if it's draft
				order.submit()
				return order
			else:
				return order  # Already submitted
		except frappe.DoesNotExistError:
			frappe.throw(_("Sales Order {0} not found").format(order_name))
	
	# Submit the sales order using the full data
	result = submit_sales_order(json.dumps(order_data))
	
	# Handle table occupation for dine-in orders
	table_number = order_data.get("table_number")
	if table_number and result.get("name"):
		try:
			table_doc = frappe.get_doc("Restaurant Table", {"table_number": table_number})
			table_doc.occupy_table(result["name"])
		except Exception as e:
			frappe.log_error(f"Failed to occupy table {table_number}: {str(e)}")
	
	return result

@frappe.whitelist()
def convert_order_to_invoice(sales_order_name, pos_profile_name=None):
	"""Convert a Sales Order to Sales Invoice for payment"""
	try:
		# Get the Sales Order
		sales_order = frappe.get_doc("Sales Order", sales_order_name)
		
		# Create invoice manually to ensure proper linking instead of using make_sales_invoice
		invoice_doc = frappe.new_doc("Sales Invoice")
		
		# Copy basic fields from Sales Order
		invoice_doc.customer = sales_order.customer
		invoice_doc.customer_name = sales_order.customer_name
		invoice_doc.posting_date = frappe.utils.nowdate()
		invoice_doc.due_date = frappe.utils.nowdate()
		invoice_doc.company = sales_order.company
		invoice_doc.currency = sales_order.currency
		invoice_doc.selling_price_list = sales_order.selling_price_list
		invoice_doc.price_list_currency = sales_order.price_list_currency
		invoice_doc.plc_conversion_rate = sales_order.plc_conversion_rate
		invoice_doc.conversion_rate = sales_order.conversion_rate
		
		# Copy items with proper Sales Order references
		for so_item in sales_order.items:
			invoice_item = invoice_doc.append("items", {})
			invoice_item.item_code = so_item.item_code
			invoice_item.item_name = so_item.item_name
			invoice_item.description = so_item.description
			invoice_item.qty = so_item.qty
			invoice_item.rate = so_item.rate
			invoice_item.amount = so_item.amount
			invoice_item.uom = so_item.uom
			invoice_item.conversion_factor = so_item.conversion_factor
			invoice_item.stock_uom = so_item.stock_uom
			invoice_item.warehouse = so_item.warehouse
			
			# CRITICAL: Set the Sales Order references properly
			invoice_item.sales_order = sales_order_name
			invoice_item.so_detail = so_item.name
			
			# Copy other important fields
			if hasattr(so_item, 'base_rate'):
				invoice_item.base_rate = so_item.base_rate
			if hasattr(so_item, 'base_amount'):
				invoice_item.base_amount = so_item.base_amount
		
			# Copy other important fields
			if hasattr(so_item, 'base_rate'):
				invoice_item.base_rate = so_item.base_rate
			if hasattr(so_item, 'base_amount'):
				invoice_item.base_amount = so_item.base_amount
		
		# Copy taxes if they exist
		if hasattr(sales_order, 'taxes') and sales_order.taxes:
			for tax in sales_order.taxes:
				invoice_tax = invoice_doc.append("taxes", {})
				invoice_tax.charge_type = tax.charge_type
				invoice_tax.account_head = tax.account_head
				invoice_tax.description = tax.description
				invoice_tax.rate = tax.rate
				invoice_tax.tax_amount = tax.tax_amount
				invoice_tax.total = tax.total
				if hasattr(tax, 'base_tax_amount'):
					invoice_tax.base_tax_amount = tax.base_tax_amount
				if hasattr(tax, 'base_total'):
					invoice_tax.base_total = tax.base_total
		
		# Set POS specific fields
		invoice_doc.is_pos = 1
		# FORCE DISABLE stock update for restaurant orders to avoid stock validation issues
		invoice_doc.update_stock = 0
		
		# Add Sales Order reference in remarks
		invoice_doc.remarks = f"Created from Sales Order: {sales_order_name}"
		
		# Calculate totals
		invoice_doc.total = sum(item.amount for item in invoice_doc.items)
		invoice_doc.base_total = sum(item.base_amount or item.amount for item in invoice_doc.items)
		invoice_doc.net_total = invoice_doc.total
		invoice_doc.base_net_total = invoice_doc.base_total
		invoice_doc.grand_total = invoice_doc.total
		invoice_doc.base_grand_total = invoice_doc.base_total
		invoice_doc.rounded_total = invoice_doc.grand_total
		invoice_doc.base_rounded_total = invoice_doc.base_grand_total
		
		# Set missing values
		invoice_doc.flags.ignore_permissions = True
		invoice_doc.set_missing_values(for_validate=True)
		
		# Initialize payment methods from POS Profile
		# First try to get POS Profile from parameter, then from company settings, then from default
		if not pos_profile_name:
			# Try to find a POS Profile for the company
			pos_profiles = frappe.get_all("POS Profile", 
				filters={"company": sales_order.company, "disabled": 0}, 
				limit=1)
			if pos_profiles:
				pos_profile_name = pos_profiles[0].name
			else:
				# Fall back to any enabled POS Profile
				pos_profiles = frappe.get_all("POS Profile", 
					filters={"disabled": 0}, 
					limit=1)
				if pos_profiles:
					pos_profile_name = pos_profiles[0].name
		
		if pos_profile_name:
			pos_profile = frappe.get_doc("POS Profile", pos_profile_name)
			
			# Clear existing payments and add from POS Profile
			invoice_doc.payments = []
			
			for payment_method in pos_profile.payments:
				payment_entry = {
					"mode_of_payment": payment_method.mode_of_payment,
					"amount": 0.0,
					"base_amount": 0.0,
					"default": getattr(payment_method, 'default', 0)
				}
				
				# Add optional fields if they exist
				if hasattr(payment_method, 'account'):
					payment_entry["account"] = payment_method.account
				if hasattr(payment_method, 'type'):
					payment_entry["type"] = payment_method.type
					
				invoice_doc.append("payments", payment_entry)
		
		# Save the invoice
		invoice_doc.save()
		
		# DEBUG: Log the invoice items to verify proper linking
		frappe.log_error(f"DEBUG: Invoice {invoice_doc.name} created from SO {sales_order_name}", "Restaurant Order Debug")
		for item in invoice_doc.items:
			frappe.log_error(f"DEBUG: Invoice Item - item_code: {item.item_code}, sales_order: {getattr(item, 'sales_order', 'MISSING')}, so_detail: {getattr(item, 'so_detail', 'MISSING')}, amount: {item.amount}", "Restaurant Order Debug")
		
		# SIMPLIFIED BUT EFFECTIVE FIX: Focus on core ERPNext linking mechanism
		# NOTE: We do NOT update Sales Order status here during conversion
		# Status changes should only happen after successful Sales Invoice submission
		try:
			# 1. Prepare Sales Order Item references for linking (but don't mark as billed yet)
			for item in invoice_doc.items:
				if item.so_detail:
					# Only update delivered_qty to maintain order tracking
					# Do NOT update billed_amt here - that should happen on invoice submission
					frappe.db.set_value("Sales Order Item", item.so_detail, {
						"delivered_qty": item.qty
					})
			
			# 2. DO NOT recalculate per_billed or change status here
			# The Sales Order should remain in "Submitted" status until payment is completed
			# Status changes will be handled by the invoice submission process
			
			# Commit delivery quantity changes only
			frappe.db.commit()
			
		except Exception as e:
			# Simplified error handling to avoid logging issues
			print(f"Warning: Could not update Sales Order item tracking for {sales_order_name}: {str(e)}")
			# Don't fail the invoice creation if linking fails
		
		# Free table if it was a dine-in order (but don't fail if table operations fail)
		if sales_order.get("table_number"):
			try:
				table_doc = frappe.get_doc("Restaurant Table", {"table_number": sales_order.table_number})
				if table_doc.current_order == sales_order_name:
					table_doc.free_table()
			except Exception as e:
				frappe.log_error(f"Failed to free table {sales_order.table_number}: {str(e)}")
				# Don't fail the invoice creation if table operation fails
		
		return invoice_doc
		
	except frappe.DoesNotExistError:
		frappe.throw(_("Sales Order {0} not found").format(sales_order_name))
	except Exception as e:
		# Use shorter error message to avoid "Value too big" error in logging
		frappe.log_error(f"Order {sales_order_name} conversion failed")
		frappe.throw(_("Error converting order to invoice"))


@frappe.whitelist()
def get_restaurant_orders(pos_opening_shift=None, order_type=None, status=None, date_filter=None):
	"""Get restaurant orders with filtering options"""
	filters = {
		"restaurant_order_type": ["is", "set"]  # Only get orders that have restaurant_order_type
	}
	
	# Debug logging
	frappe.log_error(f"Restaurant Orders API called with: pos_opening_shift={pos_opening_shift}, order_type={order_type}, status={status}, date_filter={date_filter}", "Restaurant Orders Debug")
	frappe.log_error(f"Initial filters: {filters}", "Restaurant Orders Debug")
	
	# Only filter by pos_opening_shift if the field exists in Sales Order
	if pos_opening_shift:
		# Check if the field exists before adding to filters
		try:
			if frappe.db.has_column("Sales Order", "posa_pos_opening_shift"):
				filters["posa_pos_opening_shift"] = pos_opening_shift
		except:
			pass  # Field doesn't exist, skip this filter
	
	if order_type:
		filters["restaurant_order_type"] = order_type
	
	if status:
		if status == "Draft":
			filters["docstatus"] = 0
		elif status == "Submitted":
			filters["docstatus"] = 1
			filters["per_billed"] = ["<", 100]
		elif status == "Billed":
			filters["per_billed"] = 100
		elif status == "Cancelled":
			filters["docstatus"] = 2
	else:
		# By default, exclude cancelled orders unless specifically requested
		filters["docstatus"] = ["!=", 2]
	
	# Apply date filter - if provided, use it; otherwise default to today
	if date_filter:
		# Handle different date formats that might come from frontend
		try:
			from frappe.utils import getdate
			parsed_date = getdate(date_filter)
			filters["transaction_date"] = parsed_date
			frappe.log_error(f"Date filter parsed: {date_filter} -> {parsed_date}", "Restaurant Orders Debug")
		except:
			frappe.log_error(f"Failed to parse date filter: {date_filter}", "Restaurant Orders Debug")
			filters["transaction_date"] = date_filter
	else:
		# Default to today's orders if no specific date is provided
		from frappe.utils import today
		filters["transaction_date"] = [">=", today()]
	
	frappe.log_error(f"Final filters before query: {filters}", "Restaurant Orders Debug")
	
	frappe.log_error(f"Final filters: {filters}", "Restaurant Orders Debug")
	
	orders = frappe.get_all(
		"Sales Order",
		filters=filters,
		fields=[
			"name", "customer", "customer_name", "transaction_date", "delivery_date",
			"grand_total", "net_total", "total_taxes_and_charges", "discount_amount",
			"currency", "docstatus", "per_billed", "restaurant_order_type",
			"table_number", "expected_preparation_time", "creation"
		],
		order_by="transaction_date desc, creation desc"
	)
	
	# Disable debugging logs temporarily to avoid length issues
	# Debug: Log the actual order names being returned (with truncated title)
	order_names = [order.name for order in orders]
	# Commenting out logging to prevent "Value too big" errors
	# try:
	#	frappe.log_error(f"Order names from query: {order_names}", "Restaurant Orders Query")
	# except Exception as log_err:
	#	frappe.log_error(f"Found {len(order_names)} orders in query", "Restaurant Orders Count")
	
	# Filter out any non-Sales Order entries (safety check)
	valid_orders = []
	for order in orders:
		if order.name and order.name.startswith("SAL-ORD-"):
			valid_orders.append(order)
		# Commenting out logging to prevent issues
		# else:
		#	try:
		#		frappe.log_error(f"WARNING: Invalid order name in results: {order.name}", "Invalid Order Name")
		#	except Exception:
		#		frappe.log_error(f"WARNING: Invalid order found", "Invalid Order")
	
	# Commenting out logging to prevent "Value too big" errors
	# try:
	#	frappe.log_error(f"Found {len(valid_orders)} valid orders after filtering", "Orders Filtered")
	# except Exception:
	#	pass
	
	# Add order type details and items
	for order in valid_orders:
		if order.restaurant_order_type:
			try:
				order_type_doc = frappe.get_cached_doc("Restaurant Order Type", order.restaurant_order_type)
				order["order_type_name"] = order_type_doc.order_type_name
				order["requires_table"] = order_type_doc.requires_table
			except:
				order["order_type_name"] = order.restaurant_order_type
				order["requires_table"] = False
		
		# Get order items for the expandable view
		order_items = frappe.get_all(
			"Sales Order Item",
			filters={"parent": order.name},
			fields=["item_code", "item_name", "qty", "uom", "rate", "amount"],
			order_by="idx"
		)
		order["items"] = order_items
	
	return valid_orders

@frappe.whitelist()
def cancel_restaurant_order(sales_order_name):
	"""Cancel restaurant order and free table if applicable"""
	sales_order = frappe.get_doc("Sales Order", sales_order_name)
	
	# Free table if it was occupied
	if sales_order.get("table_number"):
		try:
			table_doc = frappe.get_doc("Restaurant Table", {"table_number": sales_order.table_number})
			if table_doc.current_order == sales_order_name:
				table_doc.free_table()
		except Exception as e:
			frappe.log_error(f"Failed to free table {sales_order.table_number}: {str(e)}")
	
	# Cancel the sales order
	sales_order.cancel()
	
	return {"success": True, "message": _("Order cancelled successfully")}

@frappe.whitelist()
def delete_restaurant_order(sales_order_name):
	"""Delete draft restaurant order and free table if applicable"""
	sales_order = frappe.get_doc("Sales Order", sales_order_name)
	
	# Validate that order is in draft status
	if sales_order.docstatus != 0:
		frappe.throw(_("Only draft orders can be deleted"))
	
	# Free table if it was occupied
	if sales_order.get("table_number"):
		try:
			table_doc = frappe.get_doc("Restaurant Table", {"table_number": sales_order.table_number})
			if table_doc.current_order == sales_order_name:
				table_doc.free_table()
		except Exception as e:
			frappe.log_error(f"Failed to free table {sales_order.table_number}: {str(e)}")
	
	# Delete the sales order
	frappe.delete_doc("Sales Order", sales_order_name)
	
	return {"success": True, "message": _("Order deleted successfully")}

@frappe.whitelist()
def get_table_status():
	"""Get current status of all tables"""
	tables = frappe.get_all(
		"Restaurant Table",
		filters={"enabled": 1},
		fields=["name", "table_number", "table_name", "capacity", "location", "status", "current_order"],
		order_by="table_number"
	)
	
	# Add order details for occupied tables
	for table in tables:
		if table.current_order:
			try:
				order = frappe.get_doc("Sales Order", table.current_order)
				table["order_customer"] = order.customer_name
				table["order_total"] = order.grand_total
				table["order_time"] = order.creation
			except:
				# Order might have been deleted, free the table
				table_doc = frappe.get_doc("Restaurant Table", table.name)
				table_doc.free_table()
				table["status"] = "Available"
				table["current_order"] = None
	
	return tables

@frappe.whitelist()
def setup_restaurant_data():
	"""Setup default restaurant order types and sample tables"""
	from posawesome.posawesome.doctype.restaurant_order_type.restaurant_order_type import create_default_order_types
	from posawesome.posawesome.doctype.restaurant_table.restaurant_table import create_sample_tables
	
	order_types = create_default_order_types()
	tables = create_sample_tables()
	
	return {
		"order_types_created": order_types,
		"tables_created": tables,
		"message": _("Restaurant setup completed successfully")
	}

@frappe.whitelist()
def create_invoice_from_multiple_orders(sales_orders, pos_profile_name=None):
	"""Create a single invoice from multiple sales orders"""
	if isinstance(sales_orders, str):
		sales_orders = json.loads(sales_orders)
	
	if not sales_orders or len(sales_orders) == 0:
		frappe.throw(_("No sales orders provided"))
	
	try:
		# Validate all orders exist and submit draft orders
		orders = []
		for order_name in sales_orders:
			order = frappe.get_doc("Sales Order", order_name)
			
			# Submit draft orders automatically
			if order.docstatus == 0:
				order.submit()
				frappe.db.commit()
				
			if order.docstatus != 1:
				frappe.throw(_("Order {0} could not be submitted").format(order_name))
			if order.per_billed >= 100:
				frappe.throw(_("Order {0} is already fully billed").format(order_name))
			orders.append(order)
		
		# Validate all orders are from the same customer
		first_customer = orders[0].customer
		if not all(order.customer == first_customer for order in orders):
			frappe.throw(_("All orders must be from the same customer"))
		
		# Use the first order as the base for the invoice
		base_order = orders[0]
		
		# Create invoice from the first order using ERPNext's built-in method
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
		invoice_doc = make_sales_invoice(base_order.name)
		
		# Set POS specific fields
		invoice_doc.is_pos = 1
		# FORCE DISABLE stock update for restaurant orders to avoid stock validation issues
		invoice_doc.update_stock = 0
		
		if len(orders) > 1:
			# Add items from additional orders - KEEP SEPARATE LINE ITEMS for proper linking
			for order in orders[1:]:
				for item in order.items:
					# ALWAYS add as separate line item - DO NOT combine quantities
					# This ensures each Sales Order Item has its own Sales Invoice Item for proper linking
					new_item = invoice_doc.append("items", {
						"item_code": item.item_code,
						"item_name": item.item_name,
						"description": item.description,
						"qty": item.qty,
						"uom": item.uom,
						"rate": item.rate,
						"amount": item.qty * item.rate,
						"warehouse": item.warehouse,
						"sales_order": order.name,
						"so_detail": item.name,
					})
					
					# CRITICAL: Ensure the so_detail field is properly set for linking
					new_item.so_detail = item.name
					new_item.sales_order = order.name
			
			# Recalculate totals
			invoice_doc.calculate_taxes_and_totals()
		
		# Initialize payment methods from POS Profile
		# First try to get POS Profile from parameter, then from company settings, then from default
		if not pos_profile_name:
			# Try to find a POS Profile for the company
			pos_profiles = frappe.get_all("POS Profile", 
				filters={"company": base_order.company, "disabled": 0}, 
				limit=1)
			if pos_profiles:
				pos_profile_name = pos_profiles[0].name
			else:
				# Fall back to any enabled POS Profile
				pos_profiles = frappe.get_all("POS Profile", 
					filters={"disabled": 0}, 
					limit=1)
				if pos_profiles:
					pos_profile_name = pos_profiles[0].name
		
		if pos_profile_name:
			pos_profile = frappe.get_doc("POS Profile", pos_profile_name)
			
			# FORCE DISABLE stock update for restaurant orders to avoid stock validation issues
			invoice_doc.update_stock = 0
			
			# Clear existing payments and add from POS Profile
			invoice_doc.payments = []
			
			for payment_method in pos_profile.payments:
				payment_entry = {
					"mode_of_payment": payment_method.mode_of_payment,
					"amount": 0.0,
					"base_amount": 0.0,
					"default": getattr(payment_method, 'default', 0)
				}
				
				# Add optional fields if they exist
				if hasattr(payment_method, 'account'):
					payment_entry["account"] = payment_method.account
				if hasattr(payment_method, 'type'):
					payment_entry["type"] = payment_method.type
					
				invoice_doc.append("payments", payment_entry)
		
		# Save the invoice
		invoice_doc.save()
		
		# APPLY SAME LINKING MECHANISM AS SINGLE ORDER
		# NOTE: We do NOT update Sales Order status here during conversion
		# Status changes should only happen after successful Sales Invoice submission
		try:
			# Prepare Sales Order Item references for linking (but don't mark as billed yet)
			for item in invoice_doc.items:
				if item.so_detail:
					# Only update delivered_qty to maintain order tracking
					# Do NOT update billed_amt here - that should happen on invoice submission
					frappe.db.set_value("Sales Order Item", item.so_detail, {
						"delivered_qty": item.qty
					})
			
			# DO NOT recalculate per_billed or change status here for ANY orders
			# The Sales Orders should remain in "Submitted" status until payment is completed
			# Status changes will be handled by the invoice submission process
			
			# Commit delivery quantity changes only
			frappe.db.commit()
			
		except Exception as e:
			# Simplified error handling to avoid logging issues
			print(f"Warning: Could not update Sales Order item tracking for multiple orders: {str(e)}")
			# Don't fail the invoice creation if linking fails
		
		# Free tables for all dine-in orders
		for order in orders:
			if order.get("table_number"):
				try:
					table_doc = frappe.get_doc("Restaurant Table", {"table_number": order.table_number})
					if table_doc.current_order == order.name:
						table_doc.free_table()
				except Exception as e:
					frappe.log_error(f"Failed to free table {order.table_number}: {str(e)}")
					# Don't fail the invoice creation if table operation fails
		
		return invoice_doc
		
	except Exception as e:
		frappe.log_error(f"Error creating invoice from multiple orders: {str(e)}")
		frappe.throw(_("Error creating invoice from orders: {0}").format(str(e)))

@frappe.whitelist()
def update_submitted_order_items(order_name, items_data):
	"""Update items in a submitted sales order"""
	if isinstance(items_data, str):
		items_data = json.loads(items_data)
	
	try:
		# Extensive debug logging
		frappe.log_error(f"=== DEBUG: update_submitted_order_items called ===", "Update Order Debug")
		frappe.log_error(f"order_name parameter: {order_name}", "Update Order Debug")
		frappe.log_error(f"items_data count: {len(items_data) if items_data else 0}", "Update Order Debug")
		
		# Check if the order exists as Sales Order
		if not frappe.db.exists("Sales Order", order_name):
			frappe.log_error(f"Sales Order {order_name} does not exist in database", "Update Order Error")
			# Check if it exists as Sales Invoice instead
			if frappe.db.exists("Sales Invoice", order_name):
				frappe.log_error(f"Document {order_name} exists as Sales Invoice, not Sales Order!", "Update Order Error")
				frappe.throw(_("Document {0} is a Sales Invoice, not a Sales Order. Cannot update orders that have been converted to invoices.").format(order_name))
			else:
				frappe.log_error(f"Document {order_name} does not exist in any form", "Update Order Error")
				frappe.throw(_("Sales Order {0} not found").format(order_name))
		
		# Log the attempt to update
		frappe.log_error(f"Attempting to fetch Sales Order: {order_name}", "Update Order Debug")
		
		order = frappe.get_doc("Sales Order", order_name)
		
		frappe.log_error(f"Successfully fetched Sales Order: {order.name}, docstatus: {order.docstatus}, per_billed: {order.per_billed}", "Update Order Debug")
		
		if order.docstatus != 1:
			frappe.throw(_("Can only update items in submitted orders"))
		
		if order.per_billed >= 100:
			frappe.throw(_("Cannot update fully billed orders"))
		
		# Cancel the order to allow modifications
		order.cancel()
		
		# Update items
		order.items = []
		for item_data in items_data:
			order.append("items", item_data)
		
		# Recalculate and resubmit
		order.calculate_taxes_and_totals()
		order.save()
		order.submit()
		
		frappe.log_error(f"Successfully updated Sales Order: {order.name}", "Update Order Success")
		return order
		
	except frappe.DoesNotExistError as e:
		frappe.log_error(f"Sales Order {order_name} not found - DoesNotExistError: {str(e)}", "Update Order Error")
		frappe.throw(_("Sales Order {0} not found").format(order_name))
	except Exception as e:
		frappe.log_error(f"Error updating submitted order {order_name}: {str(e)} - Type: {type(e).__name__}", "Update Order Error")
		frappe.throw(_("Error updating order: {0}").format(str(e)))

@frappe.whitelist()
def load_multiple_draft_orders_for_editing(sales_order_names, pos_profile_name=None):
	"""
	Load multiple draft Sales Orders and combine them into a NEW consolidated order for payment.
	Original orders remain as DRAFT - this creates a new order for processing payment only.
	"""
	try:
		frappe.log_error(f"load_multiple_draft_orders_for_editing called with: {sales_order_names}", "Multi Order Load Debug")
		
		if isinstance(sales_order_names, str):
			sales_order_names = json.loads(sales_order_names)
		
		if not sales_order_names or len(sales_order_names) < 1:
			frappe.throw(_("At least one Sales Order is required"))
		
		frappe.log_error(f"Processing {len(sales_order_names)} orders: {sales_order_names}", "Multi Order Load Debug")
		
		# Get all the draft orders
		orders = []
		first_customer = None
		total_amount = 0
		
		for order_name in sales_order_names:
			try:
				frappe.log_error(f"Fetching order: {order_name}", "Multi Order Load Debug")
				order_doc = frappe.get_doc("Sales Order", order_name)
				
				# Ensure all orders are draft
				if order_doc.docstatus != 0:
					frappe.throw(_("Order {0} is not in draft status. Only draft orders can be loaded for editing.").format(order_name))
				
				# Ensure all orders are from same customer
				if first_customer is None:
					first_customer = order_doc.customer
				elif order_doc.customer != first_customer:
					frappe.throw(_("All selected orders must be from the same customer"))
				
				orders.append(order_doc)
				total_amount += order_doc.grand_total
				frappe.log_error(f"Successfully loaded order: {order_name}, customer: {order_doc.customer}", "Multi Order Load Debug")
				
			except frappe.DoesNotExistError:
				frappe.log_error(f"Order {order_name} does not exist", "Multi Order Load Error")
				frappe.throw(_("Sales Order {0} not found").format(order_name))
			except Exception as e:
				frappe.log_error(f"Error loading order {order_name}: {str(e)}", "Multi Order Load Error")
				frappe.throw(_("Error loading order {0}: {1}").format(order_name, str(e)))
		
		frappe.log_error(f"Successfully loaded {len(orders)} orders from customer {first_customer}", "Multi Order Load Debug")
		
		# Create a NEW consolidated order document (not modifying existing ones)
		# This ensures original orders remain as draft
		first_order = orders[0]
		
		# Generate a unique name for the consolidated order (temporary)
		import datetime
		timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
		temp_order_name = f"TEMP-MULTI-{timestamp}"
		
		frappe.log_error(f"Creating new consolidated order: {temp_order_name}", "Multi Order Load Debug")
		
		consolidated_items = []
		
		# Collect all items from all orders (keep items separate, do not combine quantities)
		frappe.log_error(f"Starting item consolidation for {len(orders)} orders", "Multi Order Load Debug")
		
		for order in orders:
			frappe.log_error(f"Processing items from order {order.name}: {len(order.items)} items", "Multi Order Load Debug")
			for item in order.items:
				# Always add each item separately, even if same item_code exists
				# This ensures items from different orders remain distinct
				new_item = frappe._dict({
					'item_code': item.item_code,
					'item_name': item.item_name,
					'item_group': getattr(item, 'item_group', None),
					'description': item.description,
					'qty': item.qty,
					'uom': item.uom,
					'rate': item.rate,
					'amount': item.amount,
					'warehouse': item.warehouse,
					'source_order': order.name,  # Track which order this item came from
					'source_order_item': item.name,  # Track original item reference
					# Add a unique identifier to distinguish items from different orders
					'unique_key': f"{item.item_code}_{order.name}_{item.name}"
				})
				consolidated_items.append(new_item)
				frappe.log_error(f"Added item {item.item_code} (qty: {item.qty}) from order {order.name}", "Multi Order Load Debug")
		
		# Calculate totals (sum all individual items)
		net_total = sum(item.amount for item in consolidated_items)
		
		frappe.log_error(f"Consolidated order totals - Items: {len(consolidated_items)}, Total: {net_total}", "Multi Order Load Debug")
		
		# Set up payment methods from POS Profile
		payment_methods = []
		if pos_profile_name:
			try:
				frappe.log_error(f"Setting up payments from POS Profile: {pos_profile_name}", "Multi Order Load Debug")
				pos_profile = frappe.get_doc("POS Profile", pos_profile_name)
				
				for payment_method in pos_profile.payments:
					payment_entry = {
						"mode_of_payment": payment_method.mode_of_payment,
						"amount": 0.0,
						"base_amount": 0.0,
						"default": getattr(payment_method, 'default', 0)
					}
					
					# Add optional fields if they exist
					if hasattr(payment_method, 'account'):
						payment_entry["account"] = payment_method.account
					if hasattr(payment_method, 'type'):
						payment_entry["type"] = payment_method.type
						
					payment_methods.append(payment_entry)
				
				frappe.log_error(f"Added {len(payment_methods)} payment methods", "Multi Order Load Debug")
			except Exception as e:
				frappe.log_error(f"Error setting up payments from POS Profile: {str(e)}", "Multi Order Load Error")
				# Don't fail the entire process if POS Profile setup fails
				pass
		
		frappe.log_error(f"Successfully created consolidated order with {len(consolidated_items)} items from {len(sales_order_names)} orders", "Multi Order Load Success")
		
		# Create a NEW order structure (not modifying existing orders)
		# This ensures original draft orders remain untouched
		result = {
			'doctype': 'Sales Order',
			'name': temp_order_name,  # Temporary name - will be assigned proper name on save
			'customer': first_order.customer,
			'customer_name': getattr(first_order, 'customer_name', ''),
			'transaction_date': nowdate(),  # Use today's date for new order
			'delivery_date': getattr(first_order, 'delivery_date', nowdate()),
			'company': first_order.company,
			'currency': first_order.currency,
			'price_list_currency': first_order.currency,
			'net_total': net_total,
			'grand_total': net_total,
			'rounded_total': net_total,
			'docstatus': 0,  # Keep as draft initially
			'items': [],
			'payments': payment_methods,
			# Multi-order tracking metadata
			'is_multi_order_consolidation': True,  # Flag to identify this as a consolidated order
			'source_orders': sales_order_names,    # Original draft orders (remain as draft)
			'multi_order_count': len(sales_order_names),
			'multi_order_names': sales_order_names,
			# Important: Mark this as a payment-only order
			'is_payment_consolidation': True,  # This order is for payment processing only
			'original_orders_remain_draft': True  # Confirm original orders stay as draft
		}
		
		# Add restaurant-specific fields if they exist (use first order as reference)
		if hasattr(first_order, 'restaurant_order_type'):
			result['restaurant_order_type'] = first_order.restaurant_order_type
		if hasattr(first_order, 'table_number'):
			result['table_number'] = f"Multiple-{first_order.table_number}"  # Indicate multiple table consolidation
		
		# Convert items to dictionaries
		for item in consolidated_items:
			item_dict = {
				'item_code': item.item_code,
				'item_name': item.item_name,
				'item_group': getattr(item, 'item_group', None),
				'description': item.description,
				'qty': item.qty,
				'uom': item.uom,
				'rate': item.rate,
				'amount': item.amount,
				'warehouse': item.warehouse,
				'source_order': getattr(item, 'source_order', ''),
				'source_order_item': getattr(item, 'source_order_item', ''),
				'unique_key': getattr(item, 'unique_key', '')
			}
			result['items'].append(item_dict)
		
		frappe.log_error(f"Returning NEW consolidated order data with {len(result['items'])} items. Original orders remain DRAFT.", "Multi Order Load Debug")
		return result
		
	except Exception as e:
		error_msg = str(e)
		frappe.log_error(f"CRITICAL ERROR in load_multiple_draft_orders_for_editing: {error_msg}\nTraceback: {frappe.get_traceback()}", "Multi-Order Edit Error")
		# Provide more specific error message
		if "not found" in error_msg.lower():
			frappe.throw(_("One or more Sales Orders could not be found. Please refresh and try again."))
		elif "not in draft status" in error_msg:
			frappe.throw(_("Only draft orders can be loaded for editing: {0}").format(error_msg))
		elif "same customer" in error_msg:
			frappe.throw(_("All selected orders must be from the same customer"))
		else:
			frappe.throw(_("Error loading draft orders: {0}").format(error_msg))

@frappe.whitelist()
def finalize_multi_order_payment(consolidated_order_data, payment_data, pos_profile_name=None):
	"""
	Complete payment for a multi-order consolidation.
	This creates a final Sales Invoice for payment while keeping original orders as DRAFT.
	
	Args:
		consolidated_order_data: The consolidated order data from the POS cart
		payment_data: Payment information from POS
		pos_profile_name: POS Profile being used
	"""
	if isinstance(consolidated_order_data, str):
		consolidated_order_data = json.loads(consolidated_order_data)
	if isinstance(payment_data, str):
		payment_data = json.loads(payment_data)
	
	try:
		frappe.log_error(f"finalize_multi_order_payment called", "Multi Order Payment Debug")
		
		# Validate that this is a multi-order consolidation
		if not consolidated_order_data.get('is_multi_order_consolidation'):
			frappe.throw(_("This function is only for multi-order consolidations"))
		
		source_orders = consolidated_order_data.get('source_orders', [])
		if not source_orders:
			frappe.throw(_("No source orders found in consolidated data"))
		
		# Verify all source orders are still in draft status
		for order_name in source_orders:
			order_doc = frappe.get_doc("Sales Order", order_name)
			if order_doc.docstatus != 0:
				frappe.throw(_("Source order {0} is no longer in draft status").format(order_name))
		
		# Create a NEW Sales Invoice for the payment (do NOT touch original orders)
		invoice_doc = frappe.new_doc("Sales Invoice")
		
		# Set basic invoice fields
		invoice_doc.customer = consolidated_order_data.get('customer')
		invoice_doc.customer_name = consolidated_order_data.get('customer_name', '')
		invoice_doc.posting_date = nowdate()
		invoice_doc.posting_time = now_datetime().strftime("%H:%M:%S")
		invoice_doc.company = consolidated_order_data.get('company')
		invoice_doc.currency = consolidated_order_data.get('currency')
		invoice_doc.price_list_currency = consolidated_order_data.get('currency')
		invoice_doc.is_pos = 1
		invoice_doc.pos_profile = pos_profile_name
		
		# Add restaurant-specific fields
		if consolidated_order_data.get('restaurant_order_type'):
			invoice_doc.restaurant_order_type = consolidated_order_data.get('restaurant_order_type')
		if consolidated_order_data.get('table_number'):
			invoice_doc.table_number = consolidated_order_data.get('table_number')
		
		# Add metadata to track this as a multi-order payment
		invoice_doc.is_multi_order_payment = 1
		invoice_doc.source_draft_orders = json.dumps(source_orders)  # Track original draft orders
		
		# Add all items from consolidated order
		total_amount = 0
		for item in consolidated_order_data.get('items', []):
			invoice_item = invoice_doc.append("items", {
				"item_code": item.get('item_code'),
				"item_name": item.get('item_name'),
				"item_group": item.get('item_group'),
				"description": item.get('description'),
				"qty": item.get('qty'),
				"uom": item.get('uom'),
				"rate": item.get('rate'),
				"amount": item.get('amount'),
				"warehouse": item.get('warehouse'),
				# Add source tracking without linking to specific Sales Order
				"source_order_reference": item.get('source_order', ''),
				"remarks": f"From multi-order consolidation: {item.get('source_order', '')}"
			})
			total_amount += item.get('amount', 0)
		
		# Set invoice totals
		invoice_doc.net_total = total_amount
		invoice_doc.grand_total = total_amount
		invoice_doc.rounded_total = total_amount
		
		# Add payment information
		for payment in payment_data:
			if payment.get('amount', 0) > 0:
				payment_entry = invoice_doc.append("payments", {
					"mode_of_payment": payment.get('mode_of_payment'),
					"amount": payment.get('amount'),
					"base_amount": payment.get('amount'),  # Assuming same currency
					"account": payment.get('account', ''),
					"type": payment.get('type', 'Cash')
				})
		
		# Save and submit the invoice
		invoice_doc.insert()
		invoice_doc.submit()
		
		frappe.log_error(f"Successfully created Sales Invoice {invoice_doc.name} for multi-order payment. Original orders remain DRAFT.", "Multi Order Payment Success")
		
		# Return the invoice data
		result = {
			'doctype': 'Sales Invoice',
			'name': invoice_doc.name,
			'customer': invoice_doc.customer,
			'customer_name': invoice_doc.customer_name,
			'posting_date': invoice_doc.posting_date,
			'grand_total': invoice_doc.grand_total,
			'is_multi_order_payment': True,
			'source_draft_orders': source_orders,
			'payment_status': 'Paid',
			'message': f"Payment completed for {len(source_orders)} orders. Original orders remain as drafts."
		}
		
		# Add a note in each source order about the payment
		for order_name in source_orders:
			try:
				order_doc = frappe.get_doc("Sales Order", order_name)
				# Add a comment/note without changing the order status
				frappe.get_doc({
					"doctype": "Comment",
					"comment_type": "Info",
					"reference_doctype": "Sales Order",
					"reference_name": order_name,
					"content": f"Payment completed via consolidated invoice {invoice_doc.name}. Order remains as draft for further modifications."
				}).insert()
			except Exception as e:
				frappe.log_error(f"Failed to add payment note to order {order_name}: {str(e)}", "Multi Order Payment Note Error")
				# Don't fail the entire process if note creation fails
		
		frappe.log_error(f"Multi-order payment finalized. Invoice: {invoice_doc.name}, Source orders remain DRAFT: {source_orders}", "Multi Order Payment Complete")
		
		return result
		
	except Exception as e:
		error_msg = str(e)
		frappe.log_error(f"ERROR in finalize_multi_order_payment: {error_msg}\nTraceback: {frappe.get_traceback()}", "Multi-Order Payment Error")
		frappe.throw(_("Error processing multi-order payment: {0}").format(error_msg))

@frappe.whitelist()
def submit_multiple_orders_and_create_invoice(order_names, updated_order_data, pos_profile_name=None):
	"""
	Submit multiple draft Sales Orders with any edits, then create a consolidated Sales Invoice.
	This is called when user clicks SUBMIT in payment window after editing multiple draft orders.
	"""
	if isinstance(order_names, str):
		order_names = json.loads(order_names)
	if isinstance(updated_order_data, str):
		updated_order_data = json.loads(updated_order_data)
	
	if not order_names or len(order_names) < 1:
		frappe.throw(_("At least one Sales Order is required"))
	
	try:
		submitted_orders = []
		
		# Step 1: Update and submit each draft order with any edits made in cart
		for order_name in order_names:
			order_doc = frappe.get_doc("Sales Order", order_name)
			
			# Ensure order is still draft
			if order_doc.docstatus != 0:
				frappe.throw(_("Order {0} is no longer in draft status").format(order_name))
			
			# Apply any item changes from the consolidated edit
			# (Note: For now, we'll submit orders as-is, but you can add item update logic here)
			
			# Submit the order
			order_doc.submit()
			submitted_orders.append(order_doc)
			
			frappe.log_error(f"Successfully submitted draft order: {order_name}", "Multi-Order Submit")
		
		# Step 2: Create a consolidated Sales Invoice from all submitted orders
		first_order = submitted_orders[0]
		
		# Create Sales Invoice manually (similar to convert_order_to_invoice)
		invoice_doc = frappe.new_doc("Sales Invoice")
		
		# Set basic fields from first order
		invoice_doc.customer = first_order.customer
		invoice_doc.customer_name = first_order.customer_name
		invoice_doc.posting_date = nowdate()
		invoice_doc.posting_time = now_datetime().strftime("%H:%M:%S")
		invoice_doc.company = first_order.company
		invoice_doc.currency = first_order.currency
		invoice_doc.price_list_currency = first_order.currency
		invoice_doc.is_pos = 1
		
		# Set restaurant order fields
		if hasattr(first_order, 'restaurant_order_type'):
			invoice_doc.restaurant_order_type = first_order.restaurant_order_type
		if hasattr(first_order, 'table_number'):
			invoice_doc.table_number = first_order.table_number
		
		# Add all items from all orders
		total_amount = 0
		for order in submitted_orders:
			for item in order.items:
				invoice_item = invoice_doc.append("items", {
					"item_code": item.item_code,
					"item_name": item.item_name,
					"item_group": item.item_group,
					"description": item.description,
					"qty": item.qty,
					"uom": item.uom,
					"rate": item.rate,
					"amount": item.amount,
					"warehouse": item.warehouse,
					# Link to source Sales Order
					"sales_order": order.name,
					"so_detail": item.name
				})
				total_amount += item.amount
		
		# Set totals
		invoice_doc.net_total = total_amount
		invoice_doc.grand_total = total_amount
		invoice_doc.rounded_total = total_amount
		
		# Set up payment methods from POS Profile
		if pos_profile_name:
			pos_profile = frappe.get_doc("POS Profile", pos_profile_name)
			invoice_doc.pos_profile = pos_profile_name
			
			for payment_method in pos_profile.payments:
				payment_entry = {
					"mode_of_payment": payment_method.mode_of_payment,
					"amount": 0.0,
					"base_amount": 0.0,
					"default": getattr(payment_method, 'default', 0)
				}
				
				# Add optional fields if they exist
				if hasattr(payment_method, 'account'):
					payment_entry["account"] = payment_method.account
				if hasattr(payment_method, 'type'):
					payment_entry["type"] = payment_method.type
					
				invoice_doc.append("payments", payment_entry)
		
		# Save the consolidated invoice
		invoice_doc.save()
		
		# Add metadata to track source orders
		invoice_doc.source_orders = order_names
		invoice_doc.multi_order_count = len(order_names)
		
		frappe.log_error(f"Created consolidated invoice {invoice_doc.name} from {len(order_names)} submitted orders: {', '.join(order_names)}", "Multi-Order Invoice")
		
		return invoice_doc
		
	except Exception as e:
		frappe.log_error(f"Error submitting multiple orders and creating invoice: {str(e)}", "Multi-Order Submit Error")
		frappe.throw(_("Error processing multiple orders: {0}").format(str(e)))