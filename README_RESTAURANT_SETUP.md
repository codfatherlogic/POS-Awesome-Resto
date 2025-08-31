# Restaurant Order System for POSAwesome

This implementation adds restaurant-style ordering functionality to POSAwesome, supporting Take Away, Dine In, and Delivery orders with table management and order-to-bill conversion.

## Features Added

### 1. Restaurant Order Types
- **Dine In**: Orders for customers dining in the restaurant (requires table selection)
- **Take Away**: Orders for customers taking food to go
- **Delivery**: Orders delivered to customer locations
- Configurable preparation times for each order type

### 2. Table Management
- Restaurant table creation and management
- Table status tracking (Available, Occupied, Reserved, Out of Service)
- Automatic table occupation when dine-in orders are placed
- Table capacity and location tracking

### 3. Order-to-Bill Conversion
- Seamless conversion from restaurant orders (Sales Orders) to bills (Sales Invoices)
- Automatic table freeing when orders are converted to bills
- Maintains order reference in the final invoice

## Installation & Setup

### 1. Install the Restaurant Module

After updating POSAwesome with the restaurant features, run:

```bash
# Navigate to your Frappe bench
cd /path/to/your/frappe-bench

# Install/update the app
bench --site your-site-name install-app posawesome

# Or if already installed, migrate
bench --site your-site-name migrate
```

### 2. Setup Restaurant System

**Option A: Complete Setup (Recommended)**
```python
# In Frappe console (bench --site your-site-name console)
import frappe
result = frappe.call("posawesome.posawesome.api.restaurant_setup.setup_complete_restaurant_system")
print(result)
```

**Option B: Manual Setup**
```python
# Step 1: Create custom fields
frappe.call("posawesome.posawesome.api.restaurant_setup.create_restaurant_custom_fields")

# Step 2: Create default data
frappe.call("posawesome.posawesome.api.restaurant_orders.setup_restaurant_data")
```

**Option C: Using API from browser console**
```javascript
// Complete setup
frappe.call({
    method: "posawesome.posawesome.api.restaurant_setup.setup_complete_restaurant_system",
    callback: function(r) {
        console.log("Restaurant setup completed:", r.message);
        frappe.msgprint("Restaurant system setup completed!");
    }
});
```

### 3. Verify Setup

Check if everything is properly installed:
```python
# Check setup status
result = frappe.call("posawesome.posawesome.api.restaurant_setup.check_restaurant_setup")
print(result)
```

### 4. Enable Restaurant Mode in POS Profile

1. Go to **POS Profile** in ERPNext
2. Find your POS Profile
3. Scroll down to **"Restaurant Settings"** section (should now be visible)
4. Check **"Enable Restaurant Mode"** checkbox
5. Save the POS Profile

## Usage

### 1. Creating Restaurant Orders

1. Open POSAwesome POS interface
2. Select order type (Dine In, Take Away, or Delivery)
3. If Dine In is selected, choose an available table
4. Add items to the order
5. Save as Sales Order (not direct invoice)

### 2. Managing Tables

- View table status in the Restaurant Table doctype
- Tables are automatically occupied when dine-in orders are placed
- Tables are freed when orders are converted to bills

### 3. Converting Orders to Bills

Use the existing Sales Order to Sales Invoice conversion:

```javascript
// Convert order to invoice
frappe.call({
    method: "posawesome.posawesome.api.restaurant_orders.convert_order_to_invoice",
    args: {
        sales_order_name: "SO-2025-00001"
    },
    callback: function(r) {
        console.log("Order converted to invoice:", r.message);
    }
});
```

## API Endpoints

### Restaurant Order Types
- `get_restaurant_order_types()` - Get all enabled order types
- `create_default_order_types()` - Create default order types

### Table Management  
- `get_available_tables()` - Get available tables for dine-in
- `get_table_status()` - Get status of all tables
- `occupy_table(table_name, order_name)` - Occupy a table
- `free_table(table_name)` - Free a table

### Order Management
- `create_restaurant_order(order_data)` - Create restaurant order
- `submit_restaurant_order(order_data)` - Submit restaurant order
- `convert_order_to_invoice(sales_order_name)` - Convert order to bill
- `get_restaurant_orders()` - Get restaurant orders with filters

## Database Schema

### Restaurant Order Type
- `order_type_name` - Name of the order type
- `requires_table` - Whether table selection is required
- `default_preparation_time` - Expected preparation time in minutes
- `enabled` - Whether the order type is active

### Restaurant Table
- `table_number` - Unique table identifier
- `table_name` - Display name for the table
- `capacity` - Seating capacity
- `location` - Table location/section
- `status` - Current status (Available/Occupied/Reserved/Out of Service)
- `current_order` - Reference to current Sales Order (if occupied)

### Sales Order Extensions
- `restaurant_order_type` - Link to Restaurant Order Type
- `table_number` - Table number for dine-in orders
- `expected_preparation_time` - Preparation time in minutes

## Workflow

1. **Order Placement**: Customer places order → Sales Order created with order type
2. **Kitchen Processing**: Kitchen receives order details and prepares food
3. **Order Ready**: Food is ready for pickup/serving
4. **Billing**: Order is converted to Sales Invoice for payment
5. **Table Management**: For dine-in orders, table is freed after billing

## Customization

### Adding New Order Types
```python
# Create custom order type
order_type = frappe.get_doc({
    "doctype": "Restaurant Order Type",
    "order_type_name": "Catering",
    "description": "Large orders for events",
    "requires_table": 0,
    "default_preparation_time": 60,
    "enabled": 1
})
order_type.insert()
```

### Adding Tables
```python
# Create new table
table = frappe.get_doc({
    "doctype": "Restaurant Table", 
    "table_number": "T10",
    "table_name": "VIP Table",
    "capacity": 4,
    "location": "VIP Section",
    "status": "Available",
    "enabled": 1
})
table.insert()
```

## Integration with Existing POSAwesome Features

- **Payment Processing**: Uses existing payment methods and processing
- **Stock Management**: Integrates with existing stock tracking
- **Customer Management**: Works with existing customer database
- **Printing**: Compatible with existing receipt printing
- **Offline Mode**: Supports offline order creation
- **Multi-currency**: Works with multi-currency setups

## Troubleshooting

### Restaurant Mode Not Showing
- Ensure `posa_enable_restaurant_mode` is enabled in POS Profile
- Check that restaurant order types exist and are enabled
- Verify custom fields are properly installed

### Tables Not Available
- Check that tables exist in Restaurant Table doctype
- Verify tables are enabled and status is "Available"
- Ensure table management permissions are set correctly

### Order Conversion Issues
- Verify Sales Order exists and is submitted
- Check that user has permissions to create Sales Invoices
- Ensure all required fields are populated in the order

## Support

For issues or questions regarding the restaurant functionality:

1. Check the error logs in ERPNext
2. Verify all custom fields are installed correctly
3. Ensure proper permissions are set for restaurant doctypes
4. Test with sample data first before production use

This restaurant system seamlessly integrates with POSAwesome's existing architecture while adding powerful restaurant-specific features for order management and table tracking.