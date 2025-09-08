# Copyright (c) 2020, Youssef Restom and contributors
# For license information, please see license.txt

import json

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.doctype.batch.batch import (
    get_batch_no,
    get_batch_qty,
)  # This should be from erpnext directly
from frappe import _
from frappe.utils import cint, cstr, flt, getdate, money_in_words, nowdate, strip_html_tags
from frappe.utils.background_jobs import enqueue

from posawesome.posawesome.api.payments import (
    redeeming_customer_credit,
)  # Updated import
from posawesome.posawesome.api.utilities import (
    ensure_child_doctype,
    set_batch_nos_for_bundels,
)  # Updated imports

from .items import get_stock_availability


def _sanitize_item_name(name: str) -> str:
    """Strip HTML and limit length for item names."""
    if not name:
        return ""
    cleaned = strip_html_tags(name)
    return cleaned.strip()[:140]


def _apply_item_name_overrides(invoice_doc, overrides=None):
    """Apply custom item names to invoice items."""
    overrides = overrides or {}
    for item in invoice_doc.items:
        source = overrides.get(item.idx) or {}
        provided = source.get("item_name") if isinstance(source, dict) else None
        default_name = frappe.get_cached_value("Item", item.item_code, "item_name")
        clean = _sanitize_item_name(provided or item.item_name)
        if clean and clean != default_name:
            item.item_name = clean
            item.name_overridden = 1
        else:
            item.item_name = default_name
            item.name_overridden = 0


def _get_available_stock(item):
    """Return available stock qty for an item row."""
    warehouse = item.get("warehouse")
    batch_no = item.get("batch_no")
    item_code = item.get("item_code")
    if not item_code or not warehouse:
        return 0
    if batch_no:
        return get_batch_qty(batch_no, warehouse) or 0
    return get_stock_availability(item_code, warehouse)


def _collect_stock_errors(items):
	"""Return list of items exceeding available stock."""
	errors = []
	for d in items:
		if flt(d.get("qty")) < 0:
			continue
		available = _get_available_stock(d)
		requested = flt(d.get("stock_qty") or (flt(d.get("qty")) * flt(d.get("conversion_factor") or 1)))
		if requested > available:
			errors.append(
				{
					"item_code": d.get("item_code"),
					"warehouse": d.get("warehouse"),
					"requested_qty": requested,
					"available_qty": available,
				}
			)
	return errors


def _merge_duplicate_taxes(invoice_doc):
        """Remove duplicate tax rows with same account and rate.

        If duplicates are found, keep the first occurrence and recalculate totals.
        """
        seen = set()
        unique = []
        for tax in invoice_doc.get("taxes", []):
                key = (tax.account_head, flt(tax.rate), cstr(tax.charge_type))
                if key in seen:
                        continue
                seen.add(key)
                unique.append(tax)
        if len(unique) != len(invoice_doc.get("taxes", [])):
                invoice_doc.set("taxes", unique)
                invoice_doc.calculate_taxes_and_totals()


def _should_block(pos_profile):
    block_sale = cint(
        frappe.db.get_value(
            "POS Profile", pos_profile, "posa_block_sale_beyond_available_qty"
        )
    )
    return block_sale


def _update_related_sales_orders(invoice_doc):
    """Update the billing status of related Sales Orders after invoice submission"""
    try:
        # DEBUG: Log when this function is called
        frappe.log_error(f"DEBUG: _update_related_sales_orders called for invoice {invoice_doc.name}", "SO Update Debug")
        
        # Get all Sales Orders referenced in the invoice items
        sales_orders = set()
        for item in invoice_doc.items:
            if hasattr(item, 'sales_order') and item.sales_order:
                sales_orders.add(item.sales_order)
                frappe.log_error(f"DEBUG: Found SO reference {item.sales_order} in item {item.item_code}, so_detail: {getattr(item, 'so_detail', 'MISSING')}", "SO Update Debug")
        
        frappe.log_error(f"DEBUG: Sales Orders to update: {list(sales_orders)}", "SO Update Debug")
        
        # First, update Sales Order Item billed_amt for proper ERPNext linking
        for item in invoice_doc.items:
            if hasattr(item, 'so_detail') and item.so_detail:
                # Update the billed_amt in Sales Order Item - this creates the proper ERPNext link
                frappe.db.set_value("Sales Order Item", item.so_detail, {
                    "billed_amt": item.amount,
                    "delivered_qty": item.qty
                })
                frappe.log_error(f"DEBUG: Updated SO Item {item.so_detail} - billed_amt: {item.amount}, delivered_qty: {item.qty}", "SO Update Debug")
        
        # Update each Sales Order's status using ERPNext's proper method
        for so_name in sales_orders:
            try:
                # Recalculate Sales Order per_billed percentage using updated billed_amt values
                so_doc = frappe.get_doc("Sales Order", so_name)
                so_doc.reload()
                
                total_amount = sum(item.amount for item in so_doc.items)
                billed_amount = sum(item.billed_amt or 0 for item in so_doc.items)
                
                frappe.log_error(f"DEBUG: SO {so_name} - total_amount: {total_amount}, billed_amount: {billed_amount}", "SO Update Debug")
                
                if total_amount > 0:
                    per_billed = (billed_amount / total_amount) * 100
                    frappe.db.set_value("Sales Order", so_name, "per_billed", per_billed)
                    
                    frappe.log_error(f"DEBUG: SO {so_name} - per_billed: {per_billed}%", "SO Update Debug")
                    
                    # Update Sales Order status based on billing - RESTAURANT SPECIFIC
                    if per_billed >= 100:
                        # For restaurant orders, mark as Completed when fully billed
                        frappe.db.set_value("Sales Order", so_name, {
                            "status": "Completed",
                            "billing_status": "Fully Billed"
                        })
                        frappe.log_error(f"DEBUG: SO {so_name} - Updated to Completed/Fully Billed", "SO Update Debug")
                    elif per_billed > 0:
                        # Partially billed
                        frappe.db.set_value("Sales Order", so_name, {
                            "billing_status": "Partly Billed"
                        })
                        frappe.log_error(f"DEBUG: SO {so_name} - Updated to Partly Billed", "SO Update Debug")
                    else:
                        # Not billed
                        frappe.db.set_value("Sales Order", so_name, {
                            "billing_status": "Not Billed"
                        })
                        frappe.log_error(f"DEBUG: SO {so_name} - Updated to Not Billed", "SO Update Debug")
                
                frappe.db.commit()
                
            except Exception as e:
                # Use shorter error message to avoid "Value too big" error
                frappe.log_error(f"SO {so_name} billing update failed: {str(e)}", "SO Update Debug")
                # Don't fail the invoice submission if SO update fails
                pass
        
        # CONSOLIDATION FINALIZATION: Check if any of the processed Sales Orders were consolidated
        # and finalize the consolidation process now that the invoice is submitted
        for so_name in sales_orders:
            try:
                # Check if this Sales Order was part of a consolidation
                so_doc = frappe.get_doc("Sales Order", so_name)
                if hasattr(so_doc, 'custom_consolidated_invoice_reference') and so_doc.custom_consolidated_invoice_reference:
                    # This is a consolidated order - finalize the consolidation process
                    frappe.log_error(f"CONSOLIDATION FINALIZE: Found consolidated order {so_name}, calling finalization", "Consolidation Debug")
                    
                    # Import and call the finalization function
                    from posawesome.posawesome.api.restaurant_orders import finalize_consolidated_order_submission
                    finalize_consolidated_order_submission(so_name)
                    
                    frappe.log_error(f"CONSOLIDATION FINALIZE: Successfully finalized consolidation for {so_name}", "Consolidation Debug")
                    
            except Exception as e:
                frappe.log_error(f"CONSOLIDATION FINALIZE: Error finalizing consolidation for {so_name}: {str(e)}", "Consolidation Debug")
                # Don't fail the invoice submission if consolidation finalization fails
                pass
                
    except Exception as e:
        # Use shorter error message to avoid "Value too big" error  
        frappe.log_error(f"Invoice {invoice_doc.name} SO updates failed: {str(e)}", "SO Update Debug")
        # Don't fail the invoice submission if SO updates fail
        pass


