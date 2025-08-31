# Restaurant Features Implementation Guide

This document provides a detailed explanation of the restaurant features implemented in the POS Awesome system and how to use them.

## Overview

The restaurant features enable a complete restaurant ordering workflow with the following capabilities:

1. **Order Type Selection** - Choose between Dine In, Take Away, and Delivery
2. **Table Management** - Select tables for Dine In orders
3. **Restaurant Orders View** - View and manage all restaurant orders
4. **Order-to-Payment Workflow** - Convert orders to payments seamlessly
5. **Enhanced UI** - Restaurant-specific button labels and validations

## Features Implemented

### 1. Show Orders Button and Orders List View

**Location**: [`InvoiceSummary.vue`](frontend/src/posapp/components/pos/InvoiceSummary.vue:122)

- When Restaurant Mode is enabled, the "Select S.O" button is replaced with "Show Orders"
- Clicking "Show Orders" opens a comprehensive dialog showing all restaurant orders
- The dialog includes filtering by order type, status, and search functionality

**Component**: [`RestaurantOrders.vue`](frontend/src/posapp/components/pos/RestaurantOrders.vue:1)

Features:
- Filter orders by Order Type (Dine In, Take Away, Delivery)
- Filter by Status (Draft, Submitted, Billed)
- Search by Order ID or Customer name
- View order details including table number, amount, and status
- Action buttons for Pay, Edit, and Cancel operations

### 2. Order Selection for Payment

**Implementation**: [`RestaurantOrders.vue`](frontend/src/posapp/components/pos/RestaurantOrders.vue:401)

- Orders with status "Submitted" can be selected for payment
- Click "Pay" button or select order and click "Convert to Payment"
- Order is loaded into the main invoice for payment processing
- Table is automatically freed when order is converted to invoice

### 3. Save & Clear Button Changes to Make Order

**Location**: [`InvoiceSummary.vue`](frontend/src/posapp/components/pos/InvoiceSummary.vue:106)

- In Restaurant Mode: Button shows "Make Order" with chef hat icon
- In Normal Mode: Button shows "Save & Clear" with save icon
- Functionality adapts based on restaurant mode settings

### 4. Order Type Selection Before Adding Items

**Implementation**: [`invoiceItemMethods.js`](frontend/src/posapp/components/pos/invoiceItemMethods.js:29)

Validation logic in [`add_item()`](frontend/src/posapp/components/pos/invoiceItemMethods.js:29):
- Checks if Order Type is selected before allowing items to be added
- Shows error message if Order Type is not selected
- Prevents item addition until requirements are met

### 5. Table Selection for Dine In Orders

**Implementation**: [`RestaurantOrderType.vue`](frontend/src/posapp/components/pos/RestaurantOrderType.vue:37)

- Table selection is shown only when Order Type requires a table
- Validation ensures table is selected for Dine In orders
- Visual indicators show required fields with asterisks
- Error styling for incomplete selections

## Backend API Enhancements

### Restaurant Orders API

**File**: [`restaurant_orders.py`](posawesome/posawesome/api/restaurant_orders.py:1)

Key methods:
- [`get_restaurant_order_types()`](posawesome/posawesome/api/restaurant_orders.py:12) - Fetch available order types
- [`get_available_tables()`](posawesome/posawesome/api/restaurant_orders.py:22) - Get available tables
- [`create_restaurant_order()`](posawesome/posawesome/api/restaurant_orders.py:32) - Create restaurant order with validation
- [`get_restaurant_orders()`](posawesome/posawesome/api/restaurant_orders.py:123) - Fetch orders with filtering
- [`cancel_restaurant_order()`](posawesome/posawesome/api/restaurant_orders.py:165) - Cancel order and free table

### Custom Fields

**File**: [`restaurant_custom_fields.json`](posawesome/fixtures/restaurant_custom_fields.json:1)

Added fields to Sales Order and Sales Invoice:
- `restaurant_order_type` - Link to Restaurant Order Type
- `table_number` - Table number for dine-in orders
- `expected_preparation_time` - Preparation time in minutes

## Workflow Implementation

### 1. Restaurant Mode Setup

Enable restaurant mode in POS Profile:
```javascript
pos_profile.posa_enable_restaurant_mode = 1
```

### 2. Order Creation Workflow

1. **Select Order Type** - Required before adding any items
2. **Select Table** - Required for Dine In orders only
3. **Add Items** - Items can only be added after order type (and table if needed) selection
4. **Make Order** - Click "Make Order" button to create restaurant order
5. **Order Management** - Use "Show Orders" to view and manage orders

### 3. Payment Workflow

1. **View Orders** - Click "Show Orders" to see all restaurant orders
2. **Select Order** - Choose an order with "Submitted" status
3. **Convert to Payment** - Click "Pay" or "Convert to Payment"
4. **Process Payment** - Complete payment in the payment dialog
5. **Table Management** - Table is automatically freed after payment

