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
			# Get table by table_number
			table_list = frappe.get_all("Restaurant Table", 
				filters={"table_number": table_number}, 
				fields=["name"]
			)
			if table_list:
				table_doc = frappe.get_doc("Restaurant Table", table_list[0].name)
				table_doc.occupy_table(sales_order.name)
				frappe.db.commit()  # Ensure the change is committed
				frappe.logger().info(f"Successfully occupied table {table_number} with order {sales_order.name}")
			else:
				frappe.logger().error(f"Table with number {table_number} not found")
		except Exception as e:
			frappe.log_error(f"Failed to occupy table {table_number}: {str(e)}")
			frappe.logger().error(f"Failed to occupy table {table_number}: {str(e)}")
			# Don't fail the order creation if table occupation fails
	
	# Check if auto-print KOT is enabled and generate KOT data
	pos_profile_name = order_data.get("pos_profile")
	auto_print_kot = False
	if pos_profile_name:
		try:
			auto_print_kot = frappe.db.get_value("POS Profile", pos_profile_name, "posa_auto_print_kot") or False
		except:
			pass  # Field might not exist yet
	
	# Add KOT data to response if auto-print is enabled
	result = sales_order
	if auto_print_kot and sales_order:
		try:
			kot_data = generate_kot_print(order_data)
			result = {
				"sales_order": sales_order,
				"kot_data": kot_data,
				"auto_print_kot": True
			}
		except Exception as e:
			frappe.log_error(f"Failed to generate KOT data: {str(e)}")
			# Don't fail order creation if KOT generation fails
	
	return result

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
			# Get table by table_number
			table_list = frappe.get_all("Restaurant Table", 
				filters={"table_number": table_number}, 
				fields=["name"]
			)
			if table_list:
				table_doc = frappe.get_doc("Restaurant Table", table_list[0].name)
				table_doc.occupy_table(result["name"])
				frappe.db.commit()  # Ensure the change is committed
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
			# Get table by table_number
			table_list = frappe.get_all("Restaurant Table", 
				filters={"table_number": sales_order.table_number}, 
				fields=["name"]
			)
			if table_list:
				table_doc = frappe.get_doc("Restaurant Table", table_list[0].name)
				if table_doc.current_order == sales_order_name:
					table_doc.free_table()
					frappe.db.commit()  # Ensure the change is committed
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
			# Get table by table_number
			table_list = frappe.get_all("Restaurant Table", 
				filters={"table_number": sales_order.table_number}, 
				fields=["name"]
			)
			if table_list:
				table_doc = frappe.get_doc("Restaurant Table", table_list[0].name)
				if table_doc.current_order == sales_order_name:
					table_doc.free_table()
					frappe.db.commit()  # Ensure the change is committed
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
def generate_kot_print(order_data):
	"""Generate Kitchen Order Ticket (KOT) print data without creating Sales Order"""
	if isinstance(order_data, str):
		order_data = json.loads(order_data)
	
	# Validate required data
	if not order_data.get("items"):
		frappe.throw(_("No items found for KOT printing"))
	
	order_type_name = ""
	if order_data.get("restaurant_order_type"):
		try:
			order_type_doc = frappe.get_doc("Restaurant Order Type", order_data.get("restaurant_order_type"))
			order_type_name = order_type_doc.order_type_name
		except:
			order_type_name = order_data.get("restaurant_order_type")
	
	# Prepare KOT data
	kot_data = {
		"kot_number": f"KOT-{now_datetime().strftime('%Y%m%d-%H%M%S')}",
		"order_type": order_type_name or _("Standard"),
		"table_number": order_data.get("table_number") or "",
		"customer_name": order_data.get("customer_name") or order_data.get("customer") or _("Walk-in Customer"),
		"datetime": now_datetime().strftime("%Y-%m-%d %H:%M:%S"),
		"items": [],
		"special_notes": order_data.get("posa_notes") or "",
		"total_items": 0
	}
	
	# Process items for KOT
	total_qty = 0
	for item in order_data.get("items", []):
		kot_item = {
			"item_code": item.get("item_code"),
			"item_name": item.get("item_name") or item.get("item_code"),
			"qty": item.get("qty", 0),
			"uom": item.get("uom") or "Nos",
			"special_instructions": item.get("special_instructions") or ""
		}
		kot_data["items"].append(kot_item)
		total_qty += float(item.get("qty", 0))
	
	kot_data["total_items"] = int(total_qty)
	
	return kot_data