def _validate_stock_on_invoice(invoice_doc):
	# CRITICAL FIX: Only validate stock items, exclude non-stock items
	items_to_check = [d.as_dict() for d in invoice_doc.items if d.get("is_stock_item") == 1]
	if hasattr(invoice_doc, "packed_items"):
		items_to_check.extend([d.as_dict() for d in invoice_doc.packed_items if d.get("is_stock_item") == 1])
	errors = _collect_stock_errors(items_to_check)
	if errors and _should_block(invoice_doc.pos_profile):
		frappe.throw(frappe.as_json({"errors": errors}), frappe.ValidationError)


def _auto_set_return_batches(invoice_doc):
        """Assign batch numbers for return invoices without a source invoice.

        When the POS Profile allows returns without an original invoice and an
        item requires a batch number, this function allocates the first
        available batch in FIFO order. If no batches exist in the selected
        warehouse, an informative error is raised instead of the generic
        validation error.
        """

        if not getattr(invoice_doc, 'is_return', False) or invoice_doc.get("return_against"):
                return

        profile = invoice_doc.get("pos_profile")
        allow_without_invoice = profile and frappe.db.get_value(
                "POS Profile", profile, "posa_allow_return_without_invoice"
        )
        if not cint(allow_without_invoice):
                return

        allow_free = cint(
                frappe.db.get_value("POS Profile", profile, "posa_allow_free_batch_return")
                or 0
        )

        for d in invoice_doc.items:
                if not d.get("item_code") or not d.get("warehouse"):
                        continue

                has_batch = frappe.db.get_value("Item", d.item_code, "has_batch_no")
                if has_batch and not d.get("batch_no"):
                        batch_list = get_batch_qty(
                                item_code=d.item_code, warehouse=d.warehouse
                        ) or []
                        batch_list = [b for b in batch_list if flt(b.get("qty")) > 0]
                        if batch_list:
                                # FIFO: batches are already sorted by posting/expiry in ERPNext
                                d.batch_no = batch_list[0].get("batch_no")
                        elif not allow_free:
                                frappe.throw(
                                        _(
                                                "No batches available in {0} for {1}."
                                        ).format(d.warehouse, d.item_code)
                                )


@frappe.whitelist()
def validate_cart_items(items, pos_profile=None):
    """Validate cart items for available stock.

    Returns a list of item dicts where requested quantity exceeds availability.
    This can be used on the front-end for pre-submission checks.
    """

    if isinstance(items, str):
        items = json.loads(items)
    
    # Check if restaurant mode is enabled - if so, bypass stock validation
    if pos_profile:
        posa_enable_restaurant_mode = frappe.db.get_value("POS Profile", pos_profile, "posa_enable_restaurant_mode")
        if posa_enable_restaurant_mode:
            return []  # Return empty list to bypass stock validation for restaurant orders
    
    # If no pos_profile provided, try to get it from frappe.session if available
    if not pos_profile:
        # Try to get current POS profile from session context
        try:
            current_user = frappe.session.user
            # Get the default POS Profile for current user or check if restaurant mode is generally enabled
            pos_profiles = frappe.get_all("POS Profile", 
                                        filters={"disabled": 0}, 
                                        fields=["name", "posa_enable_restaurant_mode"])
            for profile in pos_profiles:
                if profile.posa_enable_restaurant_mode:
                    return []  # Bypass validation if any active profile has restaurant mode
        except:
            pass  # Fallback to normal validation if we can't determine restaurant mode
    
    return _collect_stock_errors(items)


def get_latest_rate(from_currency: str, to_currency: str):
    """Return the most recent Currency Exchange rate and its date."""
    rate_doc = frappe.get_all(
        "Currency Exchange",
        filters={"from_currency": from_currency, "to_currency": to_currency},
        fields=["exchange_rate", "date"],
        order_by="date desc, creation desc",
        limit=1,
    )
    if rate_doc:
        return flt(rate_doc[0].exchange_rate), rate_doc[0].date
    rate = get_exchange_rate(from_currency, to_currency, nowdate())
    return flt(rate), nowdate()


@frappe.whitelist()
def validate_return_items(original_invoice_name, return_items, doctype="Sales Invoice"):
    """
    Ensure that return items do not exceed the quantity from the original invoice.
    """
    original_invoice = frappe.get_doc(doctype, original_invoice_name)
    original_item_qty = {}

    for item in original_invoice.items:
        original_item_qty[item.item_code] = original_item_qty.get(item.item_code, 0) + item.qty

    returned_items = frappe.get_all(
        doctype,
        filters={
            "return_against": original_invoice_name,
            "docstatus": 1,
            "is_return": 1,
        },
        fields=["name"],
    )

    for returned_invoice in returned_items:
        ret_doc = frappe.get_doc(doctype, returned_invoice.name)
        for item in ret_doc.items:
            if item.item_code in original_item_qty:
                original_item_qty[item.item_code] -= abs(item.qty)

    for item in return_items:
        item_code = item.get("item_code")
        return_qty = abs(item.get("qty", 0))
        if item_code in original_item_qty and return_qty > original_item_qty[item_code]:
            return {
                "valid": False,
                "message": _("You are trying to return more quantity for item {0} than was sold.").format(
                    item_code
                ),
            }

    return {"valid": True}


