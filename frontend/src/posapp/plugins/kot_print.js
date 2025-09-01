/**
 * KOT (Kitchen Order Ticket) Print Module
 * Handles printing of kitchen order tickets for restaurant orders
 */

export function generateKOTHTML(kotData) {
	if (!kotData) return "";

	const itemsRows = (kotData.items || [])
		.map((item) => {
			const specialInstructions = item.special_instructions
				? `<br><small style="color: #666; font-style: italic;">${item.special_instructions}</small>`
				: "";
			return `
			<tr>
				<td style="border-bottom: 1px dashed #ccc; padding: 8px 2px; vertical-align: top;">
					<strong>${item.item_name}</strong>${specialInstructions}
				</td>
				<td style="border-bottom: 1px dashed #ccc; padding: 8px 2px; text-align: center; vertical-align: top;">
					<strong style="font-size: 14px;">${item.qty} ${item.uom}</strong>
				</td>
			</tr>`;
		})
		.join("");

	const tableInfo = kotData.table_number
		? `<p style="margin: 3px 0;"><strong>Table:</strong> ${kotData.table_number}</p>`
		: "";

	const notesSection = kotData.special_notes
		? `
		<div style="border: 1px solid #ccc; padding: 8px; margin: 10px 0; background: #f9f9f9;">
			<strong>Special Notes:</strong><br>
			${kotData.special_notes}
		</div>`
		: "";

	return `
	<!DOCTYPE html>
	<html>
	<head>
		<meta charset="utf-8">
		<title>KOT ${kotData.kot_number}</title>
		<style>
			@media print {
				body { margin: 0; }
				.no-print { display: none; }
			}
			body { 
				font-family: 'Courier New', monospace; 
				width: 300px; 
				margin: 0 auto; 
				padding: 15px; 
				font-size: 12px; 
				line-height: 1.4;
			}
			.header { 
				text-align: center; 
				border-bottom: 2px solid #000; 
				padding-bottom: 10px; 
				margin-bottom: 15px; 
			}
			.kot-title { 
				font-size: 18px; 
				font-weight: bold; 
				margin: 0 0 5px 0; 
				letter-spacing: 1px;
			}
			.kot-number {
				font-size: 14px;
				margin: 0;
				font-weight: normal;
			}
			.kot-info { 
				margin: 15px 0; 
			}
			.kot-info p { 
				margin: 3px 0; 
				font-size: 13px;
			}
			.items-table { 
				width: 100%; 
				border-collapse: collapse; 
				margin: 15px 0; 
			}
			.items-table th { 
				border-bottom: 2px solid #000; 
				padding: 8px 2px; 
				text-align: left; 
				font-size: 13px;
				font-weight: bold;
			}
			.items-table td { 
				padding: 8px 2px; 
				vertical-align: top; 
				font-size: 12px;
			}
			.footer { 
				border-top: 2px solid #000; 
				padding-top: 10px; 
				margin-top: 20px; 
				text-align: center; 
			}
			.dashed-line { 
				border-top: 1px dashed #000; 
				margin: 15px 0; 
			}
			.priority-high {
				background-color: #ffe6e6;
				border-left: 4px solid #ff4444;
			}
			.btn-print {
				background: #4CAF50;
				color: white;
				border: none;
				padding: 8px 16px;
				cursor: pointer;
				margin: 5px;
				border-radius: 4px;
			}
			.btn-close {
				background: #f44336;
				color: white;
				border: none;
				padding: 8px 16px;
				cursor: pointer;
				margin: 5px;
				border-radius: 4px;
			}
		</style>
	</head>
	<body>
		<div class="header">
			<h2 class="kot-title">🍳 KITCHEN ORDER TICKET</h2>
			<p class="kot-number">KOT #: ${kotData.kot_number}</p>
		</div>
		
		<div class="kot-info">
			<p><strong>Order Type:</strong> ${kotData.order_type}</p>
			${tableInfo}
			<p><strong>Customer:</strong> ${kotData.customer_name}</p>
			<p><strong>Date & Time:</strong> ${kotData.datetime}</p>
		</div>
		
		<div class="dashed-line"></div>
		
		<table class="items-table">
			<thead>
				<tr>
					<th style="width: 65%;">ITEM</th>
					<th style="width: 35%; text-align: center;">QUANTITY</th>
				</tr>
			</thead>
			<tbody>
				${itemsRows}
			</tbody>
		</table>
		
		<div class="dashed-line"></div>
		
		<div class="kot-info">
			<p><strong>Total Items:</strong> ${kotData.total_items}</p>
			${notesSection}
		</div>
		
		<div class="footer">
			<p><strong>*** FOR KITCHEN USE ONLY ***</strong></p>
			<p style="font-size: 11px;">Please prepare items as ordered</p>
			<p style="font-size: 10px; color: #666;">Printed on: ${new Date().toLocaleString()}</p>
		</div>
		
		<div class="no-print" style="text-align: center; margin-top: 20px;">
			<button class="btn-print" onclick="window.print()">🖨️ Print KOT</button>
			<button class="btn-close" onclick="window.close()">❌ Close</button>
		</div>
		
		<script>
			// Auto-print if called from silent print mode
			if (window.opener && window.opener.kotSilentPrint) {
				window.onload = function() {
					window.print();
					setTimeout(function() {
						window.close();
					}, 1000);
				};
			}
		</script>
	</body>
	</html>
	`;
}

/**
 * Print KOT using silent print method
 * @param {Object} kotData - The KOT data to print
 */
export function printKOTSilent(kotData) {
	const html = generateKOTHTML(kotData);
	const printWindow = window.open("", "_blank", "width=400,height=600,scrollbars=yes");
	printWindow.kotSilentPrint = true; // Flag for auto-print
	printWindow.document.write(html);
	printWindow.document.close();
	printWindow.focus();
}

/**
 * Print KOT with user control
 * @param {Object} kotData - The KOT data to print
 */
export function printKOTWithPreview(kotData) {
	const html = generateKOTHTML(kotData);
	const printWindow = window.open("", "_blank", "width=400,height=600,scrollbars=yes,resizable=yes");
	printWindow.document.write(html);
	printWindow.document.close();
	printWindow.focus();
	return printWindow;
}

/**
 * Print KOT directly from backend HTML response
 * @param {string} kotHTML - The generated KOT HTML from backend
 * @param {boolean} silentPrint - Whether to auto-print
 */
export function printKOTHTML(kotHTML, silentPrint = false) {
	const printWindow = window.open("", "_blank", "width=400,height=600,scrollbars=yes,resizable=yes");
	
	if (silentPrint) {
		printWindow.kotSilentPrint = true;
	}
	
	printWindow.document.write(kotHTML);
	printWindow.document.close();
	printWindow.focus();
	return printWindow;
}
