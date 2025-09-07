// Kitchen Order Ticket (KOT) Print Utilities

export function printKot(kotData, options = {}) {
    const printContent = generateKotPrintHtml(kotData, options);
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(printContent);
    printWindow.document.close();
    printWindow.focus();
    
    // Auto-print if specified
    if (options.autoPrint !== false) {
        printWindow.print();
        
        // Close the print window after printing
        setTimeout(() => {
            printWindow.close();
        }, 1000);
    }
    
    return printWindow;
}

export function printVoidKot(voidKotData, options = {}) {
    const printContent = generateVoidKotPrintHtml(voidKotData, options);
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(printContent);
    printWindow.document.close();
    printWindow.focus();
    
    // Auto-print if specified
    if (options.autoPrint !== false) {
        printWindow.print();
        
        // Close the print window after printing
        setTimeout(() => {
            printWindow.close();
        }, 1000);
    }
    
    return printWindow;
}

// Legacy function name for backward compatibility
export function printKOTHTML(kotData, options = {}) {
    return printKot(kotData, options);
}

function generateKotPrintHtml(kotData, options = {}) {
    // Get print width from options or default to 58mm
    const printWidth = options.printWidth || kotData.print_width || '58mm';
    
    // Adjust font sizes and layout based on print width
    const isWideFormat = printWidth === '80mm';
    const bodyStyle = isWideFormat 
        ? `font-family: 'Courier New', monospace; width: 80mm; margin: 0; padding: 8px; font-size: 12px; line-height: 1.3;`
        : `font-family: 'Courier New', monospace; width: 58mm; margin: 0; padding: 5px; font-size: 10px; line-height: 1.2;`;
    
    const titleSize = isWideFormat ? '14px' : '12px';
    const infoSize = isWideFormat ? '11px' : '9px';
    const tableSize = isWideFormat ? '11px' : '9px';
    const headerSize = isWideFormat ? '10px' : '8px';
    const footerSize = isWideFormat ? '11px' : '9px';
    
    return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>KOT - ${kotData.kot_number}</title>
        <style>
            body { ${bodyStyle} }
            .kot-header { text-align: center; border-bottom: 1px solid #000; padding-bottom: 5px; margin-bottom: 8px; }
            .kot-title { font-size: ${titleSize}; font-weight: bold; margin: 2px 0; }
            .kot-info { margin-bottom: 8px; font-size: ${infoSize}; }
            .kot-info div { margin-bottom: 2px; }
            .items-table { width: 100%; border-collapse: collapse; font-size: ${tableSize}; }
            .items-table th, .items-table td { border: none; padding: 1px 2px; text-align: left; }
            .items-table th { border-bottom: 1px solid #000; font-weight: bold; font-size: ${headerSize}; }
            .kot-footer { margin-top: 8px; text-align: center; border-top: 1px solid #000; padding-top: 5px; font-size: ${footerSize}; }
            @media print {
                body { margin: 0; padding: ${isWideFormat ? '4px' : '2px'}; width: ${printWidth}; }
                .kot-header { page-break-inside: avoid; }
            }
        </style>
    </head>
    <body>
        <div class="kot-header">
            <div class="kot-title">KITCHEN ORDER TICKET</div>
            <div>${kotData.kot_number}</div>
            <div>${kotData.datetime}</div>
        </div>
        
        <div class="kot-info">
            <div><strong>Type:</strong> ${kotData.order_type}</div>
            ${kotData.table_number ? `<div><strong>Table:</strong> ${kotData.table_number}</div>` : ''}
            <div><strong>Customer:</strong> ${kotData.customer_name}</div>
        </div>
        
        <table class="items-table">
            <thead>
                <tr>
                    <th style="width: 60%;">Item</th>
                    <th style="width: 40%; text-align: center;">Qty</th>
                </tr>
            </thead>
            <tbody>
                ${kotData.items.map(item => `
                    <tr>
                        <td>${item.item_name}</td>
                        <td style="text-align: center;">${item.qty} ${item.uom}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        
        <div class="kot-footer">
            <div><strong>Total Items: ${kotData.total_items}</strong></div>
            ${kotData.special_notes ? `<div style="margin-top: 5px; font-style: italic;">${kotData.special_notes}</div>` : ''}
        </div>
    </body>
    </html>
    `;
}

function generateVoidKotPrintHtml(voidKotData, options = {}) {
    // Get print width from options or default to 58mm
    const printWidth = options.printWidth || voidKotData.print_width || '58mm';
    
    // Adjust font sizes and layout based on print width
    const isWideFormat = printWidth === '80mm';
    const bodyStyle = isWideFormat 
        ? `font-family: 'Courier New', monospace; width: 80mm; margin: 0; padding: 8px; font-size: 12px; line-height: 1.3;`
        : `font-family: 'Courier New', monospace; width: 58mm; margin: 0; padding: 5px; font-size: 10px; line-height: 1.2;`;
    
    const titleSize = isWideFormat ? '14px' : '12px';
    const infoSize = isWideFormat ? '11px' : '9px';
    const tableSize = isWideFormat ? '11px' : '9px';
    const headerSize = isWideFormat ? '10px' : '8px';
    const footerSize = isWideFormat ? '11px' : '9px';
    
    return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Void KOT - ${voidKotData.kot_number}</title>
        <style>
            body { ${bodyStyle} }
            .kot-header { text-align: center; border-bottom: 1px solid #000; padding-bottom: 5px; margin-bottom: 8px; }
            .kot-title { font-size: ${titleSize}; font-weight: bold; color: #ff0000; margin: 2px 0; }
            .kot-info { margin-bottom: 8px; font-size: ${infoSize}; }
            .kot-info div { margin-bottom: 2px; }
            .items-table { width: 100%; border-collapse: collapse; font-size: ${tableSize}; }
            .items-table th, .items-table td { border: none; padding: 1px 2px; text-align: left; }
            .items-table th { border-bottom: 1px solid #000; font-weight: bold; font-size: ${headerSize}; }
            .void-status { color: #ff0000; font-weight: bold; }
            .kot-footer { margin-top: 8px; text-align: center; border-top: 1px solid #000; padding-top: 5px; font-size: ${footerSize}; }
            @media print {
                body { margin: 0; padding: ${isWideFormat ? '4px' : '2px'}; width: ${printWidth}; }
                .kot-header { page-break-inside: avoid; }
            }
        </style>
    </head>
    <body>
        <div class="kot-header">
            <div class="kot-title">*** VOID KOT ***</div>
            <div>${voidKotData.kot_number}</div>
            <div>${voidKotData.datetime}</div>
        </div>
        
        <div class="kot-info">
            <div><strong>Order #:</strong> ${voidKotData.order_number}</div>
            <div><strong>Type:</strong> ${voidKotData.order_type}</div>
            ${voidKotData.table_number ? `<div><strong>Table:</strong> ${voidKotData.table_number}</div>` : ''}
            <div><strong>Customer:</strong> ${voidKotData.customer_name}</div>
        </div>
        
        <table class="items-table">
            <thead>
                <tr>
                    <th style="width: 60%;">Item</th>
                    <th style="width: 40%; text-align: center;">Qty</th>
                </tr>
            </thead>
            <tbody>
                ${voidKotData.voided_items.map(item => `
                    <tr>
                        <td>${item.item_name}</td>
                        <td style="text-align: center;" class="void-status">${item.qty} VOID</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        
        <div class="kot-footer">
            <div><strong>Total Voided Items: ${voidKotData.total_voided_items}</strong></div>
            <div class="void-status">${voidKotData.special_notes}</div>
            <div>Reason: ${voidKotData.void_reason}</div>
        </div>
    </body>
    </html>
    `;
}