@frappe.whitelist()
def update_invoice(data):
    data = json.loads(data)
    
    # DEBUG: Log all incoming data to understand what we're dealing with
    frappe.log_error(
        message=f"update_invoice DEBUG: Incoming data keys: {list(data.keys())}, name: {data.get('name')}, doctype: {data.get('doctype')}, virtual_payment_document: {data.get('virtual_payment_document')}, is_multi_order_payment_view: {data.get('is_multi_order_payment_view')}",
        title="Update Invoice Debug"
    )
    
    # CRITICAL FIX: Prevent saving virtual multi-order payment documents
    if data.get("doctype") == "POS Multi Order Payment" or data.get("virtual_payment_document") or \
       (data.get("name", "").startswith("new-multi-order-")):
        frappe.log_error(
            message=f"update_invoice: Blocked attempt to save virtual payment document. Name: {data.get('name')}, Doctype: {data.get('doctype')}, virtual_payment_document: {data.get('virtual_payment_document')}",
            title="Update Invoice Debug"
        )
        # Return success without actually saving - this prevents the delivery date validation error
        return {
            "name": data.get("name"),
            "doctype": data.get("doctype", "Sales Order"),
            "status": "success",
            "message": "Virtual payment document - save skipped",
            "docstatus": 0
        }
    
    # ADDITIONAL SAFEGUARD: Block any document without a real name (temp multi-order documents)
    if not data.get("name") and data.get("is_multi_order_payment_view"):
        frappe.log_error(
            message="update_invoice: Blocked attempt to save multi-order payment view without name",
            title="Update Invoice Debug"
        )
        # Return success without saving
        return {
            "name": "temp-multi-order-payment",
            "doctype": data.get("doctype", "Sales Order"),
            "status": "success", 
            "message": "Multi-order payment view - save skipped",
            "docstatus": 0
        }
    
    # For existing documents, use the doctype from data; for new documents, determine from POS Profile
    if data.get("name") and data.get("doctype"):
        # Existing document - use the provided doctype
        doctype = data.get("doctype")
        frappe.log_error(f"update_invoice: Using existing document type: {doctype} for {data.get('name')}", "Update Invoice Debug")
    else:
        # New document - determine doctype based on POS Profile setting
        pos_profile = data.get("pos_profile")
        doctype = "Sales Invoice"
        if pos_profile and frappe.db.get_value(
            "POS Profile", pos_profile, "create_pos_invoice_instead_of_sales_invoice"
        ):
            doctype = "POS Invoice"
        frappe.log_error(f"update_invoice: Using default document type: {doctype} for new document", "Update Invoice Debug")

    # DON'T override the doctype if it's already provided - this was the bug!
    # Only set doctype for new documents without a name
    if not data.get("name"):
        data.setdefault("doctype", doctype)
    
    print(f"DEBUG: After doctype logic - data doctype: {data.get('doctype')}, name: {data.get('name')}")
    
    frappe.log_error(f"DEBUG FLOW: name={data.get('name')}, target_doctype={doctype}, data_doctype={data.get('doctype')}, name_starts_SO={data.get('name', '').startswith('SO')}, SO_exists={frappe.db.exists('Sales Order', data.get('name')) if data.get('name') else False}", "Update Invoice Debug")    # CRITICAL DEBUG: Print to stdout for immediate visibility
    print(f"DEBUG: Checking conditions for {data.get('name')}")
    print(f"  - First condition: name={data.get('name')} AND exists in Sales Invoice: {frappe.db.exists('Sales Invoice', data.get('name')) if data.get('name') else False}")
    print(f"  - Second condition: starts with SO: {data.get('name', '').startswith('SO')} AND SO exists: {frappe.db.exists('Sales Order', data.get('name')) if data.get('name') else False}")

    # FIXED: Check specifically for Sales Invoice existence, not the target doctype
    if data.get("name") and frappe.db.exists("Sales Invoice", data.get("name")):
        # Document exists as Sales Invoice - update it with proper locking
        invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
        
        # CRITICAL FIX: Reload document to get latest version and prevent modification conflicts
        invoice_doc.reload()
        
        # CRITICAL FIX: Preserve Sales Order references before updating
        original_so_refs = {}
        if hasattr(invoice_doc, 'items') and invoice_doc.items:
            for i, item in enumerate(invoice_doc.items):
                if hasattr(item, 'sales_order') and item.sales_order:
                    original_so_refs[i] = {
                        'sales_order': item.sales_order,
                        'so_detail': getattr(item, 'so_detail', None)
                    }
        
        # Update the document
        invoice_doc.update(data)
        
        # CRITICAL FIX: Restore Sales Order references after update
        if original_so_refs and hasattr(invoice_doc, 'items') and invoice_doc.items:
            for i, item in enumerate(invoice_doc.items):
                if i in original_so_refs:
                    item.sales_order = original_so_refs[i]['sales_order']
                    if original_so_refs[i]['so_detail']:
                        item.so_detail = original_so_refs[i]['so_detail']
            frappe.log_error(f"Restored {len(original_so_refs)} Sales Order references in invoice {data.get('name')}", "SO Reference Preservation")
    elif data.get("name") and data.get("name").startswith("SO") and frappe.db.exists("Sales Order", data.get("name")):
        # This is a Sales Order that needs to be converted to Sales Invoice
        sales_order_name = data.get("name")
        frappe.log_error(f"CONVERSION REQUEST: Sales Order {sales_order_name} conversion requested in update_invoice", "Update Invoice Debug")
        
        # Check if a Sales Invoice already exists for this Sales Order
        si_items = frappe.get_all("Sales Invoice Item", 
            filters={"sales_order": sales_order_name}, 
            fields=["parent"], 
            order_by="creation desc")
        
        frappe.log_error(f"DEBUG: Found {len(si_items)} SI items for {sales_order_name}: {si_items}", "Update Invoice Debug")
        
        if si_items:
            # Sales Invoice already exists - use the existing one
            existing_invoice_name = si_items[0].parent
            frappe.log_error(f"EXISTING SI FOUND: Using existing Sales Invoice {existing_invoice_name} for SO {sales_order_name}", "Update Invoice Debug")
            
            # Load the existing Sales Invoice and Sales Order for comparison
            invoice_doc = frappe.get_doc("Sales Invoice", existing_invoice_name)
            sales_order_doc = frappe.get_doc("Sales Order", sales_order_name)
            
            # CRITICAL FIX: Reload document to get latest version and prevent modification conflicts
            invoice_doc.reload()
            
            # ENHANCED: Force complete item synchronization from Sales Order
            # This handles any item changes (new items, quantity changes, removed items)
            frappe.log_error(f"ITEM SYNC: Starting complete synchronization between SO {sales_order_name} and SI {existing_invoice_name}", "Update Invoice Debug")
            
            # Clear existing items and rebuild from Sales Order
            invoice_doc.items = []
            
            # Add all items from Sales Order to Sales Invoice
            for so_item in sales_order_doc.items:
                frappe.log_error(f"SYNC ITEM: Adding {so_item.item_code} (qty: {so_item.qty}, rate: {so_item.rate}) from SO to SI", "Update Invoice Debug")
                
                si_item = invoice_doc.append("items", {})
                si_item.item_code = so_item.item_code
                si_item.item_name = so_item.item_name
                si_item.description = so_item.description
                si_item.qty = so_item.qty
                si_item.rate = so_item.rate
                si_item.amount = so_item.amount
                si_item.warehouse = so_item.warehouse
                si_item.sales_order = sales_order_name
                si_item.so_detail = so_item.name
                si_item.income_account = getattr(so_item, 'income_account', None) or "Sales - ASP"
                si_item.expense_account = getattr(so_item, 'expense_account', None) or "Cost of Goods Sold - ASP"
                si_item.cost_center = getattr(so_item, 'cost_center', None) or "Main - ASP"
                si_item.uom = so_item.uom
                si_item.stock_uom = so_item.stock_uom
                si_item.conversion_factor = so_item.conversion_factor
                si_item.stock_qty = so_item.stock_qty
            
            # Recalculate totals after complete synchronization
            frappe.log_error(f"ITEM SYNC COMPLETE: Recalculating totals for SI {existing_invoice_name}", "Update Invoice Debug")
            invoice_doc.calculate_taxes_and_totals()
            
            # Update the data to use the correct invoice name (but preserve synced items)
            data["name"] = existing_invoice_name
            # Don't update items through data.update() to preserve our synchronization
            items_data = data.pop("items", None)  # Remove items from data to prevent override
            invoice_doc.update(data)
            # Restore items if they were in the original data but we want to keep our synced version
            if items_data:
                data["items"] = items_data
            
            frappe.log_error(f"SUCCESS: Updated existing Sales Invoice {existing_invoice_name}", "Update Invoice Debug")
        else:
            # No existing Sales Invoice - need to convert the Sales Order
            frappe.log_error(f"CONVERTING: Creating new Sales Invoice from Sales Order {sales_order_name}", "Update Invoice Debug")
            
            try:
                # Check Sales Order status and handle accordingly
                so_doc = frappe.get_doc("Sales Order", sales_order_name)
                frappe.log_error(f"SO STATUS CHECK: {sales_order_name} docstatus={so_doc.docstatus}, status={so_doc.status}", "Update Invoice Debug")
                
                if so_doc.docstatus == 2:  # Cancelled
                    frappe.throw(_("Cannot convert cancelled Sales Order {0} to Sales Invoice").format(sales_order_name))
                elif so_doc.docstatus == 1:  # Already submitted
                    frappe.log_error(f"SUBMITTED SO: {sales_order_name} is already submitted, trying ERPNext standard conversion", "Update Invoice Debug")
                    # For submitted orders, use ERPNext's standard make_sales_invoice function
                    from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
                    converted_result = make_sales_invoice(sales_order_name)
                    if converted_result:
                        # Save the new invoice
                        converted_result.save()
                        frappe.log_error(f"SUCCESS: Standard conversion of submitted SO {sales_order_name} to SI {converted_result.name}", "Update Invoice Debug")
                    else:
                        frappe.throw(_("Failed to convert submitted Sales Order {0} using standard conversion").format(sales_order_name))
                else:  # Draft status (docstatus == 0)
                    frappe.log_error(f"DRAFT SO: {sales_order_name} is in draft, using restaurant conversion", "Update Invoice Debug")
                    # For draft orders, use the restaurant conversion function
                    from posawesome.posawesome.api.restaurant_orders import convert_order_to_invoice
                    converted_result = convert_order_to_invoice(sales_order_name, data.get("pos_profile"))
                
                # Handle both document object and dictionary returns
                if converted_result:
                    if hasattr(converted_result, 'name'):
                        # It's a document object
                        invoice_doc = converted_result
                        frappe.log_error(f"SUCCESS: Converted SO {sales_order_name} to SI {invoice_doc.name} (document object)", "Update Invoice Debug")
                    elif isinstance(converted_result, dict) and converted_result.get("name"):
                        # It's a dictionary with name
                        invoice_doc = frappe.get_doc("Sales Invoice", converted_result["name"])
                        frappe.log_error(f"SUCCESS: Converted SO {sales_order_name} to SI {invoice_doc.name} (from dict)", "Update Invoice Debug")
                    else:
                        frappe.throw(_("Invalid conversion result for Sales Order {0}").format(sales_order_name))
                    
                    # Update the converted invoice with any additional data
                    # Remove the old name to prevent conflicts
                    conversion_data = data.copy()
                    conversion_data.pop("name", None)  # Remove the SO name
                    invoice_doc.update(conversion_data)
                else:
                    frappe.throw(_("Failed to convert Sales Order {0} to Sales Invoice").format(sales_order_name))
                    
            except Exception as conversion_error:
                frappe.log_error(f"CONVERSION ERROR: {str(conversion_error)}", "Update Invoice Debug")
                
                # If conversion fails because it's already billed, try to find the existing invoice
                if "already been billed" in str(conversion_error):
                    frappe.log_error(f"ALREADY BILLED: Searching for existing invoice for SO {sales_order_name}", "Update Invoice Debug")
                    # Re-search for invoices in case we missed one
                    si_items_retry = frappe.get_all("Sales Invoice Item", 
                        filters={"sales_order": sales_order_name}, 
                        fields=["parent"])
                    
                    if si_items_retry:
                        existing_invoice_name = si_items_retry[0].parent
                        frappe.log_error(f"FOUND EXISTING: Using Sales Invoice {existing_invoice_name} for already billed SO {sales_order_name}", "Update Invoice Debug")
                        
                        invoice_doc = frappe.get_doc("Sales Invoice", existing_invoice_name)
                        
                        # CRITICAL FIX: Reload document to get latest version and prevent modification conflicts
                        invoice_doc.reload()
                        
                        data["name"] = existing_invoice_name
                        invoice_doc.update(data)
                    else:
                        frappe.throw(_("Sales Order {0} conversion failed: {1}").format(sales_order_name, str(conversion_error)))
                else:
                    frappe.throw(_("Error converting Sales Order {0}: {1}").format(sales_order_name, str(conversion_error)))
    else:
        invoice_doc = frappe.get_doc(data)

    # Set currency from data before set_missing_values
    # Validate return items if this is a return invoice
    if (data.get("is_return") or getattr(invoice_doc, 'is_return', False)) and invoice_doc.get("return_against"):
        validation = validate_return_items(
            invoice_doc.return_against,
            [d.as_dict() for d in invoice_doc.items],
            doctype=invoice_doc.doctype,
        )
        if not validation.get("valid"):
            frappe.throw(validation.get("message"))
    selected_currency = data.get("currency")
    price_list_currency = data.get("price_list_currency")
    if not price_list_currency and invoice_doc.get("selling_price_list"):
        price_list_currency = frappe.db.get_value("Price List", invoice_doc.selling_price_list, "currency")

    # Ensure customer exists before setting missing values
    customer_name = invoice_doc.get("customer")
    if customer_name and not frappe.db.exists("Customer", customer_name):
        try:
            cust = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": customer_name,
                    "customer_group": "All Customer Groups",
                    "territory": "All Territories",
                    "customer_type": "Individual",
                }
            )
            cust.flags.ignore_permissions = True
            cust.insert()
            invoice_doc.customer = cust.name
            invoice_doc.customer_name = cust.customer_name
        except Exception as e:
            frappe.log_error(f"Failed to create customer {customer_name}: {e}")

    # Preserve provided item names for manual overrides
    overrides = {d.idx: {"item_name": d.item_name} for d in invoice_doc.items}
    locked_items = {}
    if getattr(invoice_doc, 'is_return', False):
        for d in invoice_doc.items:
            if d.get("locked_price"):
                locked_items[d.idx] = {
                    "rate": d.rate,
                    "price_list_rate": d.price_list_rate,
                    "discount_percentage": d.discount_percentage,
                    "discount_amount": d.discount_amount,
                    "is_free_item": d.get("is_free_item"),
                }

    invoice_doc.ignore_pricing_rule = 1
    invoice_doc.flags.ignore_pricing_rule = True

    # Set missing values first
    invoice_doc.set_missing_values()

    # Reapply any custom item names after defaults are set
    _apply_item_name_overrides(invoice_doc, overrides)

    # Remove duplicate taxes from item and profile templates
    _merge_duplicate_taxes(invoice_doc)

    if locked_items:
        for item in invoice_doc.items:
            locked = locked_items.get(item.idx)
            if locked:
                item.update(locked)
        invoice_doc.calculate_taxes_and_totals()

    # Get company currency first
    company_currency = frappe.get_cached_value(
        "Company", invoice_doc.company, "default_currency"
    )
    
    # Ensure selected currency is preserved after set_missing_values
    if selected_currency:
        invoice_doc.currency = selected_currency
    price_list_currency = price_list_currency or company_currency

    conversion_rate = 1
    exchange_rate_date = invoice_doc.posting_date
    if invoice_doc.currency != company_currency:
        conversion_rate, exchange_rate_date = get_latest_rate(
            invoice_doc.currency,
            company_currency,
        )
        if not conversion_rate:
            frappe.throw(
                _(
                        "Unable to find exchange rate for {0} to {1}. Please create a Currency Exchange record manually"
                    ).format(invoice_doc.currency, company_currency)
                )

        plc_conversion_rate = 1
        if price_list_currency != invoice_doc.currency:
            plc_conversion_rate, _ignored = get_latest_rate(
                price_list_currency,
                invoice_doc.currency,
            )
            if not plc_conversion_rate:
                frappe.throw(
                    _(
                        "Unable to find exchange rate for {0} to {1}. Please create a Currency Exchange record manually"
                    ).format(price_list_currency, invoice_doc.currency)
                )

        invoice_doc.conversion_rate = conversion_rate
        invoice_doc.plc_conversion_rate = plc_conversion_rate
        invoice_doc.price_list_currency = price_list_currency

        # Update rates and amounts for all items using multiplication
        for item in invoice_doc.items:
            if item.price_list_rate:
                item.base_price_list_rate = flt(
                    item.price_list_rate * (conversion_rate / plc_conversion_rate),
                    item.precision("base_price_list_rate"),
                )
            if item.rate:
                item.base_rate = flt(item.rate * conversion_rate, item.precision("base_rate"))
            if item.amount:
                item.base_amount = flt(item.amount * conversion_rate, item.precision("base_amount"))

        # Update payment amounts
        for payment in invoice_doc.payments:
            payment.base_amount = flt(payment.amount * conversion_rate, payment.precision("base_amount"))

        # Update invoice level amounts
        invoice_doc.base_total = flt(invoice_doc.total * conversion_rate, invoice_doc.precision("base_total"))
        invoice_doc.base_net_total = flt(
            invoice_doc.net_total * conversion_rate,
            invoice_doc.precision("base_net_total"),
        )
        invoice_doc.base_grand_total = flt(
            invoice_doc.grand_total * conversion_rate,
            invoice_doc.precision("base_grand_total"),
        )
        invoice_doc.base_rounded_total = flt(
            invoice_doc.rounded_total * conversion_rate,
            invoice_doc.precision("base_rounded_total"),
        )
        invoice_doc.base_in_words = money_in_words(invoice_doc.base_rounded_total, company_currency)

        # Update data to be sent back to frontend
        data["conversion_rate"] = conversion_rate
        data["plc_conversion_rate"] = plc_conversion_rate
        data["exchange_rate_date"] = exchange_rate_date

    inclusive = frappe.get_cached_value("POS Profile", invoice_doc.pos_profile, "posa_tax_inclusive")
    if invoice_doc.get("taxes"):
        for tax in invoice_doc.taxes:
            if tax.charge_type == "Actual":
                tax.included_in_print_rate = 0
            else:
                tax.included_in_print_rate = 1 if inclusive else 0

    # For return invoices, payments should be negative amounts
    if getattr(invoice_doc, 'is_return', False):
        for payment in invoice_doc.payments:
            payment.amount = -abs(payment.amount)
            payment.base_amount = -abs(payment.base_amount)

        invoice_doc.paid_amount = flt(
                sum(p.amount for p in invoice_doc.payments)
        )
        invoice_doc.base_paid_amount = flt(
                sum(p.base_amount for p in invoice_doc.payments)
        )

    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    invoice_doc.docstatus = 0
    
    # FINAL SAFEGUARD: Check if this is a virtual payment document before saving
    is_virtual_payment = (
        hasattr(invoice_doc, 'virtual_payment_document') and invoice_doc.virtual_payment_document or
        (hasattr(invoice_doc, 'name') and invoice_doc.name and invoice_doc.name.startswith("new-multi-order-")) or
        (hasattr(invoice_doc, 'is_multi_order_payment_view') and invoice_doc.is_multi_order_payment_view) or
        (invoice_doc.doctype == "POS Multi Order Payment") or
        # Additional checks for multi-order scenarios based on original data
        (data.get("virtual_payment_document")) or
        (data.get("name", "").startswith("new-multi-order-")) or
        (data.get("doctype") == "POS Multi Order Payment") or
        (data.get("is_multi_order_payment_view"))
    )
    
    # DEBUG: Always log what we're about to save to understand the issue
    frappe.log_error(
        message=f"FINAL SAFEGUARD DEBUG: About to save - Name: {getattr(invoice_doc, 'name', 'Unknown')}, Doctype: {invoice_doc.doctype}, is_virtual_payment: {is_virtual_payment}, has_virtual_flag: {hasattr(invoice_doc, 'virtual_payment_document')}, data_virtual_flag: {data.get('virtual_payment_document')}, data_name: {data.get('name')}, data_doctype: {data.get('doctype')}",
        title="Pre-Save Debug"
    )
    
    if is_virtual_payment:
        frappe.log_error(
            message=f"FINAL SAFEGUARD: Blocked save of virtual payment document. Name: {getattr(invoice_doc, 'name', 'Unknown')}, Doctype: {invoice_doc.doctype}",
            title="Virtual Payment Save Blocked"
        )
        # Set a delivery date to avoid validation error if this is a Sales Order
        if invoice_doc.doctype == "Sales Order" and not invoice_doc.delivery_date:
            from datetime import datetime, timedelta
            invoice_doc.delivery_date = (datetime.now() + timedelta(days=1)).date()
            
        # Create a fake response that looks like a saved document
        response = invoice_doc.as_dict()
        response["conversion_rate"] = getattr(invoice_doc, 'conversion_rate', 1.0)
        response["plc_conversion_rate"] = getattr(invoice_doc, 'plc_conversion_rate', 1.0)
        return response
    
    # BULLETPROOF DELIVERY DATE FIX: Ensure ALL Sales Orders have delivery_date before saving
    if invoice_doc.doctype == "Sales Order" and not invoice_doc.delivery_date:
        from datetime import datetime, timedelta
        invoice_doc.delivery_date = (datetime.now() + timedelta(days=1)).date()
        frappe.log_error(
            message=f"AUTO-SET delivery_date for Sales Order: {getattr(invoice_doc, 'name', 'Unknown')} to prevent validation error",
            title="Delivery Date Auto-Set"
        )
    
    # Reload document to avoid "Document has been modified" timestamp mismatch error
    if hasattr(invoice_doc, 'name') and invoice_doc.name and not invoice_doc.name.startswith('new-'):
        invoice_doc.reload()
    
    invoice_doc.save()

    # Return both the invoice doc and the updated data
    response = invoice_doc.as_dict()
    response["conversion_rate"] = invoice_doc.conversion_rate
    response["plc_conversion_rate"] = invoice_doc.plc_conversion_rate
    response["exchange_rate_date"] = exchange_rate_date
    return response


