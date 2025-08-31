# -*- coding: utf-8 -*-
# Copyright (c) 2025, Youssef Restom and contributors
# For license information, please see license.txt

import frappe
from frappe import _

@frappe.whitelist()
def create_restaurant_custom_fields():
    """Create custom fields for restaurant functionality"""
    
    # POS Profile Restaurant Fields
    pos_profile_fields = [
        {
            "fieldname": "posa_restaurant_section",
            "fieldtype": "Section Break",
            "label": "Restaurant Settings",
            "insert_after": "posa_language"
        },
        {
            "fieldname": "posa_enable_restaurant_mode",
            "fieldtype": "Check",
            "label": "Enable Restaurant Mode",
            "description": "Enable restaurant ordering features (Take Away, Dine In, Table Management)",
            "default": "0",
            "insert_after": "posa_restaurant_section"
        }
    ]
    
    # Sales Order Restaurant Fields
    sales_order_fields = [
        {
            "fieldname": "restaurant_order_type",
            "fieldtype": "Link",
            "label": "Restaurant Order Type",
            "options": "Restaurant Order Type",
            "insert_after": "order_type"
        },
        {
            "fieldname": "table_number",
            "fieldtype": "Data",
            "label": "Table Number",
            "depends_on": "eval:doc.restaurant_order_type",
            "insert_after": "restaurant_order_type"
        },
        {
            "fieldname": "expected_preparation_time",
            "fieldtype": "Int",
            "label": "Expected Preparation Time (minutes)",
            "depends_on": "eval:doc.restaurant_order_type",
            "insert_after": "table_number"
        }
    ]
    
    # Sales Invoice Restaurant Fields
    sales_invoice_fields = [
        {
            "fieldname": "restaurant_order_type",
            "fieldtype": "Link",
            "label": "Restaurant Order Type",
            "options": "Restaurant Order Type",
            "insert_after": "pos_profile"
        },
        {
            "fieldname": "table_number",
            "fieldtype": "Data",
            "label": "Table Number",
            "depends_on": "eval:doc.restaurant_order_type",
            "insert_after": "restaurant_order_type"
        },
        {
            "fieldname": "expected_preparation_time",
            "fieldtype": "Int",
            "label": "Expected Preparation Time (minutes)",
            "depends_on": "eval:doc.restaurant_order_type",
            "insert_after": "table_number"
        }
    ]
    
    # Create fields for each doctype
    doctypes_fields = [
        ("POS Profile", pos_profile_fields),
        ("Sales Order", sales_order_fields),
        ("Sales Invoice", sales_invoice_fields)
    ]
    
    created_fields = []
    
    for doctype, fields in doctypes_fields:
        for field_data in fields:
            field_name = f"{doctype}-{field_data['fieldname']}"
            
            # Check if field already exists
            if not frappe.db.exists("Custom Field", field_name):
                try:
                    custom_field = frappe.get_doc({
                        "doctype": "Custom Field",
                        "dt": doctype,
                        **field_data
                    })
                    custom_field.insert(ignore_permissions=True)
                    created_fields.append(field_name)
                    frappe.db.commit()
                except Exception as e:
                    frappe.log_error(f"Error creating custom field {field_name}: {str(e)}")
    
    return {
        "success": True,
        "created_fields": created_fields,
        "message": f"Created {len(created_fields)} custom fields for restaurant functionality"
    }

@frappe.whitelist()
def setup_complete_restaurant_system():
    """Complete restaurant system setup"""
    
    # 1. Create custom fields
    fields_result = create_restaurant_custom_fields()
    
    # 2. Create default order types
    from posawesome.posawesome.doctype.restaurant_order_type.restaurant_order_type import create_default_order_types
    order_types = create_default_order_types()
    
    # 3. Create sample tables
    from posawesome.posawesome.doctype.restaurant_table.restaurant_table import create_sample_tables
    tables = create_sample_tables()
    
    return {
        "success": True,
        "custom_fields_created": fields_result.get("created_fields", []),
        "order_types_created": order_types,
        "tables_created": tables,
        "message": "Restaurant system setup completed successfully!"
    }

@frappe.whitelist()
def check_restaurant_setup():
    """Check if restaurant system is properly set up"""
    
    # Check custom fields
    required_fields = [
        "POS Profile-posa_restaurant_section",
        "POS Profile-posa_enable_restaurant_mode",
        "Sales Order-restaurant_order_type",
        "Sales Order-table_number",
        "Sales Order-expected_preparation_time",
        "Sales Invoice-restaurant_order_type",
        "Sales Invoice-table_number",
        "Sales Invoice-expected_preparation_time"
    ]
    
    missing_fields = []
    for field in required_fields:
        if not frappe.db.exists("Custom Field", field):
            missing_fields.append(field)
    
    # Check order types
    order_types_count = frappe.db.count("Restaurant Order Type", {"enabled": 1})
    
    # Check tables
    tables_count = frappe.db.count("Restaurant Table", {"enabled": 1})
    
    return {
        "custom_fields_missing": missing_fields,
        "custom_fields_ok": len(missing_fields) == 0,
        "order_types_count": order_types_count,
        "tables_count": tables_count,
        "setup_complete": len(missing_fields) == 0 and order_types_count > 0
    }