## Validation Rules

### Order Type Validation
- Order Type must be selected before adding items
- Error message: "Please select an Order Type before adding items"

### Table Validation
- Table must be selected for Dine In orders
- Error message: "Please select a table for [Order Type] orders"
- Table availability is checked before order creation

### Order Status Validation
- Only "Submitted" orders can be converted to payment
- "Draft" orders can be edited or cancelled
- "Billed" orders are read-only

## Component Structure

```
Pos.vue (Main Container)
├── Invoice.vue (Invoice Management)
│   ├── RestaurantOrderType.vue (Order Type & Table Selection)
│   └── InvoiceSummary.vue (Action Buttons)
├── RestaurantOrders.vue (Orders List Dialog)
└── Other Components...
```

## Event Flow

### Order Creation
1. User selects Order Type → [`RestaurantOrderType.vue`](frontend/src/posapp/components/pos/RestaurantOrderType.vue:142)
2. User selects Table (if required) → [`RestaurantOrderType.vue`](frontend/src/posapp/components/pos/RestaurantOrderType.vue:149)
3. User adds items → [`invoiceItemMethods.js`](frontend/src/posapp/components/pos/invoiceItemMethods.js:29) validates
4. User clicks "Make Order" → [`save_and_clear_invoice()`](frontend/src/posapp/components/pos/invoiceItemMethods.js:269)
5. Backend creates restaurant order → [`create_restaurant_order()`](posawesome/posawesome/api/restaurant_orders.py:32)

### Order Payment
1. User clicks "Show Orders" → [`show_restaurant_orders()`](frontend/src/posapp/components/pos/Invoice.vue:1272)
2. Orders dialog opens → [`RestaurantOrders.vue`](frontend/src/posapp/components/pos/RestaurantOrders.vue:276)
3. User selects order for payment → [`convert_to_payment()`](frontend/src/posapp/components/pos/RestaurantOrders.vue:406)
4. Order loads in main invoice → [`new_order()`](frontend/src/posapp/components/pos/invoiceItemMethods.js:321)
5. User processes payment normally

## Error Handling

### Frontend Validation
- Order Type selection validation
- Table selection validation for Dine In
- Item addition prevention without proper selection
- Visual error indicators and messages

### Backend Validation
- Order Type existence and enabled status
- Table availability checking
- Table occupation management
- Order status validation

## Testing the Implementation

### Prerequisites
1. Enable Restaurant Mode in POS Profile
2. Ensure Restaurant Order Types exist (Dine In, Take Away, Delivery)
3. Create Restaurant Tables for testing

### Test Scenarios

#### Scenario 1: Dine In Order
1. Open POS
2. Try adding item without Order Type → Should show error
3. Select "Dine In" Order Type
4. Try adding item without table → Should show error
5. Select available table
6. Add items to cart
7. Click "Make Order" → Should create restaurant order
8. Click "Show Orders" → Should see the created order
9. Select order and convert to payment

#### Scenario 2: Take Away Order
1. Select "Take Away" Order Type
2. Add items (no table required)
3. Click "Make Order"
4. Verify order creation

#### Scenario 3: Order Management
1. Create multiple orders with different types
2. Use "Show Orders" to view all orders
3. Filter by order type and status
4. Edit draft orders
5. Convert submitted orders to payment
6. Cancel unwanted orders

## Configuration

### POS Profile Settings
- `posa_enable_restaurant_mode` - Enable/disable restaurant features

### Restaurant Order Types
- Create order types with appropriate settings
- Set `requires_table` for Dine In orders
- Configure default preparation times

### Restaurant Tables
- Create tables with unique table numbers
- Set capacity and location information
- Tables automatically managed (Available/Occupied)

## Troubleshooting

### Common Issues

1. **Order Type not showing**
   - Ensure Restaurant Order Types are created and enabled
   - Check POS Profile has restaurant mode enabled

2. **Table selection not appearing**
   - Verify Order Type has `requires_table` checked
   - Ensure Restaurant Tables exist and are enabled

3. **Orders not appearing in Show Orders**
   - Check orders have `restaurant_order_type` field set
   - Verify POS Opening Shift is active

4. **Cannot add items**
   - Ensure Order Type is selected first
   - For Dine In, ensure table is selected

### Debug Information

Enable console logging to see:
- Order type and table selection events
- Item addition validation results
- Restaurant order creation responses
- Order loading and conversion processes

## Future Enhancements

Potential improvements:
1. Order status tracking (Preparing, Ready, Served)
2. Kitchen display integration
3. Order timing and preparation tracking
4. Table layout visualization
5. Order modification after creation
6. Split billing for tables
7. Order merging capabilities

## Conclusion

The restaurant features provide a complete ordering workflow that integrates seamlessly with the existing POS system. The implementation ensures proper validation, user experience, and data integrity while maintaining compatibility with existing POS functionality.