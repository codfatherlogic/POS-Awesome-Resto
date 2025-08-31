# -*- coding: utf-8 -*-
# Copyright (c) 2025, Youssef Restom and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class RestaurantTable(Document):
	def validate(self):
		self.validate_table_number()
		self.validate_capacity()
	
	def validate_table_number(self):
		if not self.table_number:
			frappe.throw("Table Number is required")
		
		# Check for duplicate table numbers
		existing = frappe.db.get_value(
			"Restaurant Table", 
			{"table_number": self.table_number, "name": ["!=", self.name]}, 
			"name"
		)
		if existing:
			frappe.throw(f"Table Number '{self.table_number}' already exists")
	
	def validate_capacity(self):
		if self.capacity and self.capacity < 1:
			frappe.throw("Seating Capacity must be at least 1")
	
	def occupy_table(self, order_name):
		"""Mark table as occupied with current order"""
		self.status = "Occupied"
		self.current_order = order_name
		self.save(ignore_permissions=True)
	
	def free_table(self):
		"""Mark table as available and clear current order"""
		self.status = "Available"
		self.current_order = None
		self.save(ignore_permissions=True)

@frappe.whitelist()
def get_available_tables():
	"""Get all available and enabled tables"""
	return frappe.get_all(
		"Restaurant Table",
		filters={"enabled": 1, "status": "Available"},
		fields=["name", "table_number", "table_name", "capacity", "location"],
		order_by="table_number"
	)

@frappe.whitelist()
def get_all_tables():
	"""Get all enabled tables with their status"""
	return frappe.get_all(
		"Restaurant Table",
		filters={"enabled": 1},
		fields=["name", "table_number", "table_name", "capacity", "location", "status", "current_order"],
		order_by="table_number"
	)

@frappe.whitelist()
def occupy_table(table_name, order_name):
	"""Occupy a table with an order"""
	table = frappe.get_doc("Restaurant Table", table_name)
	if table.status != "Available":
		frappe.throw(f"Table {table.table_number} is not available")
	
	table.occupy_table(order_name)
	return {"success": True, "message": f"Table {table.table_number} occupied"}

@frappe.whitelist()
def free_table(table_name):
	"""Free a table"""
	table = frappe.get_doc("Restaurant Table", table_name)
	table.free_table()
	return {"success": True, "message": f"Table {table.table_number} is now available"}

@frappe.whitelist()
def create_sample_tables():
	"""Create sample restaurant tables for testing"""
	sample_tables = [
		{"table_number": "T01", "table_name": "Table 1", "capacity": 2, "location": "Window Side"},
		{"table_number": "T02", "table_name": "Table 2", "capacity": 4, "location": "Center"},
		{"table_number": "T03", "table_name": "Table 3", "capacity": 6, "location": "Corner"},
		{"table_number": "T04", "table_name": "Table 4", "capacity": 2, "location": "Bar Area"},
		{"table_number": "T05", "table_name": "Table 5", "capacity": 8, "location": "Private Room"},
	]
	
	created_tables = []
	for table_data in sample_tables:
		if not frappe.db.exists("Restaurant Table", table_data["table_number"]):
			doc = frappe.get_doc({
				"doctype": "Restaurant Table",
				"status": "Available",
				"enabled": 1,
				**table_data
			})
			doc.insert(ignore_permissions=True)
			created_tables.append(table_data["table_number"])
	
	return created_tables