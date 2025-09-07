# KOT Print Width Configuration

This enhancement allows you to configure the print width for Kitchen Order Tickets (KOT) in your restaurant POS system.

## Features

### Configurable Print Widths
- **58mm**: Standard thermal printer width (default)
- **80mm**: Wide thermal printer width with better readability

### Smart Formatting
- **58mm Format**: Compact layout optimized for small thermal printers
  - Font size: 10px
  - Padding: 5px
  - Line height: 1.2
  
- **80mm Format**: Expanded layout with better readability
  - Font size: 12px
  - Padding: 8px
  - Line height: 1.3
  - Larger titles and better spacing

## How to Configure

### 1. Enable Restaurant Mode
1. Go to **POS Profile** in your ERPNext/POS Awesome setup
2. Enable **"Enable Restaurant Mode"** checkbox
3. Enable **"Auto Print KOT"** if you want automatic printing

### 2. Set KOT Print Width
1. In the same POS Profile, find the **"KOT Print Width"** field
2. Select either:
   - **58mm** - for standard thermal printers
   - **80mm** - for wide thermal printers
3. Save the POS Profile

### 3. Test the Configuration
1. Create a new restaurant order
2. The KOT will automatically use the configured print width
3. For manual reprinting, use the "Reprint KOT" option

## Technical Implementation

### Frontend Changes
- Updated `kot_print.js` plugin to support dynamic width configuration
- Added responsive CSS for both 58mm and 80mm formats
- Improved font sizing and layout scaling

### Backend Changes
- Modified `generate_kot_print()` function to read print width from POS Profile
- Added `posa_kot_print_width` custom field to POS Profile
- Updated void KOT functionality to respect print width settings

### Database Changes
- New custom field: `posa_kot_print_width` in POS Profile
- Options: "58mm" (default) or "80mm"
- Depends on restaurant mode being enabled

## Benefits

1. **Printer Compatibility**: Support for both standard and wide thermal printers
2. **Better Readability**: 80mm format provides more space for item names and details
3. **Flexible Configuration**: Easy to switch between formats per POS Profile
4. **Backward Compatibility**: Existing setups continue to work with 58mm default

## Usage Examples

### For 58mm Printers (Default)
```
KITCHEN ORDER TICKET
KOT-20240907-143022
2024-09-07 14:30:22

Type: Dine In
Table: T-001
Customer: John Doe

Item                  Qty
-----------------------
Margherita Pizza        2
Coca Cola               1
-----------------------
Total Items: 3
```

### For 80mm Printers
```
        KITCHEN ORDER TICKET
        KOT-20240907-143022
        2024-09-07 14:30:22

Type: Dine In
Table: T-001  
Customer: John Doe

Item                           Qty
------------------------------------
Margherita Pizza Large           2
Coca Cola 500ml                  1
------------------------------------
Total Items: 3

Special Notes: Extra cheese
```

## Installation

The feature is automatically available after updating POS Awesome. Run the database migration to add the new field:

```bash
bench --site your-site migrate
```

## Troubleshooting

1. **Field not visible**: Ensure "Enable Restaurant Mode" is checked first
2. **Print width not applied**: Verify the POS Profile is saved and restart the POS session
3. **Layout issues**: Clear browser cache after updating

---

For more information, visit the [POS Awesome documentation](https://github.com/codfatherlogic/POS-Awesome-Resto/wiki).