def generate_void_kot_print(sales_order, voided_items):
	"""Generate Kitchen Order Ticket (KOT) print data for voided items"""
	
	# Get order type name
	order_type_name = ""
	if sales_order.restaurant_order_type:
		try:
			order_type_doc = frappe.get_doc("Restaurant Order Type", sales_order.restaurant_order_type)
			order_type_name = order_type_doc.order_type_name
		except:
			order_type_name = sales_order.restaurant_order_type
	
	# Prepare Void KOT data
	void_kot_data = {
		"kot_number": f"VOID-KOT-{now_datetime().strftime('%Y%m%d-%H%M%S')}",
		"order_number": sales_order.name,
		"order_type": order_type_name or _("Standard"),
		"table_number": sales_order.table_number or "",
		"customer_name": sales_order.customer_name or sales_order.customer or _("Walk-in Customer"),
		"datetime": now_datetime().strftime("%Y-%m-%d %H:%M:%S"),
		"voided_items": [],
		"special_notes": _("VOID - Items cancelled from order"),
		"total_voided_items": 0,
		"is_void": True,
		"void_reason": _("Items voided by staff")
	}
	
	# Process voided items for KOT
	total_qty = 0
	for item in voided_items:
		void_kot_item = {
			"item_code": item.get("item_code", ""),
			"item_name": item.get("item_name", ""),
			"qty": item.get("qty", 0),
			"uom": "Nos",  # Default UOM
			"status": "VOIDED"
		}
		void_kot_data["voided_items"].append(void_kot_item)
		total_qty += float(item.get("qty", 0))
	
	void_kot_data["total_voided_items"] = int(total_qty)
	
	return void_kot_data

@frappe.whitelist()
def reprint_kot(order_name):
	"""Reprint KOT for an existing order"""
	try:
		# Get the sales order
		sales_order = frappe.get_doc("Sales Order", order_name)
		
		# Convert sales order to order_data format needed by generate_kot_html
		order_data = {
			"customer": sales_order.customer,
			"customer_name": sales_order.customer_name or sales_order.customer,
			"items": [],
			"table_number": sales_order.table_number,
			"restaurant_order_type": sales_order.restaurant_order_type,
			"order_date": sales_order.transaction_date or sales_order.order_date,
			"name": sales_order.name
		}
		
		# Convert sales order items to the format expected
		for item in sales_order.items:
			order_data["items"].append({
				"item_code": item.item_code,
				"item_name": item.item_name,
				"qty": item.qty,
				"uom": item.uom,
				"special_instructions": getattr(item, 'special_instructions', '') or ''
			})
		
		# Generate KOT HTML
		kot_html = generate_kot_html(order_data)
		
		return kot_html
		
	except Exception as e:
		frappe.log_error(f"Error reprinting KOT for order {order_name}: {str(e)}")
		frappe.throw(f"Error reprinting KOT: {str(e)}")

