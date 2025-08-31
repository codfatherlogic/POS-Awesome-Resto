"""
Simple script to create restaurant custom fields
Run this in Frappe console: bench --site your-site-name console
Then: exec(open('apps/posawesome/create_restaurant_fields.py').read())
"""

import frappe

def create_field(doctype, fieldname, fieldtype, label, insert_after, **kwargs):
    field_name = f"{doctype}-{fieldname}"
    if frappe.db.exists("Custom Field", field_name):
        print(f"Field {field_name} already exists")
        return
    
    doc = frappe.get_doc({
        "doctype": "Custom Field",
        "dt": doctype,
        "fieldname": fieldname,
        "fieldtype": fieldtype,
        "label": label,
        "insert_after": insert_after,
        **kwargs
    })
    doc.insert(ignore_permissions=True)
    print(f"Created: {field_name}")

print("Creating Restaurant Custom Fields...")

# POS Profile
create_field("POS Profile", "posa_restaurant_section", "Section Break", "Restaurant Settings", "posa_language")
create_field("POS Profile", "posa_enable_restaurant_mode", "Check", "Enable Restaurant Mode", "posa_restaurant_section", default="0")

# Sales Order  
create_field("Sales Order", "restaurant_order_type", "Link", "Restaurant Order Type", "order_type", options="Restaurant Order Type")
create_field("Sales Order", "table_number", "Data", "Table Number", "restaurant_order_type", depends_on="eval:doc.restaurant_order_type")
create_field("Sales Order", "expected_preparation_time", "Int", "Expected Preparation Time (minutes)", "table_number", depends_on="eval:doc.restaurant_order_type")

# Sales Invoice
create_field("Sales Invoice", "restaurant_order_type", "Link", "Restaurant Order Type", "pos_profile", options="Restaurant Order Type")  
create_field("Sales Invoice", "table_number", "Data", "Table Number", "restaurant_order_type", depends_on="eval:doc.restaurant_order_type")
create_field("Sales Invoice", "expected_preparation_time", "Int", "Expected Preparation Time (minutes)", "table_number", depends_on="eval:doc.restaurant_order_type")

frappe.db.commit()
print("All restaurant custom fields created successfully!")
print("Now go to POS Profile and enable 'Enable Restaurant Mode'")