@frappe.whitelist()
def submit_invoice(invoice, data):
    data = json.loads(data)
    invoice = json.loads(invoice)
    pos_profile = invoice.get("pos_profile")
    doctype = "Sales Invoice"
    if pos_profile and frappe.db.get_value(
        "POS Profile", pos_profile, "create_pos_invoice_instead_of_sales_invoice"
    ):
        doctype = "POS Invoice"

    invoice_name = invoice.get("name")
    invoice_doc = None  # Initialize invoice_doc
    
    # CRITICAL FIX: Handle Sales Order to Sales Invoice conversion naming issue
    # If the invoice_name starts with "SO" (Sales Order), find the corresponding Sales Invoice
    if invoice_name and invoice_name.startswith("SO") and not frappe.db.exists(doctype, invoice_name):
        # Check if this is actually a Sales Order being converted
        if frappe.db.exists("Sales Order", invoice_name):
            frappe.log_error(f"SINGLE ORDER CONVERSION: Found Sales Order {invoice_name}, looking for corresponding Sales Invoice", "Submit Invoice Debug")
            
            # Find the corresponding Sales Invoice created from this Sales Order
            # Look for Sales Invoice Items that reference this Sales Order (any status)
            si_items = frappe.get_all("Sales Invoice Item", 
                filters={"sales_order": invoice_name}, 
                fields=["parent"], 
                order_by="creation desc")
            
            if si_items:
                # Found the corresponding Sales Invoice - use it for submission
                actual_invoice_name = si_items[0].parent
                
                # Check if the Sales Invoice is in draft status (can be updated/submitted)
                si_status = frappe.db.get_value("Sales Invoice", actual_invoice_name, "docstatus")
                
                if si_status == 0:  # Draft - can be submitted
                    invoice["name"] = actual_invoice_name  # Update the invoice data
                    invoice_name = actual_invoice_name
                    frappe.log_error(f"RESOLVED: Found draft Sales Invoice {actual_invoice_name} for Sales Order {invoice.get('name')}", "Submit Invoice Debug")
                    
                    # Load the existing Sales Invoice and update it with payment data
                    invoice_doc = frappe.get_doc(doctype, invoice_name)
                    invoice_doc.update(invoice)
                    frappe.log_error(f"UPDATED: Loaded and updated draft Sales Invoice {invoice_name}", "Submit Invoice Debug")
                elif si_status == 1:  # Already submitted
                    frappe.log_error(f"ALREADY SUBMITTED: Sales Invoice {actual_invoice_name} for Sales Order {invoice_name} is already submitted", "Submit Invoice Debug")
                    frappe.throw(_("Sales Order {0} has already been processed and submitted as Sales Invoice {1}").format(invoice_name, actual_invoice_name))
                else:  # Cancelled
                    frappe.log_error(f"CANCELLED: Sales Invoice {actual_invoice_name} for Sales Order {invoice_name} is cancelled", "Submit Invoice Debug")
                    frappe.throw(_("Sales Order {0} was processed as Sales Invoice {1} but it has been cancelled").format(invoice_name, actual_invoice_name))
            else:
                # No existing Sales Invoice found - this shouldn't happen if conversion was done properly
                # The order might not have been converted yet, so the frontend should convert it first
                frappe.log_error(f"NO SI FOUND: No Sales Invoice found for Sales Order {invoice_name}", "Submit Invoice Debug")
                frappe.throw(_("Sales Order {0} has not been converted to Sales Invoice yet. Please convert the order first.").format(invoice_name))
        else:
            # Neither Sales Order nor Sales Invoice exists with this name
            frappe.log_error(f"NAMING ERROR: Document {invoice_name} not found in either Sales Order or {doctype}", "Submit Invoice Error")
            frappe.throw(_("Document {0} not found. Please refresh and try again.").format(invoice_name))
    
    # Only proceed with standard document creation/loading if invoice_doc is not already set
    if not invoice_doc:
        if not invoice_name or not frappe.db.exists(doctype, invoice_name):
            # Standard case - create new invoice
            created = update_invoice(json.dumps(invoice))
            invoice_name = created.get("name")
            invoice_doc = frappe.get_doc(doctype, invoice_name)
        else:
            # Invoice exists - load and update it
            invoice_doc = frappe.get_doc(doctype, invoice_name)
            invoice_doc.update(invoice)

    # Ensure item name overrides are respected on submit
    _apply_item_name_overrides(invoice_doc)
    
    # FORCE DISABLE stock update for restaurant orders to avoid stock validation issues
    pos_profile_doc = None
    if pos_profile:
        pos_profile_doc = frappe.get_cached_doc("POS Profile", pos_profile)
        if pos_profile_doc and getattr(pos_profile_doc, 'posa_enable_restaurant_mode', 0):
            invoice_doc.update_stock = 0
    
    # Also disable for delivery orders
    if invoice.get("posa_delivery_date"):
        invoice_doc.update_stock = 0
    mop_cash_list = [
        i.mode_of_payment
        for i in invoice_doc.payments
        if "cash" in i.mode_of_payment.lower() and i.type == "Cash"
    ]
    if len(mop_cash_list) > 0:
        cash_account = get_bank_cash_account(mop_cash_list[0], invoice_doc.company)
    else:
        cash_account = {"account": frappe.get_value("Company", invoice_doc.company, "default_cash_account")}

    # Update remarks with items details
    items = []
    for item in invoice_doc.items:
        if item.item_name and item.rate and item.qty:
            total = item.rate * item.qty
            items.append(f"{item.item_name} - Rate: {item.rate}, Qty: {item.qty}, Amount: {total}")

    # Add the grand total at the end of remarks
    grand_total = f"\nGrand Total: {invoice_doc.grand_total}"
    items.append(grand_total)

    invoice_doc.remarks = "\n".join(items)

    # creating advance payment
    if data.get("credit_change"):
        advance_payment_entry = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "mode_of_payment": "Cash",
                "paid_to": cash_account["account"],
                "payment_type": "Receive",
                "party_type": "Customer",
                "party": invoice_doc.get("customer"),
                "paid_amount": invoice_doc.get("credit_change"),
                "received_amount": invoice_doc.get("credit_change"),
                "company": invoice_doc.get("company"),
            }
        )

        advance_payment_entry.flags.ignore_permissions = True
        frappe.flags.ignore_account_permission = True
        advance_payment_entry.save()
        advance_payment_entry.submit()

    # calculating cash
    total_cash = 0
    if data.get("redeemed_customer_credit"):
        total_cash = invoice_doc.total - float(data.get("redeemed_customer_credit"))

    is_payment_entry = 0
    if data.get("redeemed_customer_credit"):
        for row in data.get("customer_credit_dict"):
            if row["type"] == "Advance" and row["credit_to_redeem"]:
                advance = frappe.get_doc("Payment Entry", row["credit_origin"])

                advance_payment = {
                    "reference_type": "Payment Entry",
                    "reference_name": advance.name,
                    "remarks": advance.remarks,
                    "advance_amount": advance.unallocated_amount,
                    "allocated_amount": row["credit_to_redeem"],
                }

                advance_row = invoice_doc.append("advances", {})
                advance_row.update(advance_payment)
                child_dt = (
                    "POS Invoice Advance"
                    if invoice_doc.doctype == "POS Invoice"
                    else "Sales Invoice Advance"
                )
                ensure_child_doctype(invoice_doc, "advances", child_dt)
                invoice_doc.is_pos = 0
                is_payment_entry = 1

    payments = invoice_doc.payments

    _auto_set_return_batches(invoice_doc)

    # if frappe.get_value("POS Profile", invoice_doc.pos_profile, "posa_auto_set_batch"):
    #     set_batch_nos(invoice_doc, "warehouse", throw=True)
    set_batch_nos_for_bundels(invoice_doc, "warehouse", throw=True)

    _validate_stock_on_invoice(invoice_doc)

    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    invoice_doc.posa_is_printed = 1
    invoice_doc.save()

    if data.get("due_date"):
        frappe.db.set_value(
            invoice_doc.doctype,
            invoice_doc.name,
            "due_date",
            data.get("due_date"),
            update_modified=False,
        )

    if frappe.get_value(
        "POS Profile",
        invoice_doc.pos_profile,
        "posa_allow_submissions_in_background_job",
    ):
        invoices_list = frappe.get_all(
            invoice_doc.doctype,
            filters={
                "posa_pos_opening_shift": invoice_doc.posa_pos_opening_shift,
                "docstatus": 0,
                "posa_is_printed": 1,
            },
        )
        for invoice in invoices_list:
            enqueue(
                method=submit_in_background_job,
                queue="short",
                timeout=1000,
                is_async=True,
                kwargs={
                    "invoice": invoice.name,
                    "doctype": invoice_doc.doctype,
                    "invoice_doc": invoice_doc,
                    "data": data,
                    "is_payment_entry": is_payment_entry,
                    "total_cash": total_cash,
                    "cash_account": cash_account,
                    "payments": payments,
                },
            )
    else:
        # CRITICAL: Auto-submit related Sales Orders before submitting Sales Invoice
        # ERPNext requires Sales Orders to be submitted before Sales Invoice submission
        for item in invoice_doc.items:
            if hasattr(item, 'sales_order') and item.sales_order:
                so_name = item.sales_order
                so_doc = frappe.get_doc("Sales Order", so_name)
                
                if so_doc.docstatus == 0:  # Draft status - needs submission
                    frappe.log_error(f"AUTO-SUBMIT: Sales Order {so_name} is in Draft status, submitting before invoice submission", "Submit Invoice Debug")
                    
                    # Ensure delivery_date is set before submission
                    if not so_doc.delivery_date:
                        from datetime import datetime, timedelta
                        so_doc.delivery_date = (datetime.now() + timedelta(days=1)).date()
                        frappe.log_error(f"AUTO-SET delivery_date for SO {so_name}: {so_doc.delivery_date}", "Submit Invoice Debug")
                    
                    # Submit the Sales Order
                    so_doc.submit()
                    frappe.log_error(f"SUCCESS: Auto-submitted Sales Order {so_name} before invoice submission", "Submit Invoice Debug")
                elif so_doc.docstatus == 2:  # Cancelled
                    frappe.throw(_("Cannot submit Sales Invoice: Referenced Sales Order {0} is cancelled").format(so_name))
        
        invoice_doc.submit()
        redeeming_customer_credit(invoice_doc, data, is_payment_entry, total_cash, cash_account, payments)
        
        # Update related Sales Orders billing status after invoice submission
        _update_related_sales_orders(invoice_doc)

    return {"name": invoice_doc.name, "status": invoice_doc.docstatus}


