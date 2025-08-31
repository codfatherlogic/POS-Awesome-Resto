"""
Quick setup script for restaurant data
Run this in Frappe console after enabling restaurant mode
"""

import frappe

def create_restaurant_order_types():
    """Create default restaurant order types"""
    order_types = [
        {
            "order_type_name": "Take Away",
            "description": "Customer taking order to go",
            "requires_table": 0,
            "default_preparation_time": 10,
            "enabled": 1
        },
        {
            "order_type_name": "Dine In", 
            "description": "Customer dining in the restaurant",
            "requires_table": 1,
            "default_preparation_time": 15,
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
    
    created = []
    for order_type in order_types:
        if not frappe.db.exists("Restaurant Order Type", order_type["order_type_name"]):
            doc = frappe.get_doc({
                "doctype": "Restaurant Order Type",
                **order_type
            })
            doc.insert(ignore_permissions=True)
            created.append(order_type["order_type_name"])
            print(f"Created order type: {order_type['order_type_name']}")
    
    return created

def create_restaurant_tables():
    """Create sample restaurant tables"""
    tables = [
        {"table_number": "T01", "table_name": "Table 1", "capacity": 2, "location": "Window Side"},
        {"table_number": "T02", "table_name": "Table 2", "capacity": 4, "location": "Center"},
        {"table_number": "T03", "table_name": "Table 3", "capacity": 6, "location": "Corner"},
        {"table_number": "T04", "table_name": "Table 4", "capacity": 2, "location": "Bar Area"},
        {"table_number": "T05", "table_name": "Table 5", "capacity": 8, "location": "Private Room"},
    ]
    
    created = []
    for table_data in tables:
        if not frappe.db.exists("Restaurant Table", table_data["table_number"]):
            doc = frappe.get_doc({
                "doctype": "Restaurant Table",
                "status": "Available",
                "enabled": 1,
                **table_data
            })
            doc.insert(ignore_permissions=True)
            created.append(table_data["table_number"])
            print(f"Created table: {table_data['table_number']}")
    
    return created

# Run the setup
print("Setting up restaurant data...")
order_types = create_restaurant_order_types()
tables = create_restaurant_tables()

frappe.db.commit()

print(f"\n✅ Setup completed!")
print(f"Created {len(order_types)} order types: {', '.join(order_types)}")
print(f"Created {len(tables)} tables: {', '.join(tables)}")
print("\nNow refresh POSAwesome and the restaurant interface should appear!")