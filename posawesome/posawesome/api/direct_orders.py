import frappe
from frappe import _
from posawesome.posawesome.api.invoices import update_invoice


@frappe.whitelist()
def create_direct_invoice(customer, items, pos_profile, company, currency=None, conversion_rate=1, plc_conversion_rate=1, taxes_and_charges=None, print_kot=False):
    """Create a Sales Invoice directly without restaurant order (for Direct Order modes)"""
    try:
        # Prepare invoice data structure similar to get_invoice_doc
        invoice_data = {
            "doctype": "Sales Invoice",
            "customer": customer,
            "company": company,
            "pos_profile": pos_profile,
            "currency": currency,
            "conversion_rate": conversion_rate,
            "plc_conversion_rate": plc_conversion_rate,
            "is_pos": 1,
            "update_stock": 0,  # For restaurant mode
            "items": items,
            "taxes_and_charges": taxes_and_charges,
            "posting_date": frappe.utils.nowdate(),
            "posting_time": frappe.utils.nowtime()
        }
        
        # Create the invoice using the standard update_invoice method
        invoice_doc = update_invoice(frappe.as_json(invoice_data))
        
        result = {"invoice": invoice_doc}
        
        # If Direct Order + KOT mode, generate KOT data
        if print_kot and invoice_doc.get("name"):
            try:
                kot_data = generate_kot_for_invoice(invoice_doc["name"])
                result["kot_data"] = kot_data
                result["kot_printed"] = True
            except Exception as e:
                frappe.log_error(f"Failed to generate KOT for direct order {invoice_doc['name']}: {str(e)}")
                result["kot_printed"] = False
                # Don't fail the invoice creation if KOT generation fails
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error creating direct invoice: {str(e)}")
        frappe.throw(_("Error creating direct invoice: {0}").format(str(e)))


def generate_kot_for_invoice(invoice_name):
    """Generate KOT data for a direct invoice"""
    try:
        invoice = frappe.get_doc("Sales Invoice", invoice_name)
        
        # Prepare KOT data structure
        kot_data = {
            "invoice_name": invoice_name,
            "customer": invoice.customer,
            "customer_name": invoice.customer_name,
            "order_type": invoice.get("restaurant_order_type"),
            "table_number": invoice.get("table_number"),
            "posting_date": invoice.posting_date,
            "posting_time": invoice.posting_time,
            "items": []
        }
        
        # Add items to KOT
        for item in invoice.items:
            kot_item = {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "uom": item.uom,
                "rate": item.rate,
                "amount": item.amount
            }
            kot_data["items"].append(kot_item)
        
        # Generate print format URL for KOT
        if frappe.db.exists("Print Format", "Kitchen Order Ticket"):
            kot_data["print_url"] = f"/printview?doctype=Sales%20Invoice&name={invoice_name}&format=Kitchen%20Order%20Ticket"
        
        return kot_data
        
    except Exception as e:
        frappe.log_error(f"Error generating KOT for invoice {invoice_name}: {str(e)}")
        return None


@frappe.whitelist()
def validate_direct_order_cart(items, pos_profile_name):
    """Validate cart items for direct order mode"""
    try:
        # Basic validation for direct orders
        if not items:
            frappe.throw(_("Cart is empty. Please add items before proceeding."))
        
        # Additional validations can be added here
        # For example, stock validation, price validation, etc.
        
        return {"valid": True, "message": "Cart validated successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error validating direct order cart: {str(e)}")
        return {"valid": False, "message": str(e)}