@frappe.whitelist()
def generate_kot_html(order_data):
	"""Generate KOT HTML for printing"""
	if isinstance(order_data, str):
		order_data = json.loads(order_data)
	
	kot_data = generate_kot_print(order_data)
	
	# Generate KOT HTML template
	items_html = ""
	for item in kot_data["items"]:
		items_html += f"""
		<tr>
			<td style="padding: 2px 0; border-bottom: 1px dotted #ccc;">
				{item['item_name']}
			</td>
			<td style="padding: 2px 0; text-align: center; border-bottom: 1px dotted #ccc;">
				{item['qty']} {item['uom']}
			</td>
		</tr>"""
	
	table_info = f"<p><strong>Table:</strong> {kot_data['table_number']}</p>" if kot_data["table_number"] else ""
	notes_section = f"<p style='margin-top: 5px; font-style: italic;'>{kot_data['special_notes']}</p>" if kot_data["special_notes"] else ""
	
	kot_html = f"""
	<!DOCTYPE html>
	<html>
	<head>
		<meta charset="utf-8">
		<title>KOT {kot_data['kot_number']}</title>
		<style>
			body {{ font-family: 'Courier New', monospace; width: 58mm; margin: 0; padding: 5px; font-size: 10px; line-height: 1.2; }}
			.header {{ text-align: center; border-bottom: 1px solid #000; padding-bottom: 5px; margin-bottom: 8px; }}
			.kot-title {{ font-size: 12px; font-weight: bold; margin: 2px 0; }}
			.kot-info {{ margin: 8px 0; font-size: 9px; }}
			.kot-info p {{ margin: 2px 0; }}
			.items-table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 9px; }}
			.items-table th {{ border-bottom: 1px solid #000; padding: 2px 0; text-align: left; font-weight: bold; font-size: 8px; }}
			.items-table td {{ padding: 2px 0; vertical-align: top; }}
			.footer {{ border-top: 1px solid #000; padding-top: 5px; margin-top: 8px; text-align: center; font-size: 9px; }}
			.dashed-line {{ border-top: 1px dotted #000; margin: 5px 0; }}
			@media print {{
				body {{ margin: 0; padding: 2px; width: 58mm; }}
			}}
		</style>
	</head>
	<body>
		<div class="header">
			<h2 class="kot-title">KITCHEN ORDER TICKET</h2>
			<p><strong>KOT #:</strong> {kot_data['kot_number']}</p>
		</div>
		
		<div class="kot-info">
			<p><strong>Type:</strong> {kot_data['order_type']}</p>
			{table_info}
			<p><strong>Customer:</strong> {kot_data['customer_name']}</p>
			<p><strong>Date & Time:</strong> {kot_data['datetime']}</p>
		</div>
		
		<div class="dashed-line"></div>
		
		<table class="items-table">
			<thead>
				<tr>
					<th style="width: 60%;">ITEM</th>
					<th style="width: 40%; text-align: center;">QTY</th>
				</tr>
			</thead>
			<tbody>
				{items_html}
			</tbody>
		</table>
		
		<div class="dashed-line"></div>
		
		<div class="kot-info">
			<p><strong>Total Items:</strong> {kot_data['total_items']}</p>
			{notes_section}
		</div>
		
		<div class="footer">
			<p><strong>*** KITCHEN COPY ***</strong></p>
			<p>Please prepare items as ordered</p>
		</div>
		
		<script>
			window.onload = function() {{
				window.print();
			}};
		</script>
	</body>
	</html>
	"""
	
	return kot_html

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
def add_items_to_draft_order(order_name, items_data):
	"""Add new items to a draft sales order (easier than submitted orders)"""
	if isinstance(items_data, str):
		items_data = json.loads(items_data)
	
	try:
		# Debug logging
		frappe.log_error(f"=== DEBUG: add_items_to_draft_order called ===", "Add Items to Draft Debug")
		frappe.log_error(f"order_name parameter: {order_name}", "Add Items to Draft Debug")
		frappe.log_error(f"items_data count: {len(items_data) if items_data else 0}", "Add Items to Draft Debug")
		
		# Check if the order exists
		if not frappe.db.exists("Sales Order", order_name):
			frappe.throw(_("Sales Order {0} not found").format(order_name))
		
		order = frappe.get_doc("Sales Order", order_name)
		
		if order.docstatus != 0:
			frappe.throw(_("Can only add items to draft orders"))
		
		# Add new items to the draft order (check for existing items and increment qty)
		for item_data in items_data:
			# Look for existing item with same item_code, rate, and basic properties
			existing_item = None
			for existing in order.items:
				if (existing.item_code == item_data.get("item_code") and 
					existing.rate == item_data.get("rate") and
					existing.uom == item_data.get("uom")):
					existing_item = existing
					break
			
			if existing_item:
				# Increment quantity of existing item
				existing_item.qty += item_data.get("qty", 1)
				# Recalculate amount
				existing_item.amount = existing_item.qty * existing_item.rate
				frappe.log_error(f"Incremented qty for existing item {existing_item.item_code}: {existing_item.qty}", "Add Items to Draft Debug")
			else:
				# Add as new item
				order.append("items", item_data)
				frappe.log_error(f"Added new item {item_data.get('item_code')}", "Add Items to Draft Debug")
		
		# Recalculate totals and save
		order.calculate_taxes_and_totals()
		order.save()
		
		frappe.log_error(f"Successfully added items to draft Sales Order: {order.name}", "Add Items to Draft Success")
		return order
		
	except Exception as e:
		frappe.log_error(f"Error adding items to draft order {order_name}: {str(e)} - Type: {type(e).__name__}", "Add Items to Draft Error")
		frappe.throw(_("Error adding items to order: {0}").format(str(e)))