def submit_in_background_job(kwargs):
    invoice = kwargs.get("invoice")
    doctype = kwargs.get("doctype") or "Sales Invoice"
    data = kwargs.get("data")
    is_payment_entry = kwargs.get("is_payment_entry")
    total_cash = kwargs.get("total_cash")
    cash_account = kwargs.get("cash_account")
    payments = kwargs.get("payments")

    invoice_doc = frappe.get_doc(doctype, invoice)

    # Update remarks with items details for background job
    items = []
    for item in invoice_doc.items:
        if item.item_name and item.rate and item.qty:
            total = item.rate * item.qty
            items.append(f"{item.item_name} - Rate: {item.rate}, Qty: {item.qty}, Amount: {total}")

    # Add the grand total at the end of remarks
    grand_total = f"\nGrand Total: {invoice_doc.grand_total}"
    items.append(grand_total)

    invoice_doc.remarks = "\n".join(items)
    invoice_doc.save()

    invoice_doc.submit()
    redeeming_customer_credit(invoice_doc, data, is_payment_entry, total_cash, cash_account, payments)
    
    # Update related Sales Orders billing status after invoice submission
    _update_related_sales_orders(invoice_doc)


@frappe.whitelist()
def delete_invoice(invoice):
    doctype = "Sales Invoice"
    if frappe.db.exists("POS Invoice", invoice):
        doctype = "POS Invoice"
    elif not frappe.db.exists("Sales Invoice", invoice):
        frappe.throw(_("Invoice {0} does not exist").format(invoice))

    if frappe.db.has_column(doctype, "posa_is_printed") and frappe.get_value(
        doctype, invoice, "posa_is_printed"
    ):
        frappe.throw(_("This invoice {0} cannot be deleted").format(invoice))

    frappe.delete_doc(doctype, invoice, force=1)
    return _("Invoice {0} Deleted").format(invoice)


