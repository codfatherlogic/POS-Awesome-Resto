import frappe
from frappe import _
import json


@frappe.whitelist()
def create_direct_invoice(customer, items, pos_profile, company, currency=None, conversion_rate=1, plc_conversion_rate=1, taxes_and_charges=None, print_kot=False):
    """Create a Sales Invoice directly without restaurant order (for Direct Order modes)"""
    try:
        # Parse JSON strings if necessary
        if isinstance(items, str):
            items = json.loads(items)
        if isinstance(print_kot, str):
            print_kot = print_kot.lower() in ('true', '1', 'yes')
        
        # Create a new Sales Invoice document
        invoice_doc = frappe.new_doc("Sales Invoice")
        
        # Set basic fields
        invoice_doc.customer = customer
        invoice_doc.company = company
        invoice_doc.pos_profile = pos_profile
        invoice_doc.currency = currency or frappe.get_cached_value("Company", company, "default_currency")
        invoice_doc.conversion_rate = float(conversion_rate)
        invoice_doc.plc_conversion_rate = float(plc_conversion_rate)
        invoice_doc.is_pos = 1
        invoice_doc.update_stock = 0  # For restaurant mode
        invoice_doc.posting_date = frappe.utils.nowdate()
        invoice_doc.posting_time = frappe.utils.nowtime()
        
        # Add taxes and charges if provided
        if taxes_and_charges:
            invoice_doc.taxes_and_charges = taxes_and_charges
        
        # Add items to the invoice
        for item_data in items:
            item = invoice_doc.append("items", {})
            item.item_code = item_data.get("item_code")
            item.qty = float(item_data.get("qty", 1))
            item.rate = float(item_data.get("rate", 0))
            item.amount = float(item_data.get("amount", 0))
            item.description = item_data.get("description", "")
            item.warehouse = item_data.get("warehouse")
            item.uom = item_data.get("uom")
            item.stock_uom = item_data.get("stock_uom")
            item.conversion_factor = float(item_data.get("conversion_factor", 1))
        
        # Set missing values and save
        invoice_doc.flags.ignore_permissions = True
        invoice_doc.set_missing_values()
        invoice_doc.save()
        
        result = {"invoice": invoice_doc.as_dict()}
        
        # If Direct Order + KOT mode, generate KOT data
        if print_kot and invoice_doc.name:
            try:
                kot_data = generate_kot_for_invoice(invoice_doc.name)
                result["kot_data"] = kot_data
                result["kot_printed"] = True
            except Exception as e:
                frappe.log_error(f"Failed to generate KOT for direct order {invoice_doc.name}: {str(e)}")
                result["kot_printed"] = False
                # Don't fail the invoice creation if KOT generation fails
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error creating direct invoice: {str(e)}")
        frappe.throw(_("Error creating direct invoice: {0}").format(str(e)))


@frappe.whitelist()
def generate_kot_for_invoice(invoice_name):
    """Generate KOT data for a direct invoice"""
    try:
        invoice = frappe.get_doc("Sales Invoice", invoice_name)
        
        # Get current timestamp for KOT
        now = frappe.utils.now_datetime()
        
        # Prepare KOT data structure
        kot_data = {
            "invoice_name": invoice_name,
            "customer": invoice.customer,
            "customer_name": invoice.customer_name or invoice.customer,
            "order_type": invoice.get("restaurant_order_type") or "Direct Order",
            "table_number": invoice.get("table_number") or "",
            "posting_date": invoice.posting_date,
            "posting_time": invoice.posting_time,
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "kot_number": f"KOT-{invoice_name}",
            "items": [],
            "total_items": 0,
            "special_notes": "Direct Order - Kitchen preparation required"
        }
        
        # Add items to KOT
        total_qty = 0
        for item in invoice.items:
            kot_item = {
                "item_code": item.item_code,
                "item_name": item.item_name or item.item_code,
                "qty": item.qty,
                "uom": item.uom or "Nos",
                "rate": item.rate,
                "amount": item.amount,
                "special_instructions": ""
            }
            kot_data["items"].append(kot_item)
            total_qty += item.qty
        
        kot_data["total_items"] = int(total_qty)
        
        # Generate print format URL for KOT if available
        if frappe.db.exists("Print Format", "Kitchen Order Ticket"):
            kot_data["print_url"] = f"/printview?doctype=Sales%20Invoice&name={invoice_name}&format=Kitchen%20Order%20Ticket"
        
        return kot_data
        
    except Exception as e:
        frappe.log_error(f"Error generating KOT for invoice {invoice_name}: {str(e)}")
        return None