@frappe.whitelist()
def add_items_to_existing_order(order_name, items_data):
	"""Add new items to an existing submitted sales order"""
	if isinstance(items_data, str):
		items_data = json.loads(items_data)
	
	try:
		# Extensive debug logging
		frappe.log_error(f"=== DEBUG: add_items_to_existing_order called ===", "Add Items Debug")
		frappe.log_error(f"order_name parameter: {order_name}", "Add Items Debug")
		frappe.log_error(f"items_data count: {len(items_data) if items_data else 0}", "Add Items Debug")
		
		# Check if the order exists as Sales Order
		if not frappe.db.exists("Sales Order", order_name):
			frappe.log_error(f"Sales Order {order_name} does not exist in database", "Add Items Error")
			# Check if it exists as Sales Invoice instead
			if frappe.db.exists("Sales Invoice", order_name):
				frappe.log_error(f"Document {order_name} exists as Sales Invoice, not Sales Order!", "Add Items Error")
				frappe.throw(_("Document {0} is a Sales Invoice, not a Sales Order. Cannot add items to orders that have been converted to invoices.").format(order_name))
			else:
				frappe.log_error(f"Document {order_name} does not exist in any form", "Add Items Error")
				frappe.throw(_("Sales Order {0} not found").format(order_name))
		
		# Log the attempt to fetch
		frappe.log_error(f"Attempting to fetch Sales Order: {order_name}", "Add Items Debug")
		
		order = frappe.get_doc("Sales Order", order_name)
		
		frappe.log_error(f"Successfully fetched Sales Order: {order.name}, docstatus: {order.docstatus}, per_billed: {order.per_billed}", "Add Items Debug")
		
		if order.docstatus != 1:
			frappe.throw(_("Can only add items to submitted orders"))
		
		if order.per_billed >= 100:
			frappe.throw(_("Cannot add items to fully billed orders"))
		
		# Store existing items
		existing_items = [item.as_dict() for item in order.items]
		
		# Cancel the order to allow modifications
		order.cancel()
		
		# Keep existing items and add new ones
		order.items = []
		
		# Re-add existing items and merge with new items
		existing_items_dict = {}
		for item_data in existing_items:
			# Remove some auto-generated fields that might cause issues
			item_data.pop('name', None)
			item_data.pop('creation', None)
			item_data.pop('modified', None)
			item_data.pop('modified_by', None)
			item_data.pop('owner', None)
			item_data.pop('docstatus', None)
			
			# Create a key for grouping items (item_code + rate + uom)
			item_key = f"{item_data.get('item_code')}_{item_data.get('rate')}_{item_data.get('uom')}"
			existing_items_dict[item_key] = item_data
		
		# Process new items - merge with existing or add as new
		for item_data in items_data:
			item_key = f"{item_data.get('item_code')}_{item_data.get('rate')}_{item_data.get('uom')}"
			
			if item_key in existing_items_dict:
				# Increment quantity of existing item
				existing_items_dict[item_key]['qty'] += item_data.get('qty', 1)
				# Recalculate amount
				existing_items_dict[item_key]['amount'] = existing_items_dict[item_key]['qty'] * existing_items_dict[item_key]['rate']
				frappe.log_error(f"Incremented qty for existing item {item_data.get('item_code')}: {existing_items_dict[item_key]['qty']}", "Add Items Debug")
			else:
				# Add as new item
				existing_items_dict[item_key] = item_data
				frappe.log_error(f"Added new item {item_data.get('item_code')}", "Add Items Debug")
		
		# Add all items (existing + new) to the order
		for item_data in existing_items_dict.values():
			order.append("items", item_data)
		
		# Recalculate and resubmit
		order.calculate_taxes_and_totals()
		order.save()
		order.submit()
		
		frappe.log_error(f"Successfully added items to Sales Order: {order.name}", "Add Items Success")
		return order
		
	except frappe.DoesNotExistError as e:
		frappe.log_error(f"Sales Order {order_name} not found - DoesNotExistError: {str(e)}", "Add Items Error")
		frappe.throw(_("Sales Order {0} not found").format(order_name))
	except Exception as e:
		frappe.log_error(f"Error adding items to order {order_name}: {str(e)} - Type: {type(e).__name__}", "Add Items Error")
		frappe.throw(_("Error adding items to order: {0}").format(str(e)))

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
		temp_order_name = f"new-multi-order-{timestamp}"
		
		frappe.log_error(f"Creating new consolidated order: {temp_order_name}", "Multi Order Load Debug")
		
		consolidated_items = []
		
		# Collect all items from all orders (keep items separate, do not combine quantities)
		# This ensures proper Sales Order line item linking in the final Sales Invoice
		frappe.log_error(f"Starting item consolidation for {len(orders)} orders", "Multi Order Load Debug")
		
		for order in orders:
			frappe.log_error(f"Processing items from order {order.name}: {len(order.items)} items", "Multi Order Load Debug")
			for item in order.items:
				# Always add each item separately, even if same item_code exists
				# This ensures items from different orders remain distinct for proper SO->SI linking
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
					'source_order_item': item.name,  # Track original item reference for SO->SI linking
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
		
		# CRITICAL DEBUGGING: Log what we're actually returning
		print(f"=== LOAD_MULTIPLE_DRAFT_ORDERS RETURN DEBUG ===")
		print(f"Returning result keys: {list(result.keys())}")
		print(f"source_orders in result: {result.get('source_orders', 'NOT_IN_RESULT')}")
		print(f"multi_order_names in result: {result.get('multi_order_names', 'NOT_IN_RESULT')}")
		print(f"is_multi_order_consolidation in result: {result.get('is_multi_order_consolidation', 'NOT_IN_RESULT')}")
		
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
		print("=== FINALIZE MULTI ORDER PAYMENT DEBUG START ===")
		print(f"consolidated_order_data type: {type(consolidated_order_data)}")
		print(f"consolidated_order_data keys: {list(consolidated_order_data.keys()) if isinstance(consolidated_order_data, dict) else 'Not a dict'}")
		
		# Log all the critical fields we're looking for
		print(f"source_orders field: {consolidated_order_data.get('source_orders', 'FIELD_NOT_FOUND')}")
		print(f"multi_order_names field: {consolidated_order_data.get('multi_order_names', 'FIELD_NOT_FOUND')}")
		print(f"is_multi_order_consolidation field: {consolidated_order_data.get('is_multi_order_consolidation', 'FIELD_NOT_FOUND')}")
		
		# Validate that this is a multi-order consolidation
		if not consolidated_order_data.get('is_multi_order_consolidation'):
			print("ERROR: Missing is_multi_order_consolidation flag!")
			frappe.throw(_("This function is only for multi-order consolidations"))
		
		source_orders = consolidated_order_data.get('source_orders', [])		# Try alternative field names if source_orders is empty
		if not source_orders:
			source_orders = consolidated_order_data.get('multi_order_names', [])
		
		if not source_orders:
			# Additional debugging for missing source_orders
			print(f"ERROR: Missing source_orders! Available keys: {list(consolidated_order_data.keys())}")
			print(f"Full data: {consolidated_order_data}")
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
		if payment_data:
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
		
		# Return the invoice data in the same format as normal POS invoice submission
		result = {
			'doctype': 'Sales Invoice',
			'name': invoice_doc.name,
			'customer': invoice_doc.customer,
			'customer_name': invoice_doc.customer_name,
			'posting_date': str(invoice_doc.posting_date),
			'posting_time': invoice_doc.posting_time,
			'company': invoice_doc.company,
			'currency': invoice_doc.currency,
			'net_total': invoice_doc.net_total,
			'grand_total': invoice_doc.grand_total,
			'rounded_total': invoice_doc.rounded_total,
			'is_pos': invoice_doc.is_pos,
			'pos_profile': invoice_doc.pos_profile,
			'docstatus': invoice_doc.docstatus,
			'status': 'Paid',
			# Multi-order specific fields
			'is_multi_order_payment': True,
			'source_draft_orders': source_orders,
			'items': [item.as_dict() for item in invoice_doc.items],
			'payments': [payment.as_dict() for payment in invoice_doc.payments],
			# Include restaurant fields if they exist
			'restaurant_order_type': getattr(invoice_doc, 'restaurant_order_type', None),
			'table_number': getattr(invoice_doc, 'table_number', None),
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
		frappe.logger().error(f"ERROR in finalize_multi_order_payment: {error_msg}")
		frappe.logger().error(f"Traceback: {frappe.get_traceback()}")
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

@frappe.whitelist()
def void_order_items(order_name, items_to_void):
	"""Void specific items from a restaurant order"""
	try:
		if isinstance(items_to_void, str):
			items_to_void = json.loads(items_to_void)
		
		# Get a fresh copy of the document to avoid timestamp mismatch
		order_doc = frappe.get_doc("Sales Order", order_name)
		
		# Verify it's a draft order
		if order_doc.docstatus != 0:
			frappe.throw(_("Can only void items from draft orders"))
		
		# Create a list of items to keep and track voided items
		items_to_keep = []
		voided_items = []
		
		for item in order_doc.items:
			# Check if this item should be partially or fully voided
			void_qty = 0
			void_item_data = None
			
			for void_item in items_to_void:
				if item.idx == void_item.get("idx"):
					void_qty = float(void_item.get("qty", 0))
					void_item_data = void_item
					break
			
			if void_qty > 0:
				# Validate void quantity
				if void_qty > item.qty:
					frappe.throw(_("Cannot void {0} quantity of {1}. Only {2} available.").format(void_qty, item.item_name, item.qty))
				
				if void_qty == item.qty:
					# Void entire item - don't add to items_to_keep
					voided_items.append({
						"item_name": item.item_name,
						"qty": item.qty,
						"amount": item.amount
					})
				else:
					# Partial void - update quantity and add to items_to_keep
					remaining_qty = item.qty - void_qty
					void_amount = (item.amount / item.qty) * void_qty
					remaining_amount = item.amount - void_amount
					
					# Update item with remaining quantity
					item.qty = remaining_qty
					item.amount = remaining_amount
					
					# Recalculate item-level totals
					item.net_amount = remaining_amount
					item.base_amount = remaining_amount
					item.base_net_amount = remaining_amount
					
					items_to_keep.append(item)
					
					voided_items.append({
						"item_name": item.item_name,
						"qty": void_qty,
						"amount": void_amount
					})
			else:
				# Item not being voided - keep as is
				items_to_keep.append(item)
		
		# Check if there are items left after voiding
		if not items_to_keep:
			frappe.throw(_("Cannot void all items. At least one item must remain in the order."))
		
		# Update the order with remaining items
		order_doc.items = []
		for item in items_to_keep:
			order_doc.append("items", item)
		
		# Recalculate totals
		order_doc.calculate_taxes_and_totals()
		
		# Save the updated order with flags to bypass timestamp check
		order_doc.flags.ignore_permissions = True
		order_doc.flags.ignore_validate_update_after_submit = True
		order_doc.flags.ignore_version = True
		order_doc.save(ignore_permissions=True, ignore_version=True)
		
		# Explicitly commit the transaction to ensure persistence
		frappe.db.commit()
		
		# Reload the document to verify changes were saved
		updated_doc = frappe.get_doc("Sales Order", order_name)
		
		# Generate KOT print for voided items
		void_kot_data = None
		try:
			void_kot_data = generate_void_kot_print(updated_doc, voided_items)
		except Exception as e:
			frappe.log_error(f"Error generating void KOT: {str(e)}", "Void KOT Generation Error")
		
		# Log the void action
		frappe.log_error(
			f"Successfully voided {len(voided_items)} items from order {order_name}: {', '.join([item['item_name'] for item in voided_items])}. Remaining items: {len(updated_doc.items)}", 
			"Restaurant Order Items Voided"
		)
		
		result = {
			"status": "success",
			"message": _("Items voided successfully"),
			"voided_items": voided_items,
			"remaining_items": len(updated_doc.items),
			"updated_total": updated_doc.grand_total
		}
		
		# Add KOT data to response if generated successfully
		if void_kot_data:
			result["void_kot_data"] = void_kot_data
			result["print_void_kot"] = True
			
		return result
		
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(f"Error voiding items from order {order_name}: {str(e)}\n{frappe.get_traceback()}", "Void Items Error")
		frappe.throw(_("Error voiding items: {0}").format(str(e)))

@frappe.whitelist()
def debug_test_consolidation():
	"""Debug function to test multi-order consolidation data preservation"""
	
	# Test 1: Create sample consolidation data with proper fields
	sample_data = {
		"name": "debug-test-invoice",
		"doctype": "Sales Invoice",
		"customer": "Test Customer", 
		"grand_total": 100,
		"is_multi_order_consolidation": True,
		"source_orders": ["test-order-1", "test-order-2"],
		"multi_order_names": ["test-order-1", "test-order-2"],
		"payments": [{"mode_of_payment": "Cash", "amount": 100}]
	}
	
	frappe.logger().info("=== Debug Consolidation Test ===")
	frappe.logger().info(f"Sample data created with keys: {list(sample_data.keys())}")
	frappe.logger().info(f"source_orders: {sample_data.get('source_orders')}")
	frappe.logger().info(f"multi_order_names: {sample_data.get('multi_order_names')}")
	frappe.logger().info(f"is_multi_order_consolidation: {sample_data.get('is_multi_order_consolidation')}")
	
	# Test 2: Call finalize_multi_order_payment directly
	try:
		result = finalize_multi_order_payment(sample_data, {}, "Test-Profile")
		frappe.logger().info(f"finalize_multi_order_payment result: {result}")
		return {"status": "success", "result": result, "test_data": sample_data}
	except Exception as e:
		error_msg = f"finalize_multi_order_payment error: {str(e)}"
		frappe.logger().error(error_msg)
		return {"status": "error", "error": error_msg, "test_data": sample_data}