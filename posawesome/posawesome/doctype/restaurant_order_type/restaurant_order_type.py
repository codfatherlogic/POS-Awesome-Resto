# -*- coding: utf-8 -*-
# Copyright (c) 2025, Youssef Restom and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class RestaurantOrderType(Document):
	def validate(self):
		self.validate_order_type_name()
	
	def validate_order_type_name(self):
		if not self.order_type_name:
			frappe.throw("Order Type Name is required")
		
		# Check for duplicate order type names
		existing = frappe.db.get_value(
			"Restaurant Order Type", 
			{"order_type_name": self.order_type_name, "name": ["!=", self.name]}, 
			"name"
		)
		if existing:
			frappe.throw(f"Order Type '{self.order_type_name}' already exists")

@frappe.whitelist()
def get_enabled_order_types():
	"""Get all enabled restaurant order types"""
	return frappe.get_all(
		"Restaurant Order Type",
		filters={"enabled": 1},
		fields=["name", "order_type_name", "requires_table", "default_preparation_time"],
		order_by="order_type_name"
	)

@frappe.whitelist()
def create_default_order_types():
	"""Create default restaurant order types if they don't exist"""
	default_types = [
		{
			"order_type_name": "Dine In",
			"description": "Customer dining in the restaurant",
			"requires_table": 1,
			"default_preparation_time": 15,
			"enabled": 1
		},
		{
			"order_type_name": "Take Away",
			"description": "Customer taking order to go",
			"requires_table": 0,
			"default_preparation_time": 10,
			"enabled": 1
		},
		{
			"order_type_name": "Delivery",
			"description": "Order delivered to customer location",
			"requires_table": 0,
			"default_preparation_time": 20,
			"enabled": 1
		}
	]
	
	created_types = []
	for order_type in default_types:
		if not frappe.db.exists("Restaurant Order Type", order_type["order_type_name"]):
			doc = frappe.get_doc({
				"doctype": "Restaurant Order Type",
				**order_type
			})
			doc.insert(ignore_permissions=True)
			created_types.append(order_type["order_type_name"])
	
	return created_types