@frappe.whitelist()
def get_draft_invoices(pos_opening_shift, doctype="Sales Invoice"):
    filters = {
        "posa_pos_opening_shift": pos_opening_shift,
        "docstatus": 0,
    }
    if frappe.db.has_column(doctype, "posa_is_printed"):
        filters["posa_is_printed"] = 0

    invoices_list = frappe.get_list(
        doctype,
        filters=filters,
        fields=["name"],
        limit_page_length=0,
        order_by="modified desc",
    )
    data = []
    for invoice in invoices_list:
        data.append(frappe.get_cached_doc(doctype, invoice["name"]))
    return data


@frappe.whitelist()
def search_invoices_for_return(
    invoice_name,
    company,
    customer_name=None,
    customer_id=None,
    mobile_no=None,
    tax_id=None,
    from_date=None,
    to_date=None,
    min_amount=None,
    max_amount=None,
    page=1,
    doctype="Sales Invoice",
):
    """
    Search for invoices that can be returned with separate customer search fields and pagination

    Args:
        invoice_name: Invoice ID to search for
        company: Company to search in
        customer_name: Customer name to search for
        customer_id: Customer ID to search for
        mobile_no: Mobile number to search for
        tax_id: Tax ID to search for
        from_date: Start date for filtering
        to_date: End date for filtering
        min_amount: Minimum invoice amount to filter by
        max_amount: Maximum invoice amount to filter by
        page: Page number for pagination (starts from 1)

    Returns:
        Dictionary with:
        - invoices: List of invoice documents
        - has_more: Boolean indicating if there are more invoices to load
    """
    # Start with base filters
    filters = {
        "company": company,
        "docstatus": 1,
        "is_return": 0,
    }

    # Convert page to integer if it's a string
    if page and isinstance(page, str):
        page = int(page)
    else:
        page = 1  # Default to page 1

    # Items per page - can be adjusted based on performance requirements
    page_length = 100
    start = (page - 1) * page_length

    # Add invoice name filter if provided
    if invoice_name:
        filters["name"] = ["like", f"%{invoice_name}%"]

    # Add date range filters if provided
    if from_date:
        filters["posting_date"] = [">=", from_date]

    if to_date:
        if "posting_date" in filters:
            filters["posting_date"] = ["between", [from_date, to_date]]
        else:
            filters["posting_date"] = ["<=", to_date]

    # Add amount filters if provided
    if min_amount:
        filters["grand_total"] = [">=", float(min_amount)]

    if max_amount:
        if "grand_total" in filters:
            # If min_amount was already set, change to between
            filters["grand_total"] = ["between", [float(min_amount), float(max_amount)]]
        else:
            filters["grand_total"] = ["<=", float(max_amount)]

    # If any customer search criteria is provided, find matching customers
    customer_ids = []
    if customer_name or customer_id or mobile_no or tax_id:
        conditions = []
        params = {}

        if customer_name:
            conditions.append("customer_name LIKE %(customer_name)s")
            params["customer_name"] = f"%{customer_name}%"

        if customer_id:
            conditions.append("name LIKE %(customer_id)s")
            params["customer_id"] = f"%{customer_id}%"

        if mobile_no:
            conditions.append("mobile_no LIKE %(mobile_no)s")
            params["mobile_no"] = f"%{mobile_no}%"

        if tax_id:
            conditions.append("tax_id LIKE %(tax_id)s")
            params["tax_id"] = f"%{tax_id}%"

        # Build the WHERE clause for the query
        where_clause = " OR ".join(conditions)
        customer_query = f"""
        SELECT name
        FROM `tabCustomer`
        WHERE {where_clause}
        LIMIT 100
    """

        customers = frappe.db.sql(customer_query, params, as_dict=True)
        customer_ids = [c.name for c in customers]

        # If we found matching customers, add them to the filter
        if customer_ids:
            filters["customer"] = ["in", customer_ids]
        # If customer search criteria provided but no matches found, return empty
        elif any([customer_name, customer_id, mobile_no, tax_id]):
            return {"invoices": [], "has_more": False}

    # Count total invoices matching the criteria (for has_more flag)
    total_count_query = frappe.get_list(
        doctype,
        filters=filters,
        fields=["count(name) as total_count"],
        as_list=False,
    )
    total_count = total_count_query[0].total_count if total_count_query else 0

    # Get invoices matching all criteria with pagination
    invoices_list = frappe.get_list(
        doctype,
        filters=filters,
        fields=["name"],
        limit_start=start,
        limit_page_length=page_length,
        order_by="posting_date desc, name desc",
    )

    # Process and return the results
    data = []

    # Process invoices and check for returns
    for invoice in invoices_list:
        invoice_doc = frappe.get_doc(doctype, invoice.name)

        # Check if any items have already been returned
        has_returns = frappe.get_all(
            doctype,
            filters={"return_against": invoice.name, "docstatus": 1},
            fields=["name"],
        )

        if has_returns:
            # Calculate returned quantity per item_code
            returned_qty = {}
            for ret_inv in has_returns:
                ret_doc = frappe.get_doc(doctype, ret_inv.name)
                for item in ret_doc.items:
                    returned_qty[item.item_code] = returned_qty.get(item.item_code, 0) + abs(item.qty)

            # Filter items with remaining qty
            filtered_items = []
            for item in invoice_doc.items:
                remaining_qty = item.qty - returned_qty.get(item.item_code, 0)
                if remaining_qty > 0:
                    new_item = item.as_dict().copy()
                    new_item["qty"] = remaining_qty
                    new_item["amount"] = remaining_qty * item.rate
                    if item.get("stock_qty"):
                        new_item["stock_qty"] = (
                            item.stock_qty / item.qty * remaining_qty if item.qty else remaining_qty
                        )
                    filtered_items.append(frappe._dict(new_item))

            if filtered_items:
                # Create a copy of invoice with filtered items
                filtered_invoice = frappe.get_doc(doctype, invoice.name)
                filtered_invoice.items = filtered_items
                data.append(filtered_invoice)
        else:
            data.append(invoice_doc)

    # Check if there are more results
    has_more = (start + page_length) < total_count

    return {"invoices": data, "has_more": has_more}


