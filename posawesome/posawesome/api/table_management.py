# -*- coding: utf-8 -*-
# Copyright (c) 2025, Youssef Restom and contributors
# For license information, please see license.txt

import frappe
from frappe import _

@frappe.whitelist()
def sync_table_occupations():
	"""Sync table occupations with existing restaurant orders"""
	
	# Get all open restaurant orders (Draft and Submitted but not fully billed)
	open_orders = frappe.get_all(
		"Sales Order",
		filters={
			"restaurant_order_type": ["is", "set"],
			"table_number": ["is", "set"],
			"docstatus": ["in", [0, 1]],
			"per_billed": ["<", 100]
		},
		fields=["name", "table_number", "docstatus", "per_billed"]
	)
	
	# Get all tables currently marked as occupied
	occupied_tables = frappe.get_all(
		"Restaurant Table",
		filters={"status": "Occupied"},
		fields=["name", "table_number", "current_order", "status"]
	)
	
	# Create a map of table_number to current_order for quick lookup
	table_occupation_map = {t.table_number: t.current_order for t in occupied_tables}
	
	synced_count = 0
	freed_count = 0
	errors = []
	
	# Process open orders - ensure tables are occupied
	for order in open_orders:
		try:
			table_number = order.table_number
			order_name = order.name
			
			# Check if table is properly occupied
			current_occupied_order = table_occupation_map.get(table_number)
			
			if current_occupied_order != order_name:
				# Table is either free or occupied by a different order
				# Occupy it with the current order
				table_doc = frappe.get_doc("Restaurant Table", table_number)
				table_doc.occupy_table(order_name)
				frappe.logger().info(f"Synced table {table_number} with order {order_name}")
				synced_count += 1
				
		except Exception as e:
			error_msg = f"Failed to sync table {order.table_number} with order {order.name}: {str(e)}"
			errors.append(error_msg)
			frappe.log_error(error_msg, "Table Sync Error")
	
	# Free tables that are occupied by completed/cancelled orders
	for table in occupied_tables:
		try:
			if table.current_order:
				# Check if the order still exists and is still open
				order_exists = frappe.db.exists("Sales Order", table.current_order)
				if order_exists:
					order = frappe.get_doc("Sales Order", table.current_order)
					# Free table if order is cancelled or fully billed
					if order.docstatus == 2 or order.per_billed >= 100:
						table_doc = frappe.get_doc("Restaurant Table", table.name)
						table_doc.free_table()
						frappe.logger().info(f"Freed table {table.table_number} from completed order {table.current_order}")
						freed_count += 1
				else:
					# Order doesn't exist anymore, free the table
					table_doc = frappe.get_doc("Restaurant Table", table.name)
					table_doc.free_table()
					frappe.logger().info(f"Freed table {table.table_number} from non-existent order {table.current_order}")
					freed_count += 1
					
		except Exception as e:
			error_msg = f"Failed to check/free table {table.table_number}: {str(e)}"
			errors.append(error_msg)
			frappe.log_error(error_msg, "Table Free Error")
	
	# Commit all changes
	frappe.db.commit()
	
	result = {
		"success": True,
		"message": f"Table sync completed. Synced: {synced_count}, Freed: {freed_count}",
		"synced_count": synced_count,
		"freed_count": freed_count,
		"errors": errors
	}
	
	return result

@frappe.whitelist()
def check_table_order_consistency():
	"""Check consistency between table occupations and orders"""
	
	inconsistencies = []
	
	# Check orders that should have occupied tables
	open_orders = frappe.get_all(
		"Sales Order",
		filters={
			"restaurant_order_type": ["is", "set"],
			"table_number": ["is", "set"],
			"docstatus": ["in", [0, 1]],
			"per_billed": ["<", 100]
		},
		fields=["name", "table_number", "docstatus", "per_billed"]
	)
	
	for order in open_orders:
		try:
			table_doc = frappe.get_doc("Restaurant Table", order.table_number)
			if table_doc.status != "Occupied" or table_doc.current_order != order.name:
				inconsistencies.append({
					"type": "order_without_table",
					"order": order.name,
					"table": order.table_number,
					"table_status": table_doc.status,
					"table_current_order": table_doc.current_order
				})
		except Exception as e:
			inconsistencies.append({
				"type": "error",
				"order": order.name,
				"table": order.table_number,
				"error": str(e)
			})
	
	# Check tables that are occupied but shouldn't be
	occupied_tables = frappe.get_all(
		"Restaurant Table",
		filters={"status": "Occupied"},
		fields=["name", "table_number", "current_order"]
	)
	
	for table in occupied_tables:
		try:
			if table.current_order:
				order_exists = frappe.db.exists("Sales Order", table.current_order)
				if order_exists:
					order = frappe.get_doc("Sales Order", table.current_order)
					if order.docstatus == 2 or order.per_billed >= 100:
						inconsistencies.append({
							"type": "table_with_completed_order",
							"table": table.table_number,
							"order": table.current_order,
							"order_status": order.docstatus,
							"order_per_billed": order.per_billed
						})
				else:
					inconsistencies.append({
						"type": "table_with_nonexistent_order",
						"table": table.table_number,
						"order": table.current_order
					})
		except Exception as e:
			inconsistencies.append({
				"type": "error",
				"table": table.table_number,
				"error": str(e)
			})
	
	return {
		"success": True,
		"inconsistencies": inconsistencies,
		"total_issues": len(inconsistencies)
	}
