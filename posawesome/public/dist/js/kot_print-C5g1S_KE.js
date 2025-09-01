function r(t, o = {}) {
  const i = n(t, o), e = window.open("", "_blank");
  return e.document.write(i), e.document.close(), e.focus(), o.autoPrint !== !1 && (e.print(), setTimeout(() => {
    e.close();
  }, 1e3)), e;
}
function s(t, o = {}) {
  const i = d(t, o), e = window.open("", "_blank");
  return e.document.write(i), e.document.close(), e.focus(), o.autoPrint !== !1 && (e.print(), setTimeout(() => {
    e.close();
  }, 1e3)), e;
}
function n(t, o = {}) {
  return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>KOT - ${t.kot_number}</title>
        <style>
            body { font-family: 'Courier New', monospace; width: 58mm; margin: 0; padding: 5px; font-size: 10px; line-height: 1.2; }
            .kot-header { text-align: center; border-bottom: 1px solid #000; padding-bottom: 5px; margin-bottom: 8px; }
            .kot-title { font-size: 12px; font-weight: bold; margin: 2px 0; }
            .kot-info { margin-bottom: 8px; font-size: 9px; }
            .kot-info div { margin-bottom: 2px; }
            .items-table { width: 100%; border-collapse: collapse; font-size: 9px; }
            .items-table th, .items-table td { border: none; padding: 1px 2px; text-align: left; }
            .items-table th { border-bottom: 1px solid #000; font-weight: bold; font-size: 8px; }
            .kot-footer { margin-top: 8px; text-align: center; border-top: 1px solid #000; padding-top: 5px; font-size: 9px; }
            @media print {
                body { margin: 0; padding: 2px; width: 58mm; }
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
                ${t.items.map((i) => `
                    <tr>
                        <td>${i.item_name}</td>
                        <td style="text-align: center;">${i.qty} ${i.uom}</td>
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
function d(t, o = {}) {
  return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Void KOT - ${t.kot_number}</title>
        <style>
            body { font-family: 'Courier New', monospace; width: 58mm; margin: 0; padding: 5px; font-size: 10px; line-height: 1.2; }
            .kot-header { text-align: center; border-bottom: 1px solid #000; padding-bottom: 5px; margin-bottom: 8px; }
            .kot-title { font-size: 12px; font-weight: bold; color: #ff0000; margin: 2px 0; }
            .kot-info { margin-bottom: 8px; font-size: 9px; }
            .kot-info div { margin-bottom: 2px; }
            .items-table { width: 100%; border-collapse: collapse; font-size: 9px; }
            .items-table th, .items-table td { border: none; padding: 1px 2px; text-align: left; }
            .items-table th { border-bottom: 1px solid #000; font-weight: bold; font-size: 8px; }
            .void-status { color: #ff0000; font-weight: bold; }
            .kot-footer { margin-top: 8px; text-align: center; border-top: 1px solid #000; padding-top: 5px; font-size: 9px; }
            @media print {
                body { margin: 0; padding: 2px; width: 58mm; }
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
                ${t.voided_items.map((i) => `
                    <tr>
                        <td>${i.item_name}</td>
                        <td style="text-align: center;" class="void-status">${i.qty} VOID</td>
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
  r as printKot,
  s as printVoidKot
};