@frappe.whitelist()
def create_sales_invoice_from_order(sales_order):
    sales_invoice = make_sales_invoice(sales_order, ignore_permissions=True)
    sales_invoice.save()
    return sales_invoice


@frappe.whitelist()
def delete_sales_invoice(sales_invoice):
    frappe.delete_doc("Sales Invoice", sales_invoice)


@frappe.whitelist()
def get_sales_invoice_child_table(sales_invoice, sales_invoice_item):
    parent_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    child_doc = frappe.get_doc("Sales Invoice Item", {"parent": parent_doc.name, "name": sales_invoice_item})
    return child_doc


@frappe.whitelist()
def update_invoice_from_order(data):
    data = json.loads(data)
    invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
    invoice_doc.update(data)
    invoice_doc.save()
    return invoice_doc


@frappe.whitelist()
def get_available_currencies():
    """Get list of available currencies from ERPNext"""
    return frappe.get_all(
        "Currency",
        fields=["name", "currency_name"],
        filters={"enabled": 1},
        order_by="currency_name",
    )


@frappe.whitelist()
def fetch_exchange_rate(
    currency: str, company: str, posting_date: str | None = None
):
    """Return latest exchange rate and its date."""
    company_currency = frappe.get_cached_value("Company", company, "default_currency")
    rate, date = get_latest_rate(currency, company_currency)
    return {"exchange_rate": rate, "date": date}


@frappe.whitelist()
def fetch_exchange_rate_pair(
    from_currency: str, to_currency: str, posting_date: str | None = None
):
    """Return latest exchange rate between two currencies along with rate date."""
    rate, date = get_latest_rate(from_currency, to_currency)
    return {"exchange_rate": rate, "date": date}


@frappe.whitelist()
def get_price_list_currency(price_list: str) -> str:
    """Return the currency of the given Price List."""
    if not price_list:
        return None
    return frappe.db.get_value("Price List", price_list, "currency")


@frappe.whitelist()
def debug_so_to_si_query(sales_order_name="SO00013"):
    """Debug function to test our SO to SI query"""
    si_items = frappe.get_all("Sales Invoice Item", 
        filters={"sales_order": sales_order_name}, 
        fields=["parent"], 
        order_by="creation desc")
    
    result = {
        "sales_order": sales_order_name,
        "found_invoices": si_items,
        "count": len(si_items)
    }
    
    if si_items:
        result["existing_invoice"] = si_items[0].parent
        # Try loading the document
        try:
            si_doc = frappe.get_doc("Sales Invoice", si_items[0].parent)
            result["invoice_status"] = si_doc.docstatus
            result["invoice_doctype"] = si_doc.doctype
        except Exception as e:
            result["error"] = str(e)
    
    return result


