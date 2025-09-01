#!/usr/bin/env python3

import frappe
import json
import os

def install_restaurant_custom_fields():
    """Install restaurant custom fields from the JSON file"""
    
    # Path to the restaurant custom fields file
    fields_file = os.path.join(frappe.get_app_path("posawesome"), "fixtures", "restaurant_custom_fields.json")
    
    # Load the custom fields data
    with open(fields_file, 'r') as f:
        fields_data = json.load(f)
    
    # Create each custom field
    for field_data in fields_data:
        try:
            # Check if field already exists
            if not frappe.db.exists("Custom Field", field_data["name"]):
                # Create new custom field
                custom_field = frappe.new_doc("Custom Field")
                custom_field.update(field_data)
                custom_field.insert()
                print(f"Created custom field: {field_data['name']}")
            else:
                print(f"Custom field already exists: {field_data['name']}")
        except Exception as e:
            print(f"Error creating custom field {field_data['name']}: {str(e)}")
    
    # Commit the changes
    frappe.db.commit()
    print("All restaurant custom fields have been installed successfully!")

if __name__ == "__main__":
    # Connect to Frappe
    frappe.init(site="pos")
    frappe.connect()
    
    # Install the custom fields
    install_restaurant_custom_fields()
