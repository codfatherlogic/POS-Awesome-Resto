import frappe

def execute():
    """Remove QZ Tray fields from POS Profile"""
    try:
        # List of QZ Tray fields to remove
        qz_fields = [
            "posa_enable_qz_tray",
            "posa_direct_order_printer", 
            "posa_kot_printer"
        ]
        
        for field_name in qz_fields:
            # Check if the custom field exists before trying to delete it
            if frappe.db.exists("Custom Field", {"dt": "POS Profile", "fieldname": field_name}):
                frappe.delete_doc("Custom Field", frappe.db.get_value("Custom Field", 
                    {"dt": "POS Profile", "fieldname": field_name}, "name"))
                print(f"Removed custom field: {field_name}")
            else:
                print(f"Custom field {field_name} not found, skipping")
        
        frappe.db.commit()
        print("QZ Tray fields removed successfully")
        
    except Exception as e:
        print(f"Error removing QZ Tray fields: {str(e)}")
        frappe.db.rollback()
