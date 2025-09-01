# KOT (Kitchen Order Ticket) Print Feature

## Overview
The KOT Print feature allows printing kitchen order tickets before finalizing orders. This is essential for restaurant workflows where the kitchen needs to start food preparation before payment is processed.

## Features Implemented

### 1. Manual KOT Print Button
- **Location**: Appears in restaurant mode when items are added to cart
- **Icon**: 🍳 Print KOT (with silverware icon)
- **Color**: Orange gradient for visibility
- **Behavior**: Prints KOT without creating Sales Order

### 2. Auto KOT Print on Make Order
- **Setting**: `posa_auto_print_kot` in POS Profile
- **Behavior**: Automatically prints KOT when "Make Order" is clicked
- **Fallback**: If auto-print fails, order creation still succeeds

### 3. KOT Template Design
- **Format**: Kitchen-focused, thermal printer compatible
- **Width**: 300px (thermal printer standard)
- **Content**: Order type, table number, items, quantities, notes
- **Excludes**: Prices, customer details, taxes (not needed in kitchen)

## Implementation Details

### Backend API Endpoints

#### 1. `generate_kot_print(order_data)`
- **Purpose**: Generate KOT data structure from order
- **Returns**: KOT data with order info, items, and metadata
- **Usage**: Called before order creation for manual print

#### 2. `generate_kot_html(order_data)`
- **Purpose**: Generate complete HTML for KOT printing
- **Returns**: Ready-to-print HTML with styling
- **Usage**: Called by frontend for manual KOT printing

#### 3. Enhanced `create_restaurant_order(order_data)`
- **New Feature**: Checks `posa_auto_print_kot` setting
- **Returns**: Either simple Sales Order or Sales Order + KOT data
- **Auto-print**: Includes KOT data when auto-print is enabled

### Frontend Components

#### 1. InvoiceSummary.vue
- **New Button**: "🍳 Print KOT" button
- **Visibility**: Restaurant mode + items exist + new order only
- **Styling**: Orange gradient with hover effects
- **Loading State**: `kotPrintLoading` for UX

#### 2. Invoice.vue
- **New Method**: `print_kot()` with validation
- **Integration**: Calls backend API and handles printing
- **Error Handling**: Validates order type, table, and items
- **Print Options**: Silent print or preview based on POS settings

#### 3. invoiceItemMethods.js
- **Enhanced**: `create_restaurant_order()` callback
- **Auto-print**: Handles new response format with KOT data
- **Dynamic Import**: Loads KOT print functions when needed
- **Fallback**: Graceful degradation if auto-print fails

### KOT Print Module (kot_print.js)

#### Functions:
- `generateKOTHTML(kotData)` - Generate HTML from KOT data
- `printKOTSilent(kotData)` - Silent print with auto-close
- `printKOTWithPreview(kotData)` - Print with user preview
- `printKOTHTML(kotHTML, silentPrint)` - Direct HTML printing

## Usage Workflow

### Manual KOT Print
1. **Select Order Type** (Dine In/Take Away/Delivery)
2. **Select Table** (if Dine In)
3. **Add Items** to cart
4. **Click "🍳 Print KOT"** → Prints kitchen ticket
5. **Click "Make Order"** → Creates Sales Order
6. **Use "Show Orders"** → Convert to payment later

### Auto KOT Print
1. **Enable Setting**: Check "Auto Print KOT on Make Order" in POS Profile
2. **Select Order Type & Table**
3. **Add Items** to cart
4. **Click "Make Order"** → Creates order AND prints KOT automatically

## KOT Template Structure

```
=================================
    🍳 KITCHEN ORDER TICKET
=================================
KOT #: KOT-20250831-132456

Order Type: Dine In
Table: T01
Customer: John Doe
Date & Time: 2025-08-31 13:24:56

---------------------------------
ITEM                        QTY
---------------------------------
Biriyani                  1 Nos
Chick Tikka Masala        1 Nos
Sample D                  2 Nos

---------------------------------
Total Items: 4

Special Notes:
Extra spicy, no onions

=================================
*** FOR KITCHEN USE ONLY ***
Please prepare items as ordered
Printed on: 8/31/2025, 1:24:56 PM
```

## Configuration

### POS Profile Settings
- **Enable Restaurant Mode**: `posa_enable_restaurant_mode` = 1
- **Auto Print KOT**: `posa_auto_print_kot` = 1 (optional)
- **Silent Print**: `posa_silent_print` = 1 (optional)

### Print Settings
- **Format**: Custom KOT HTML template
- **Size**: 300px width (thermal printer compatible)
- **Auto-print**: Configurable per POS Profile
- **Preview**: Available when silent print is disabled

## Benefits

### For Kitchen Staff
- ✅ Immediate order visibility
- ✅ No pricing distractions
- ✅ Clear item quantities
- ✅ Special instructions visible
- ✅ Order timing information

### For Front Staff
- ✅ Flexible printing control
- ✅ Order review before KOT
- ✅ Error prevention
- ✅ Workflow efficiency
- ✅ Customer service improvement

### For Management
- ✅ Better order tracking
- ✅ Kitchen efficiency
- ✅ Reduced errors
- ✅ Audit trail
- ✅ Configurable automation

## Testing Steps

### Manual KOT Print Test
1. Open POS in restaurant mode
2. Select "Dine In" order type
3. Select available table
4. Add items (Biriyani, Chick Tikka Masala)
5. Verify "🍳 Print KOT" button appears
6. Click button → Should open KOT print window
7. Verify KOT contains: order type, table, items, quantities
8. Print or close KOT window
9. Click "Make Order" → Should create Sales Order

### Auto KOT Print Test
1. Go to POS Profile → Enable "Auto Print KOT on Make Order"
2. Open POS in restaurant mode
3. Select order type and table
4. Add items to cart
5. Click "Make Order" → Should print KOT AND create order
6. Verify both KOT printed and order created
7. Check "Show Orders" for created order

## Error Handling

### Validation Checks
- ✅ Order type must be selected
- ✅ Table required for Dine In orders
- ✅ Items must exist in cart
- ✅ KOT generation error handling
- ✅ Print failure graceful degradation

### Error Messages
- "Please select an Order Type"
- "Please select a table for Dine In orders"
- "Please add items to print KOT"
- "Failed to print KOT: [error details]"

## Technical Notes

### Print Compatibility
- **Thermal Printers**: 300px width optimized
- **Regular Printers**: Responsive design
- **Browser Print**: Standard print dialog
- **Silent Print**: Direct printing without dialog

### Performance
- **Lazy Loading**: KOT print module loaded on demand
- **Error Isolation**: KOT failures don't break order creation
- **Memory Efficient**: Auto-close print windows
- **Fast Generation**: Minimal backend processing

## Future Enhancements

### Possible Improvements
1. **KOT Status Tracking** - Mark items as prepared
2. **Kitchen Display** - Digital kitchen screens
3. **Print Queue** - Multiple KOT printers
4. **Customizable Templates** - Different KOT formats
5. **Preparation Times** - Estimated cooking times
6. **Order Modifications** - Update KOTs for changes

This KOT implementation provides a complete kitchen order workflow that integrates seamlessly with the existing restaurant order system while maintaining flexibility and user control.
