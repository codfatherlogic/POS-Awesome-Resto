#!/usr/bin/env python3
"""
Direct installation script for POSAwesome Restaurant Custom Fields
Run this script to create the required custom fields for restaurant functionality.

Usage:
1. Copy this file to your frappe-bench directory
2. Run: python install_restaurant_fields.py --site your-site-name
"""

import frappe
import sys
import argparse

def create_custom_field(doctype, fieldname, fieldtype, label, insert_after, **kwargs):
    """Create a custom field if it doesn't exist"""
    field_name = f"{doctype}-{fieldname}"
    
    if frappe.db.exists("Custom Field", field_name):
        print(f"✓ Field {field_name} already exists")
        return False
    
    try:
        custom_field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": doctype,
            "fieldname": fieldname,
            "fieldtype": fieldtype,
            "label": label,
            "insert_after": insert_after,
            **kwargs
        })
        custom_field.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"✓ Created field: {field_name}")
        return True
    except Exception as e:
        print(f"✗ Error creating field {field_name}: {str(e)}")
        return False

def install_restaurant_fields():
    """Install all restaurant custom fields"""
    print("Installing POSAwesome Restaurant Custom Fields...")
    print("=" * 50)
    
    created_count = 0
    
    # POS Profile Fields
    print("\n1. Creating POS Profile fields...")
    
    if create_custom_field(
        doctype="POS Profile",
        fieldname="posa_restaurant_section",
        fieldtype="Section Break",
        label="Restaurant Settings",
        insert_after="posa_language"
    ):
        created_count += 1
    
    if create_custom_field(
        doctype="POS Profile", 
        fieldname="posa_enable_restaurant_mode",
        fieldtype="Check",
        label="Enable Restaurant Mode",
        insert_after="posa_restaurant_section",
        description="Enable restaurant ordering features (Take Away, Dine In, Table Management)",
        default="0"
    ):
        created_count += 1
    
    if create_custom_field(
        doctype="POS Profile", 
        fieldname="posa_auto_print_kot",
        fieldtype="Check",
        label="Auto Print KOT on Make Order",
        insert_after="posa_enable_restaurant_mode",
        description="Automatically print Kitchen Order Ticket when order is created",
        default="0",
        depends_on="eval:doc.posa_enable_restaurant_mode"
    ):
        created_count += 1
    
    # Sales Order Fields
    print("\n2. Creating Sales Order fields...")
    
    if create_custom_field(
        doctype="Sales Order",
        fieldname="restaurant_order_type", 
        fieldtype="Link",
        label="Restaurant Order Type",
        insert_after="order_type",
        options="Restaurant Order Type"
    ):
        created_count += 1
    
    if create_custom_field(
        doctype="Sales Order",
        fieldname="table_number",
        fieldtype="Data", 
        label="Table Number",
        insert_after="restaurant_order_type",
        depends_on="eval:doc.restaurant_order_type"
    ):
        created_count += 1
    
    if create_custom_field(
        doctype="Sales Order",
        fieldname="expected_preparation_time",
        fieldtype="Int",
        label="Expected Preparation Time (minutes)",
        insert_after="table_number",
        depends_on="eval:doc.restaurant_order_type"
    ):
        created_count += 1
    
    # Sales Invoice Fields  
    print("\n3. Creating Sales Invoice fields...")
    
    if create_custom_field(
        doctype="Sales Invoice",
        fieldname="restaurant_order_type",
        fieldtype="Link", 
        label="Restaurant Order Type",
        insert_after="pos_profile",
        options="Restaurant Order Type"
    ):
        created_count += 1
    
    if create_custom_field(
        doctype="Sales Invoice",
        fieldname="table_number",
        fieldtype="Data",
        label="Table Number", 
        insert_after="restaurant_order_type",
        depends_on="eval:doc.restaurant_order_type"
    ):
        created_count += 1
    
    if create_custom_field(
        doctype="Sales Invoice",
        fieldname="expected_preparation_time",
        fieldtype="Int",
        label="Expected Preparation Time (minutes)",
        insert_after="table_number", 
        depends_on="eval:doc.restaurant_order_type"
    ):
        created_count += 1
    
    print("\n" + "=" * 50)
    print(f"Installation completed! Created {created_count} new custom fields.")
    print("\nNext steps:")
    print("1. Go to POS Profile in ERPNext")
    print("2. Look for 'Restaurant Settings' section")
    print("3. Enable 'Enable Restaurant Mode' checkbox")
    print("4. Save the POS Profile")
    print("5. Restaurant features will appear in POSAwesome")
    
    return created_count

def main():
    parser = argparse.ArgumentParser(description='Install POSAwesome Restaurant Custom Fields')
    parser.add_argument('--site', required=True, help='Site name')
    args = parser.parse_args()
    
    # Initialize Frappe
    frappe.init(site=args.site)
    frappe.connect()
    
    try:
        install_restaurant_fields()
    except Exception as e:
        print(f"Error during installation: {str(e)}")
        sys.exit(1)
    finally:
        frappe.destroy()

if __name__ == "__main__":
    main()