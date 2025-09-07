# Fix for "Value too big" Error in Restaurant Orders

## Issue Description
When filtering restaurant orders by "Submitted" status, the system was throwing an error:
```
Error Log thscuvk1d4: 'Title' (Final filters before query: {'restaurant_order_type': ['is', 'set'], 'docstatus': 1, 'per_billed': ['<', 100], 'transaction_date': datetime.date(2025, 9, 7)}) will get truncated, as max characters allowed is 140
```

## Root Cause
The error was caused by verbose debug logging in the `get_restaurant_orders()` function. The log messages were too long, especially when logging the entire filters dictionary which contains complex filter expressions.

## Fix Applied
Removed or shortened the problematic debug logs in `/posawesome/posawesome/api/restaurant_orders.py`:

### Before (Problematic)
```python
# Debug logging
frappe.log_error(f"Restaurant Orders API called with: pos_opening_shift={pos_opening_shift}, order_type={order_type}, status={status}, date_filter={date_filter}", "Restaurant Orders Debug")
frappe.log_error(f"Initial filters: {filters}", "Restaurant Orders Debug")
...
frappe.log_error(f"Date filter parsed: {date_filter} -> {parsed_date}", "Restaurant Orders Debug")
frappe.log_error(f"Failed to parse date filter: {date_filter}", "Restaurant Orders Debug")
frappe.log_error(f"Final filters before query: {filters}", "Restaurant Orders Debug")
frappe.log_error(f"Final filters: {filters}", "Restaurant Orders Debug")
```

### After (Fixed)
```python
# Debug logging (shortened to avoid length issues)
frappe.log_error(f"Restaurant Orders API called with status={status}, date={date_filter}", "Restaurant Orders API")
```

## Changes Made
1. **Removed verbose filter logging**: Eliminated logs that tried to print the entire filters dictionary
2. **Shortened API call logging**: Kept only essential information (status and date)
3. **Removed duplicate logs**: Eliminated redundant logging statements
4. **Preserved error handling**: Kept important error logs for actual failures

## Impact
- ✅ Fixed "Value too big" error when filtering by Submitted status
- ✅ Maintained essential debugging capability
- ✅ Improved system performance by reducing log volume
- ✅ No functional impact on restaurant order filtering

## Test Cases
The fix resolves the error in these scenarios:
- Filtering orders by "Submitted" status
- Filtering orders by any status with date filters
- Any API call that previously triggered verbose logging

## Files Modified
- `/posawesome/posawesome/api/restaurant_orders.py` - Shortened debug logging in `get_restaurant_orders()` function

## Related Issues
This fix ensures that restaurant order management remains functional when filtering by different statuses, particularly when dealing with submitted orders that have complex filter criteria.
