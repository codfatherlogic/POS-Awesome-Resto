import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	"""Add KOT Print Width field to POS Profile"""
	
	custom_fields = {
		"POS Profile": [
			{
				"fieldname": "posa_kot_print_width",
				"label": "KOT Print Width",
				"fieldtype": "Select",
				"options": "58mm\n80mm",
				"default": "58mm",
				"insert_after": "posa_auto_print_kot",
				"depends_on": "eval:doc.posa_enable_restaurant_mode",
				"description": "Select the print width for Kitchen Order Tickets (KOT)"
			}
		]
	}
	
	create_custom_fields(custom_fields, update=True)
	
	print("KOT Print Width field added to POS Profile successfully")
