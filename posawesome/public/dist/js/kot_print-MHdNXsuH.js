function c(t, i = {}) {
  const o = a(t, i), e = window.open("", "_blank");
  return e.document.write(o), e.document.close(), e.focus(), i.autoPrint !== !1 && (e.print(), setTimeout(() => {
    e.close();
  }, 1e3)), e;
}
function g(t, i = {}) {
  const o = b(t, i), e = window.open("", "_blank");
  return e.document.write(o), e.document.close(), e.focus(), i.autoPrint !== !1 && (e.print(), setTimeout(() => {
    e.close();
  }, 1e3)), e;
}
function a(t, i = {}) {
  const o = i.printWidth || t.print_width || "58mm", e = o === "80mm", d = e ? "font-family: 'Courier New', monospace; width: 80mm; margin: 0; padding: 8px; font-size: 12px; line-height: 1.3;" : "font-family: 'Courier New', monospace; width: 58mm; margin: 0; padding: 5px; font-size: 10px; line-height: 1.2;", r = e ? "14px" : "12px", s = e ? "11px" : "9px", l = e ? "11px" : "9px", p = e ? "10px" : "8px", m = e ? "11px" : "9px";
  return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>KOT - ${t.kot_number}</title>
        <style>
            body { ${d} }
            .kot-header { text-align: center; border-bottom: 1px solid #000; padding-bottom: 5px; margin-bottom: 8px; }
            .kot-title { font-size: ${r}; font-weight: bold; margin: 2px 0; }
            .kot-info { margin-bottom: 8px; font-size: ${s}; }
            .kot-info div { margin-bottom: 2px; }
            .items-table { width: 100%; border-collapse: collapse; font-size: ${l}; }
            .items-table th, .items-table td { border: none; padding: 1px 2px; text-align: left; }
            .items-table th { border-bottom: 1px solid #000; font-weight: bold; font-size: ${p}; }
            .kot-footer { margin-top: 8px; text-align: center; border-top: 1px solid #000; padding-top: 5px; font-size: ${m}; }
            @media print {
                body { margin: 0; padding: ${e ? "4px" : "2px"}; width: ${o}; }
                .kot-header { page-break-inside: avoid; }
            }
        </style>
    </head>
    <body>
        <div class="kot-header">
            <div class="kot-title">KITCHEN ORDER TICKET</div>
            <div>${t.kot_number}</div>
            <div>${t.datetime}</div>
        </div>
        
        <div class="kot-info">
            <div><strong>Type:</strong> ${t.order_type}</div>
            ${t.table_number ? `<div><strong>Table:</strong> ${t.table_number}</div>` : ""}
            <div><strong>Customer:</strong> ${t.customer_name}</div>
        </div>
        
        <table class="items-table">
            <thead>
                <tr>
                    <th style="width: 60%;">Item</th>
                    <th style="width: 40%; text-align: center;">Qty</th>
                </tr>
            </thead>
            <tbody>
                ${t.items.map((n) => `
                    <tr>
                        <td>${n.item_name}</td>
                        <td style="text-align: center;">${n.qty} ${n.uom}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
        
        <div class="kot-footer">
            <div><strong>Total Items: ${t.total_items}</strong></div>
            ${t.special_notes ? `<div style="margin-top: 5px; font-style: italic;">${t.special_notes}</div>` : ""}
        </div>
    </body>
    </html>
    `;
}
function b(t, i = {}) {
  const o = i.printWidth || t.print_width || "58mm", e = o === "80mm", d = e ? "font-family: 'Courier New', monospace; width: 80mm; margin: 0; padding: 8px; font-size: 12px; line-height: 1.3;" : "font-family: 'Courier New', monospace; width: 58mm; margin: 0; padding: 5px; font-size: 10px; line-height: 1.2;", r = e ? "14px" : "12px", s = e ? "11px" : "9px", l = e ? "11px" : "9px", p = e ? "10px" : "8px", m = e ? "11px" : "9px";
  return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Void KOT - ${t.kot_number}</title>
        <style>
            body { ${d} }
            .kot-header { text-align: center; border-bottom: 1px solid #000; padding-bottom: 5px; margin-bottom: 8px; }
            .kot-title { font-size: ${r}; font-weight: bold; color: #ff0000; margin: 2px 0; }
            .kot-info { margin-bottom: 8px; font-size: ${s}; }
            .kot-info div { margin-bottom: 2px; }
            .items-table { width: 100%; border-collapse: collapse; font-size: ${l}; }
            .items-table th, .items-table td { border: none; padding: 1px 2px; text-align: left; }
            .items-table th { border-bottom: 1px solid #000; font-weight: bold; font-size: ${p}; }
            .void-status { color: #ff0000; font-weight: bold; }
            .kot-footer { margin-top: 8px; text-align: center; border-top: 1px solid #000; padding-top: 5px; font-size: ${m}; }
            @media print {
                body { margin: 0; padding: ${e ? "4px" : "2px"}; width: ${o}; }
                .kot-header { page-break-inside: avoid; }
            }
        </style>
    </head>
    <body>
        <div class="kot-header">
            <div class="kot-title">*** VOID KOT ***</div>
            <div>${t.kot_number}</div>
            <div>${t.datetime}</div>
        </div>
        
        <div class="kot-info">
            <div><strong>Order #:</strong> ${t.order_number}</div>
            <div><strong>Type:</strong> ${t.order_type}</div>
            ${t.table_number ? `<div><strong>Table:</strong> ${t.table_number}</div>` : ""}
            <div><strong>Customer:</strong> ${t.customer_name}</div>
        </div>
        
        <table class="items-table">
            <thead>
                <tr>
                    <th style="width: 60%;">Item</th>
                    <th style="width: 40%; text-align: center;">Qty</th>
                </tr>
            </thead>
            <tbody>
                ${t.voided_items.map((n) => `
                    <tr>
                        <td>${n.item_name}</td>
                        <td style="text-align: center;" class="void-status">${n.qty} VOID</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
        
        <div class="kot-footer">
            <div><strong>Total Voided Items: ${t.total_voided_items}</strong></div>
            <div class="void-status">${t.special_notes}</div>
            <div>Reason: ${t.void_reason}</div>
        </div>
    </body>
    </html>
    `;
}
export {
  c as printKot,
  g as printVoidKot
};
