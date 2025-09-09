import frappe


def execute():
    """Add Order Mode field to POS Profile for Direct Order features"""
    
    # Add Order Mode field
    if not frappe.db.exists("Custom Field", "POS Profile-posa_order_mode"):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "POS Profile",
            "fieldname": "posa_order_mode",
            "fieldtype": "Select",
            "label": "Order Mode",
            "options": "\nStandard\nDirect Order\nDirect Order + KOT",
            "default": "Standard",
            "description": "Standard: Full restaurant mode with order creation | Direct Order: Skip order creation, bill directly | Direct Order + KOT: Direct billing with KOT print",
            "depends_on": "eval:doc.posa_enable_restaurant_mode",
            "insert_after": "posa_enable_restaurant_mode"
        }).insert()
        
        frappe.db.commit()
        print("Added Order Mode field to POS Profile")