@frappe.whitelist()
def generate_kot_html_for_latest_invoice():
    """Generate KOT HTML for the most recently created invoice in this session"""
    try:
        # Get the most recent invoice created by this user
        latest_invoice = frappe.db.get_list(
            "Sales Invoice",
            filters={
                "owner": frappe.session.user,
                "docstatus": 1
            },
            fields=["name"],
            order_by="creation desc",
            limit=1
        )
        
        if not latest_invoice:
            frappe.throw(_("No recent invoice found"))
            
        invoice_name = latest_invoice[0].name
        frappe.log_error(f"DEBUG: Using latest invoice: {invoice_name}")
        
        kot_data = generate_kot_for_invoice(invoice_name)
        if not kot_data:
            frappe.throw(_("Failed to generate KOT data for invoice {0}").format(invoice_name))
        
        # Generate HTML for KOT printing
        items_html = ""
        for item in kot_data["items"]:
            items_html += f"""
            <tr>
                <td style="padding: 2px 0; border-bottom: 1px dotted #ccc;">
                    {item['item_name']}
                </td>
                <td style="padding: 2px 0; text-align: center; border-bottom: 1px dotted #ccc;">
                    {item['qty']} {item['uom']}
                </td>
            </tr>"""
        
        table_info = f"<p><strong>Table:</strong> {kot_data['table_number']}</p>" if kot_data["table_number"] else ""
        notes_section = f"<p><strong>Notes:</strong> {kot_data['special_notes']}</p>" if kot_data["special_notes"] else ""
        
        kot_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>KOT - {kot_data['kot_number']}</title>
            <style>
                body {{ margin: 0; padding: 2px; font-family: 'Courier New', monospace; width: 58mm; font-size: 10px; }}
                .header {{ text-align: center; border-bottom: 1px solid #000; padding-bottom: 5px; margin-bottom: 8px; }}
                .kot-title {{ font-size: 12px; font-weight: bold; margin: 2px 0; }}
                .kot-info {{ margin-bottom: 8px; font-size: 9px; }}
                .kot-info p {{ margin: 2px 0; }}
                .dashed-line {{ border-bottom: 1px dashed #000; margin: 8px 0; }}
                .items-table {{ width: 100%; border-collapse: collapse; font-size: 9px; }}
                .items-table th, .items-table td {{ border: none; padding: 1px 2px; text-align: left; }}
                .items-table th {{ border-bottom: 1px solid #000; font-weight: bold; font-size: 8px; }}
                .footer {{ margin-top: 8px; text-align: center; border-top: 1px solid #000; padding-top: 5px; font-size: 9px; }}
                @media print {{
                    body {{ margin: 0; padding: 2px; width: 58mm; }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2 class="kot-title">KITCHEN ORDER TICKET</h2>
                <p><strong>KOT #:</strong> {kot_data['kot_number']}</p>
            </div>
            
            <div class="kot-info">
                <p><strong>Type:</strong> {kot_data['order_type']}</p>
                {table_info}
                <p><strong>Customer:</strong> {kot_data['customer_name']}</p>
                <p><strong>Date & Time:</strong> {kot_data['datetime']}</p>
            </div>
            
            <div class="dashed-line"></div>
            
            <table class="items-table">
                <thead>
                    <tr>
                        <th style="width: 60%;">ITEM</th>
                        <th style="width: 40%; text-align: center;">QTY</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>
            
            <div class="dashed-line"></div>
            
            <div class="kot-info">
                <p><strong>Total Items:</strong> {kot_data['total_items']}</p>
                {notes_section}
            </div>
            
            <div class="footer">
                <p><strong>*** KITCHEN COPY ***</strong></p>
                <p>Please prepare items as ordered</p>
            </div>
            
            <script>
                window.onload = function() {{
                    window.print();
                }};
            </script>
        </body>
        </html>
        """
        
        return kot_html
        
    except Exception as e:
        frappe.log_error(f"Error generating KOT HTML for invoice {invoice_name}: {str(e)}")
        frappe.throw(_("Error generating KOT HTML: {0}").format(str(e)))


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