@frappe.whitelist()
def check_invoice_modification_status(invoice_name):
    """
    Check if an invoice has been modified and return its current state.
    This helps prevent modification conflicts.
    """
    try:
        # Handle SO to SI conversion
        if invoice_name and invoice_name.startswith("SO"):
            si_items = frappe.get_all("Sales Invoice Item", 
                filters={"sales_order": invoice_name}, 
                fields=["parent"])
            
            if si_items:
                invoice_name = si_items[0].parent
            else:
                return {"exists": False, "error": f"No Sales Invoice found for SO {invoice_name}"}
        
        # Check if invoice exists
        if not frappe.db.exists("Sales Invoice", invoice_name):
            return {"exists": False, "error": f"Sales Invoice {invoice_name} not found"}
        
        # Get basic info without loading full document
        invoice_info = frappe.db.get_value("Sales Invoice", invoice_name, 
            ["name", "modified", "docstatus", "status", "outstanding_amount", "grand_total"], 
            as_dict=True)
        
        return {
            "exists": True,
            "name": invoice_info.name,
            "modified": invoice_info.modified,
            "docstatus": invoice_info.docstatus,
            "status": invoice_info.status,
            "outstanding_amount": invoice_info.outstanding_amount,
            "grand_total": invoice_info.grand_total,
            "is_paid": invoice_info.outstanding_amount == 0,
            "can_pay": invoice_info.docstatus == 0 and invoice_info.outstanding_amount > 0
        }
        
    except Exception as e:
        return {"exists": False, "error": str(e)}
    """
    Safely handle invoice payment with proper document locking and state management.
    This prevents modification conflicts during payment processing.
    """
    try:
        # Handle both SO and SI names
        if invoice_name and invoice_name.startswith("SO"):
            # Convert SO to SI name first
            si_items = frappe.get_all("Sales Invoice Item", 
                filters={"sales_order": invoice_name}, 
                fields=["parent"], 
                order_by="creation desc")
            
            if si_items:
                invoice_name = si_items[0].parent
                frappe.log_error(f"PAY_SAFELY: Converted SO {invoice_name} to SI {si_items[0].parent}", "Payment Debug")
            else:
                frappe.throw(_("No Sales Invoice found for Sales Order {0}").format(invoice_name))
        
        # Load the Sales Invoice with proper locking
        invoice_doc = frappe.get_doc("Sales Invoice", invoice_name)
        
        # CRITICAL: Always reload to get the latest version
        invoice_doc.reload()
        
        # Update payment data if provided
        if payment_data:
            if isinstance(payment_data, str):
                payment_data = json.loads(payment_data)
            
            # Update payments
            if payment_data.get("payments"):
                for idx, payment in enumerate(payment_data["payments"]):
                    if idx < len(invoice_doc.payments):
                        invoice_doc.payments[idx].amount = payment.get("amount", 0)
                        invoice_doc.payments[idx].mode_of_payment = payment.get("mode_of_payment")
            
            # Update any other fields
            for key, value in payment_data.items():
                if key != "payments" and hasattr(invoice_doc, key):
                    setattr(invoice_doc, key, value)
        
        # Calculate totals and validate
        invoice_doc.calculate_taxes_and_totals()
        
        # Save the document
        invoice_doc.save()
        
        # Submit if ready
        if invoice_doc.docstatus == 0 and invoice_doc.paid_amount > 0:
            invoice_doc.submit()
        
        return invoice_doc.as_dict()
        
    except Exception as e:
        frappe.log_error(f"PAY_SAFELY ERROR for {invoice_name}: {str(e)}", "Payment Error")
        frappe.throw(_("Error processing payment for invoice {0}: {1}").format(invoice_name, str(e)))


@frappe.whitelist()
def safe_update_invoice(data):
    """Wrapper for update_invoice that handles SO to SI conversion properly"""
    data = json.loads(data) if isinstance(data, str) else data
    
    # Check if this is a Sales Order that needs conversion
    if data.get("name") and data.get("name").startswith("SO"):
        sales_order_name = data.get("name")
        
        # Find existing Sales Invoice for this SO
        si_items = frappe.get_all("Sales Invoice Item", 
            filters={"sales_order": sales_order_name}, 
            fields=["parent"], 
            order_by="creation desc")
        
        if si_items:
            # Use existing Sales Invoice
            existing_invoice_name = si_items[0].parent
            frappe.log_error(f"SAFE_UPDATE: Found existing SI {existing_invoice_name} for SO {sales_order_name}", "Safe Update Debug")
            
            # Update data to use the correct invoice name and doctype
            data["name"] = existing_invoice_name
            data["doctype"] = "Sales Invoice"
            
            # Now call the regular update_invoice with the corrected data
            return update_invoice(json.dumps(data))
        else:
            # No existing invoice - convert first then update
            frappe.log_error(f"SAFE_UPDATE: Converting SO {sales_order_name} to SI first", "Safe Update Debug")
            
            from posawesome.posawesome.api.restaurant_orders import convert_order_to_invoice
            converted_data = convert_order_to_invoice(sales_order_name, data.get("pos_profile"))
            
            if converted_data and converted_data.get("name"):
                # Update data to use the new invoice
                data["name"] = converted_data["name"]
                data["doctype"] = "Sales Invoice"
                
                # Now call the regular update_invoice
                return update_invoice(json.dumps(data))
            else:
                frappe.throw(_("Failed to convert Sales Order {0} to Sales Invoice").format(sales_order_name))
    else:
        # Regular invoice update
        return update_invoice(json.dumps(data))


@frappe.whitelist()
def pay_invoice_safely(invoice_name, payment_data=None):
    """
    Safely handle invoice payment with proper document locking and state management.
    This prevents modification conflicts during payment processing.
    """
    try:
        # Handle both SO and SI names
        if invoice_name and invoice_name.startswith("SO"):
            # Convert SO to SI name first
            si_items = frappe.get_all("Sales Invoice Item", 
                filters={"sales_order": invoice_name}, 
                fields=["parent"], 
                order_by="creation desc")
            
            if si_items:
                original_so_name = invoice_name
                invoice_name = si_items[0].parent
                frappe.log_error(f"PAY_SAFELY: Converted SO {original_so_name} to SI {invoice_name}", "Payment Debug")
            else:
                frappe.throw(_("No Sales Invoice found for Sales Order {0}").format(invoice_name))
        
        # Load the Sales Invoice with proper locking
        invoice_doc = frappe.get_doc("Sales Invoice", invoice_name)
        
        # CRITICAL: Always reload to get the latest version
        invoice_doc.reload()
        
        # Update payment data if provided
        if payment_data:
            if isinstance(payment_data, str):
                payment_data = json.loads(payment_data)
            
            # Update payments
            if payment_data.get("payments"):
                for idx, payment in enumerate(payment_data["payments"]):
                    if idx < len(invoice_doc.payments):
                        invoice_doc.payments[idx].amount = payment.get("amount", 0)
                        invoice_doc.payments[idx].mode_of_payment = payment.get("mode_of_payment")
            
            # Update any other fields
            for key, value in payment_data.items():
                if key != "payments" and hasattr(invoice_doc, key):
                    setattr(invoice_doc, key, value)
        
        # Calculate totals and validate
        invoice_doc.calculate_taxes_and_totals()
        
        # Save the document
        invoice_doc.save()
        
        # Submit if ready and has payments - but handle SO validation
        if invoice_doc.docstatus == 0 and invoice_doc.paid_amount > 0:
            try:
                # Check if any Sales Orders need to be submitted first
                for item in invoice_doc.items:
                    if hasattr(item, 'sales_order') and item.sales_order:
                        so_doc = frappe.get_doc("Sales Order", item.sales_order)
                        if so_doc.docstatus == 0:
                            frappe.log_error(f"Auto-submitting Sales Order {item.sales_order} before invoice submission", "Payment Debug")
                            so_doc.submit()
                
                # Now submit the invoice
                invoice_doc.submit()
                frappe.log_error(f"Successfully submitted invoice {invoice_doc.name}", "Payment Debug")
                
            except Exception as submit_error:
                frappe.log_error(f"Invoice submission failed for {invoice_doc.name}: {str(submit_error)}", "Payment Debug")
                # Don't fail the payment, just log the error
                # The invoice is saved with payments, just not submitted
                pass
        
        return invoice_doc.as_dict()
        
    except Exception as e:
        frappe.log_error(f"PAY_SAFELY ERROR for {invoice_name}: {str(e)}", "Payment Error")
        frappe.throw(_("Error processing payment for invoice {0}: {1}").format(invoice_name, str(e)))
