/* global __, frappe, flt */
import {
	isOffline,
	saveCustomerBalance,
	getCachedCustomerBalance,
	getCachedPriceListItems,
	getCustomerStorage,
	getOfflineCustomers,
	getTaxTemplate,
	getTaxInclusiveSetting,
} from "../../../offline/index.js";

// Import composables
import { useBatchSerial } from "../../composables/useBatchSerial.js";
import { useDiscounts } from "../../composables/useDiscounts.js";
import { useItemAddition } from "../../composables/useItemAddition.js";
import { useStockUtils } from "../../composables/useStockUtils.js";

const { setSerialNo, setBatchQty } = useBatchSerial();
const { updateDiscountAmount, calcPrices, calcItemPrice } = useDiscounts();
const { removeItem, addItem, getNewItem, clearInvoice } = useItemAddition();
const { calcUom, calcStockQty } = useStockUtils();

export default {
	remove_item(item) {
		return removeItem(item, this);
	},

	async add_item(item) {
		// Validate customer is selected first (mandatory for all modes)
		if (!this.customer) {
			this.eventBus.emit("show_message", {
				title: __("Please select a customer before adding items"),
				color: "error",
			});
			return false;
		}
		
		// Validate restaurant requirements before adding items
		if (this.pos_profile.posa_enable_restaurant_mode) {
			// Check if order type is selected (mandatory)
			if (!this.selected_order_type) {
				this.eventBus.emit("show_message", {
					title: __("Please select an Order Type before adding items"),
					color: "error",
				});
				return false;
			}
			
			// Check if table is selected for Dine In orders
			if (this.selected_order_type.requires_table && !this.selected_table) {
				this.eventBus.emit("show_message", {
					title: __("Please select a table for {0} orders", [this.selected_order_type.order_type_name]),
					color: "error",
				});
				return false;
			}
		}
		
		const res = await addItem(item, this);
		const target = this.items.find(
			(it) =>
				it.item_code === item.item_code &&
				it.uom === (item.uom || it.uom) &&
				(!it.batch_no || it.batch_no === item.batch_no),
		);
		if (target && this.fetch_available_qty) {
			this.fetch_available_qty(target);
		}
		return res;
	},

	// Create a new item object with default and calculated fields
	get_new_item(item) {
		return getNewItem(item, this);
	},

	// Reset all invoice fields to default/empty values
	clear_invoice() {
		const result = clearInvoice(this);
		
		// Clear restaurant selections when clearing invoice
		if (this.pos_profile && this.pos_profile.posa_enable_restaurant_mode) {
			this.clear_restaurant_selection();
			// Ensure invoice type remains "Order" in restaurant mode
			this.invoiceType = "Order";
			this.invoiceTypes = ["Order"];
		}
		
		return result;
	},

	// Fetch customer balance from backend or cache
	async fetch_customer_balance() {
		try {
			if (!this.customer) {
				this.customer_balance = 0;
				return;
			}

			// Check if offline and use cached balance
			if (isOffline()) {
				const cachedBalance = getCachedCustomerBalance(this.customer);
				if (cachedBalance !== null) {
					this.customer_balance = cachedBalance;
					return;
				} else {
					// No cached balance available in offline mode
					this.customer_balance = 0;
					this.eventBus.emit("show_message", {
						title: __("Customer balance unavailable offline"),
						text: __("Balance will be updated when connection is restored"),
						color: "warning",
					});
					return;
				}
			}

			// Online mode: fetch from server and cache the result
			const r = await frappe.call({
				method: "posawesome.posawesome.api.customer.get_customer_balance",
				args: { customer: this.customer },
			});

			const balance = r?.message?.balance || 0;
			this.customer_balance = balance;

			// Cache the balance for offline use
			saveCustomerBalance(this.customer, balance);
		} catch (error) {
			console.error("Error fetching balance:", error);

			// Try to use cached balance as fallback
			const cachedBalance = getCachedCustomerBalance(this.customer);
			if (cachedBalance !== null) {
				this.customer_balance = cachedBalance;
				this.eventBus.emit("show_message", {
					title: __("Using cached customer balance"),
					text: __("Could not fetch latest balance from server"),
					color: "warning",
				});
			} else {
				this.eventBus.emit("show_message", {
					title: __("Error fetching customer balance"),
					color: "error",
				});
				this.customer_balance = 0;
			}
		}
	},

	// Cancel the current invoice, optionally delete from backend
	async cancel_invoice() {
		const doc = this.get_invoice_doc();
		// Reset invoice type based on mode
		if (this.pos_profile && this.pos_profile.posa_enable_restaurant_mode) {
			this.invoiceType = "Order";
			this.invoiceTypes = ["Order"];
		} else {
			this.invoiceType = this.pos_profile.posa_default_sales_order ? "Order" : "Invoice";
			this.invoiceTypes = ["Invoice", "Order"];
		}
		this.posting_date = frappe.datetime.nowdate();
		var vm = this;
		if (doc.name && this.pos_profile.posa_allow_delete) {
			await frappe.call({
				method: "posawesome.posawesome.api.invoices.delete_invoice",
				args: { invoice: doc.name },
				async: true,
				callback: function (r) {
					if (r.message) {
						vm.eventBus.emit("show_message", {
							text: r.message,
							color: "warning",
						});
					}
				},
			});
		}
		this.clear_invoice();
		this.cancel_dialog = false;
	},

	// Load an invoice (or return invoice) from data, set all fields accordingly
	async load_invoice(data = {}) {
		console.log("load_invoice called with data:", {
			is_return: data.is_return,
			return_against: data.return_against,
			customer: data.customer,
			items_count: data.items ? data.items.length : 0,
		});

		this.clear_invoice();
		if (data.is_return) {
			console.log("Processing return invoice");
			// For return without invoice case, check if there's a return_against
			// Only set customer readonly if this is a return with reference to an invoice
			if (data.return_against) {
				console.log("Return has reference to invoice:", data.return_against);
				this.eventBus.emit("set_customer_readonly", true);
			} else {
				console.log("Return without invoice reference, customer can be selected");
				// Allow customer selection for returns without invoice
				this.eventBus.emit("set_customer_readonly", false);
			}
			this.invoiceType = "Return";
			this.invoiceTypes = ["Return"];
		}

		this.invoice_doc = data;
		this.items = data.items || [];
		this.packed_items = data.packed_items || [];
		console.log("Items set:", this.items.length, "items");

		if (data.is_return && data.return_against) {
			this.items.forEach((item) => {
				item.locked_price = true;
			});
			this.packed_items.forEach((pi) => {
				pi.locked_price = true;
			});
		}

		if (this.items.length > 0) {
			this.update_items_details(this.items);
			this.posa_offers = data.posa_offers || [];
			this.items.forEach((item) => {
				if (!item.posa_row_id) {
					item.posa_row_id = this.makeid(20);
				}
				if (item.batch_no) {
					this.set_batch_qty(item, item.batch_no);
				}
				if (!item.original_item_name) {
					item.original_item_name = item.item_name;
				}
			});
		} else {
			console.log("Warning: No items in return invoice");
		}

		if (this.packed_items.length > 0) {
			this.update_items_details(this.packed_items);
			this.packed_items.forEach((pi) => {
				if (!pi.posa_row_id) {
					pi.posa_row_id = this.makeid(20);
				}
			});
		}

		this.customer = data.customer;
		this.posting_date = this.formatDateForBackend(data.posting_date || frappe.datetime.nowdate());
		this.discount_amount = data.discount_amount;
		this.additional_discount_percentage = data.additional_discount_percentage;
		this.additional_discount = data.discount_amount;

		if (this.items.length > 0) {
			this.items.forEach((item) => {
				if (item.serial_no) {
					item.serial_no_selected = [];
					const serial_list = item.serial_no.split("\n");
					serial_list.forEach((element) => {
						if (element.length) {
							item.serial_no_selected.push(element);
						}
					});
					item.serial_no_selected_count = item.serial_no_selected.length;
				}
			});
		}

		if (data.is_return) {
			this.return_doc = data;
		} else {
			this.eventBus.emit("set_pos_coupons", data.posa_coupons);
		}

		console.log("load_invoice completed, invoice state:", {
			invoiceType: this.invoiceType,
			is_return: this.invoice_doc.is_return,
			items: this.items.length,
			customer: this.customer,
		});
	},

	// Save and clear the current invoice (draft logic)
	save_and_clear_invoice() {
		let old_invoice = null;
		const doc = this.get_invoice_doc();
		
		console.log("=== SAVE_AND_CLEAR_INVOICE DEBUG ===");
		console.log("doc from get_invoice_doc:", {
			name: doc.name,
			doctype: doc.doctype,
			docstatus: doc.docstatus
		});
		console.log("this.invoice_doc:", {
			name: this.invoice_doc?.name,
			doctype: this.invoice_doc?.doctype,
			docstatus: this.invoice_doc?.docstatus
		});
		console.log("Restaurant mode:", this.pos_profile.posa_enable_restaurant_mode);
		console.log("=== END SAVE_AND_CLEAR_INVOICE DEBUG ===");
		
		// In restaurant mode, validate order requirements and force Sales Order creation
		if (this.pos_profile.posa_enable_restaurant_mode) {
			// CRITICAL FIX: Check if this is a Sales Invoice by name format (more reliable than doctype)
			const isSalesInvoice = doc.name && doc.name.startsWith("ACC-SINV-");
			console.log("Is Sales Invoice by name:", isSalesInvoice);
			
			// If this is a Sales Invoice (converted from order), don't apply restaurant order validation
			if (doc.doctype === "Sales Invoice" || isSalesInvoice) {
				console.log("Processing Sales Invoice for payment, skipping restaurant order validation");
				// Allow normal invoice processing for payment
			} else {
				// Apply restaurant order validation for Sales Orders
				if (!this.selected_order_type) {
					this.eventBus.emit("show_message", {
						title: __("Please select an Order Type"),
						color: "error",
					});
					return false;
				}
				
				if (this.selected_order_type.requires_table && !this.selected_table) {
					this.eventBus.emit("show_message", {
						title: __("Please select a table for {0} orders", [this.selected_order_type.order_type_name]),
						color: "error",
					});
					return false;
				}
				
				// Force invoice type to be "Order" in restaurant mode to create Sales Order
				this.invoiceType = "Order";
				
				// CRITICAL FIX: If we're in restaurant mode and trying to update an order,
				// but this.invoice_doc references a Sales Invoice, we need to reload the original Sales Order
				if (doc.name && this.invoice_doc && this.invoice_doc.doctype === "Sales Invoice" && doc.name.startsWith("SAL-ORD-")) {
					console.error("CRITICAL ERROR: Attempting to update Sales Order but invoice_doc references Sales Invoice");
					console.log("invoice_doc doctype:", this.invoice_doc.doctype);
					console.log("doc name:", doc.name);
					
					this.eventBus.emit("show_message", {
						title: __("Order state error: Please reload the order from the orders list and try again."),
						color: "error",
					});
					return false;
				}
			}
		}
		
		if (doc.name) {
			// ENHANCED: Check document type by both doctype AND name format for more reliable detection
			const isSalesInvoiceByName = doc.name.startsWith("ACC-SINV-");
			const isSalesOrderByName = doc.name.startsWith("SAL-ORD-");
			
			console.log("Document type analysis:", {
				name: doc.name,
				doctype: doc.doctype,
				isSalesInvoiceByName,
				isSalesOrderByName
			});
			
			// Check document type and handle accordingly
			if (doc.doctype === "Sales Invoice" || isSalesInvoiceByName) {
				// For Sales Invoices (including those converted from restaurant orders), use regular invoice update process
				console.log("Processing Sales Invoice for payment:", {
					name: doc.name,
					doctype: doc.doctype,
					docstatus: doc.docstatus
				});
				old_invoice = this.update_invoice(doc);
			} else if (doc.docstatus === 1 && this.pos_profile.posa_enable_restaurant_mode && (doc.doctype === "Sales Order" || isSalesOrderByName)) {
				// For submitted Sales Orders in restaurant mode, use special handling
				console.log("Attempting to update submitted Sales Order with doc:", {
					name: doc.name,
					doctype: doc.doctype,
					docstatus: doc.docstatus,
					items_count: doc.items?.length || 0
				});
				old_invoice = this.update_submitted_order(doc);
			} else {
				// For other document types (draft Sales Orders, etc.), use regular update
				console.log("Using regular update for doc:", {
					name: doc.name,
					doctype: doc.doctype,
					docstatus: doc.docstatus
				});
				old_invoice = this.update_invoice(doc);
			}
		} else {
			if (doc.items.length) {
				// In restaurant mode, create restaurant order instead of regular invoice
				if (this.pos_profile.posa_enable_restaurant_mode) {
					old_invoice = this.create_restaurant_order(doc);
				} else {
					old_invoice = this.update_invoice(doc);
				}
			} else {
				this.eventBus.emit("show_message", {
					title: __("Nothing to save"),
					color: "error",
				});
			}
		}
		if (!old_invoice) {
			this.eventBus.emit("show_message", {
				title: __("Error saving the current order"),
				color: "error",
			});
		} else {
			this.clear_invoice();
			return old_invoice;
		}
	},

	// Start a new order (or return order) with provided data
	async new_order(data = {}) {
		let old_invoice = null;
		this.eventBus.emit("set_customer_readonly", false);
		this.expanded = [];
		this.posa_offers = [];
		this.eventBus.emit("set_pos_coupons", []);
		this.posa_coupons = [];
		this.return_doc = "";
		if (!data.name && !data.is_return) {
			this.items = [];
			this.customer = this.pos_profile.customer;
			this.invoice_doc = "";
			this.discount_amount = 0;
			this.additional_discount_percentage = 0;
			this.invoiceType = "Invoice";
			this.invoiceTypes = ["Invoice", "Order"];
			
			// Clear restaurant selections for new orders
			if (this.pos_profile && this.pos_profile.posa_enable_restaurant_mode) {
				this.clear_restaurant_selection();
			}
		} else {
			if (data.is_return) {
				// For return without invoice case, check if there's a return_against
				// Only set customer readonly if this is a return with reference to an invoice
				if (data.return_against) {
					this.eventBus.emit("set_customer_readonly", true);
				} else {
					// Allow customer selection for returns without invoice
					this.eventBus.emit("set_customer_readonly", false);
				}
				this.invoiceType = "Return";
				this.invoiceTypes = ["Return"];
			}
			this.invoice_doc = data;
			
			// CRITICAL FIX: In restaurant mode, validate document consistency
			if (this.pos_profile && this.pos_profile.posa_enable_restaurant_mode) {
				console.log("Loading document for editing - validating consistency");
				console.log("Document info:", {
					name: data.name,
					doctype: data.doctype,
					docstatus: data.docstatus
				});
				
				// If this claims to be a Sales Order but has inconsistent data, prevent editing
				if (data.name && data.name.startsWith("SAL-ORD-") && data.doctype !== "Sales Order") {
					console.error("CRITICAL ERROR: Document name suggests Sales Order but doctype is:", data.doctype);
					this.eventBus.emit("show_message", {
						title: __("Document type mismatch. Please reload from orders list."),
						color: "error",
					});
					return;
				}
			}
			
			this.items = data.items;
			this.update_items_details(this.items);
			this.posa_offers = data.posa_offers || [];
			
			// Load restaurant order data if available
			if (this.pos_profile && this.pos_profile.posa_enable_restaurant_mode) {
				// For restaurant mode, ensure we use Order type for Sales Orders
				if (data.doctype === "Sales Order") {
					this.invoiceType = "Order";
					this.invoiceTypes = ["Order"];
					console.log("Loading Sales Order for editing in restaurant mode:", data.name);
				}
				
				if (data.restaurant_order_type) {
					// Find the order type object
					const orderType = this.restaurant_order_types.find(t => t.name === data.restaurant_order_type);
					if (orderType) {
						this.selected_order_type = orderType;
					}
				}
				
				if (data.table_number) {
					// Find the table object
					const table = this.available_tables.find(t => t.table_number === data.table_number);
					if (table) {
						this.selected_table = table;
					}
				}
			}
			
			this.items.forEach((item) => {
				if (!item.posa_row_id) {
					item.posa_row_id = this.makeid(20);
				}
				if (item.batch_no) {
					this.set_batch_qty(item, item.batch_no);
				}
			});
			this.customer = data.customer;
			this.posting_date = this.formatDateForBackend(data.posting_date || frappe.datetime.nowdate());
			this.discount_amount = data.discount_amount;
			this.additional_discount_percentage = data.additional_discount_percentage;
			this.items.forEach((item) => {
				if (item.serial_no) {
					item.serial_no_selected = [];
					const serial_list = item.serial_no.split("\n");
					serial_list.forEach((element) => {
						if (element.length) {
							item.serial_no_selected.push(element);
						}
					});
					item.serial_no_selected_count = item.serial_no_selected.length;
				}
			});
		}
		return old_invoice;
	},

	// Build the invoice document object for backend submission
	get_invoice_doc() {
		let doc = {};
		if (this.invoice_doc.name) {
			doc = { ...this.invoice_doc };
			console.log("=== DEBUG: get_invoice_doc - starting with existing doc ===");
			console.log("Original this.invoice_doc:", {
				name: this.invoice_doc.name,
				doctype: this.invoice_doc.doctype,
				docstatus: this.invoice_doc.docstatus
			});
		}

		// Always set these fields first
		if (this.invoiceType === "Order" && this.pos_profile.posa_create_only_sales_order) {
			doc.doctype = "Sales Order";
		} else if (this.pos_profile.create_pos_invoice_instead_of_sales_invoice) {
			doc.doctype = "POS Invoice";
		} else {
			doc.doctype = "Sales Invoice";
		}
		
		// In restaurant mode, only force Sales Order doctype for new documents or actual Sales Orders
		// Don't force it for Sales Invoices created from restaurant orders (they should remain Sales Invoices)
		if (this.pos_profile.posa_enable_restaurant_mode) {
			// Only force Sales Order doctype if:
			// 1. This is a new document (no name), OR
			// 2. The existing document already has a Sales Order name format
			if (!doc.name || (doc.name && doc.name.startsWith('SAL-ORD-'))) {
				doc.doctype = "Sales Order";
				console.log("=== DEBUG: get_invoice_doc - forced doctype to Sales Order in restaurant mode ===");
			} else if (doc.name && doc.name.startsWith('ACC-SINV-')) {
				// This is a Sales Invoice created from a restaurant order - keep it as Sales Invoice
				doc.doctype = "Sales Invoice";
				console.log("=== DEBUG: get_invoice_doc - keeping Sales Invoice doctype for converted order ===");
			}
		}
		
		console.log("=== DEBUG: get_invoice_doc - final doc info ===");
		console.log("Final doc:", {
			name: doc.name,
			doctype: doc.doctype,
			docstatus: doc.docstatus,
			invoiceType: this.invoiceType,
			restaurant_mode: this.pos_profile.posa_enable_restaurant_mode
		});
		doc.is_pos = 1;
		doc.ignore_pricing_rule = 1;
		doc.company = doc.company || this.pos_profile.company;
		doc.pos_profile = doc.pos_profile || this.pos_profile.name;
		doc.posa_show_custom_name_marker_on_print = this.pos_profile.posa_show_custom_name_marker_on_print;

		// Currency related fields
		doc.currency = this.selected_currency || this.pos_profile.currency;
		doc.conversion_rate =
			(this.invoice_doc && this.invoice_doc.conversion_rate) || this.conversion_rate || 1;

		// Use actual price list currency if available
		doc.price_list_currency = this.price_list_currency || doc.currency;

		doc.plc_conversion_rate =
			(this.invoice_doc && this.invoice_doc.plc_conversion_rate) ||
			(doc.price_list_currency === doc.currency ? 1 : this.exchange_rate);

		// Other fields
		doc.campaign = doc.campaign || this.pos_profile.campaign;
		doc.selling_price_list = this.pos_profile.selling_price_list;
		doc.naming_series = doc.naming_series || this.pos_profile.naming_series;
		doc.customer = this.customer;

		// Determine if this is a return invoice
		const isReturn = this.isReturnInvoice;
		doc.is_return = isReturn ? 1 : 0;

		// Calculate amounts in selected currency
		const items = this.get_invoice_items();
		doc.items = items;
		doc.packed_items = (this.packed_items || []).map((pi) => ({
			parent_item: pi.parent_item,
			item_code: pi.item_code,
			item_name: pi.item_name,
			qty: flt(pi.qty),
			uom: pi.uom,
			warehouse: pi.warehouse,
			batch_no: pi.batch_no,
			serial_no: pi.serial_no,
			rate: flt(pi.rate),
		}));

		// Calculate totals in selected currency ensuring negative values for returns
		let total = this.Total;
		if (isReturn && total > 0) total = -Math.abs(total);

		doc.total = total;
		doc.net_total = total; // Will adjust later if taxes are inclusive
		doc.base_total = total * (this.exchange_rate || 1);
		doc.base_net_total = total * (this.exchange_rate || 1);

		// Apply discounts with correct sign for returns
		let discountAmount = flt(this.additional_discount);
		if (isReturn && discountAmount > 0) discountAmount = -Math.abs(discountAmount);

		doc.discount_amount = discountAmount;
		doc.base_discount_amount = discountAmount * (this.exchange_rate || 1);

		let discountPercentage = flt(this.additional_discount_percentage);
		if (isReturn && discountPercentage > 0) discountPercentage = -Math.abs(discountPercentage);

		doc.additional_discount_percentage = discountPercentage;

		// Calculate grand total with correct sign for returns
		let grandTotal = this.subtotal;

		// Prepare taxes array
		doc.taxes = [];
		if (this.invoice_doc && this.invoice_doc.taxes) {
			let totalTax = 0;
			this.invoice_doc.taxes.forEach((tax) => {
				if (tax.tax_amount) {
					grandTotal += flt(tax.tax_amount);
					totalTax += flt(tax.tax_amount);
				}
				doc.taxes.push({
					account_head: tax.account_head,
					charge_type: tax.charge_type || "On Net Total",
					description: tax.description,
					rate: tax.rate,
					included_in_print_rate: tax.included_in_print_rate || 0,
					tax_amount: tax.tax_amount,
					total: tax.total,
					base_tax_amount: tax.tax_amount * (this.exchange_rate || 1),
					base_total: tax.total * (this.exchange_rate || 1),
				});
			});
			doc.total_taxes_and_charges = totalTax;
		} else if (isOffline()) {
			const tmpl = getTaxTemplate(this.pos_profile.taxes_and_charges);
			if (tmpl && Array.isArray(tmpl.taxes)) {
				const inclusive = getTaxInclusiveSetting();
				let runningTotal = grandTotal;
				let totalTax = 0;
				tmpl.taxes.forEach((row) => {
					let tax_amount = 0;
					if (row.charge_type === "Actual") {
						tax_amount = flt(row.tax_amount || 0);
					} else if (inclusive) {
						tax_amount = flt((doc.total * flt(row.rate)) / 100);
					} else {
						tax_amount = flt((doc.net_total * flt(row.rate)) / 100);
					}
					if (!inclusive) {
						runningTotal += tax_amount;
					}
					totalTax += tax_amount;
					doc.taxes.push({
						account_head: row.account_head,
						charge_type: row.charge_type || "On Net Total",
						description: row.description,
						rate: row.rate,
						included_in_print_rate: row.charge_type === "Actual" ? 0 : inclusive ? 1 : 0,
						tax_amount: tax_amount,
						total: runningTotal,
						base_tax_amount: tax_amount * (this.exchange_rate || 1),
						base_total: runningTotal * (this.exchange_rate || 1),
					});
				});
				if (inclusive) {
					doc.net_total = doc.total - totalTax;
					doc.base_net_total = doc.net_total * (this.exchange_rate || 1);
					grandTotal = doc.total;
				} else {
					grandTotal = runningTotal;
				}
				doc.total_taxes_and_charges = totalTax;
			}
		}

		if (isReturn && grandTotal > 0) grandTotal = -Math.abs(grandTotal);

		doc.grand_total = grandTotal;
		doc.base_grand_total = grandTotal * (this.exchange_rate || 1);

		// Apply rounding to get rounded total unless disabled in POS Profile
		if (this.pos_profile.disable_rounded_total) {
			doc.rounded_total = flt(grandTotal, this.currency_precision);
			doc.base_rounded_total = flt(doc.base_grand_total, this.currency_precision);
		} else {
			doc.rounded_total = this.roundAmount(grandTotal);
			doc.base_rounded_total = this.roundAmount(doc.base_grand_total);
		}

		// Add POS specific fields
		doc.posa_pos_opening_shift = this.pos_opening_shift.name;
		doc.payments = this.get_payments();

		// Handle return specific fields
		if (isReturn) {
			if (this.invoice_doc.return_against) {
				doc.return_against = this.invoice_doc.return_against;
			}
			// For restaurant mode, disable stock update to avoid validation issues
			doc.update_stock = this.pos_profile.posa_enable_restaurant_mode ? 0 : 1;

			// Double-check all values are negative
			if (doc.grand_total > 0) doc.grand_total = -Math.abs(doc.grand_total);
			if (doc.base_grand_total > 0) doc.base_grand_total = -Math.abs(doc.base_grand_total);
			if (doc.rounded_total > 0) doc.rounded_total = -Math.abs(doc.rounded_total);
			if (doc.base_rounded_total > 0) doc.base_rounded_total = -Math.abs(doc.base_rounded_total);
			if (doc.total > 0) doc.total = -Math.abs(doc.total);
			if (doc.base_total > 0) doc.base_total = -Math.abs(doc.base_total);
			if (doc.net_total > 0) doc.net_total = -Math.abs(doc.net_total);
			if (doc.base_net_total > 0) doc.base_net_total = -Math.abs(doc.base_net_total);

			// Ensure payments have negative amounts
			if (doc.payments && doc.payments.length) {
				doc.payments.forEach((payment) => {
					if (payment.amount > 0) payment.amount = -Math.abs(payment.amount);
					if (payment.base_amount > 0) payment.base_amount = -Math.abs(payment.base_amount);
				});
			}
		}

		// Add offer details
		doc.posa_offers = this.posa_offers;
		doc.posa_coupons = this.posa_coupons;
		doc.posa_delivery_charges = this.selected_delivery_charge?.name || null;
		doc.posa_delivery_charges_rate = this.delivery_charges_rate || 0;
		doc.posting_date = this.formatDateForBackend(this.posting_date_display);

		// Add flags to ensure proper rate handling
		doc.ignore_pricing_rule = 1;

		// Preserve the real price list currency
		doc.price_list_currency = this.price_list_currency || doc.currency;
		doc.plc_conversion_rate = this.exchange_rate || doc.conversion_rate;
		doc.ignore_default_fields = 1; // Add this to prevent default field updates

		// Add custom fields to track offer rates
		doc.posa_is_offer_applied = this.posa_offers.length > 0 ? 1 : 0;

		// Calculate base amounts using the exchange rate
		const baseCurrency = this.price_list_currency || this.pos_profile.currency;
		if (this.selected_currency !== baseCurrency) {
			// For returns, we need to ensure negative values
			const multiplier = isReturn ? -1 : 1;

			// Convert amounts back to the base currency
			doc.base_total = (total / this.exchange_rate) * multiplier;
			doc.base_net_total = (total / this.exchange_rate) * multiplier;
			doc.base_discount_amount = (discountAmount / this.exchange_rate) * multiplier;
			doc.base_grand_total = (grandTotal / this.exchange_rate) * multiplier;
			doc.base_rounded_total = (grandTotal / this.exchange_rate) * multiplier;
		} else {
			// Same currency, just ensure negative values for returns
			const multiplier = isReturn ? -1 : 1;
			// When in base currency, the base amounts are the same as the regular amounts
			doc.base_total = total * multiplier;
			doc.base_net_total = total * multiplier;
			doc.base_discount_amount = discountAmount * multiplier;
			doc.base_grand_total = grandTotal * multiplier;
			doc.base_rounded_total = grandTotal * multiplier;
		}

		// Ensure payments have correct base amounts
		if (doc.payments && doc.payments.length) {
			doc.payments.forEach((payment) => {
				if (this.selected_currency !== baseCurrency) {
					// Convert payment amount to base currency
					payment.base_amount = payment.amount / this.exchange_rate;
				} else {
					payment.base_amount = payment.amount;
				}

				// For returns, ensure negative values
				if (isReturn) {
					payment.amount = -Math.abs(payment.amount);
					payment.base_amount = -Math.abs(payment.base_amount);
				}
			});
		}

		// Add restaurant-specific fields if restaurant mode is enabled
		if (this.pos_profile.posa_enable_restaurant_mode) {
			if (this.selected_order_type) {
				doc.restaurant_order_type = this.selected_order_type.name;
			}
			
			if (this.selected_table) {
				doc.table_number = this.selected_table.table_number;
			}
			
			if (this.selected_order_type && this.selected_order_type.default_preparation_time) {
				doc.expected_preparation_time = this.selected_order_type.default_preparation_time;
			}
		}

		return doc;
	},

	// Get invoice doc from order doc (for sales order to invoice conversion)
	async get_invoice_from_order_doc() {
		let doc = {};
		if (this.invoice_doc.doctype == "Sales Order") {
			await frappe.call({
				method: "posawesome.posawesome.api.invoices.create_sales_invoice_from_order",
				args: {
					sales_order: this.invoice_doc.name,
				},
				// async: false,
				callback: function (r) {
					if (r.message) {
						doc = r.message;
					}
				},
			});
		} else {
			doc = this.invoice_doc;
		}
		const Items = [];
		const updatedItemsData = this.get_invoice_items();
		doc.items.forEach((item) => {
			const updatedData = updatedItemsData.find(
				(updatedItem) => updatedItem.item_code === item.item_code,
			);
			if (updatedData) {
				item.item_code = updatedData.item_code;
				item.posa_row_id = updatedData.posa_row_id;
				item.posa_offers = updatedData.posa_offers;
				item.posa_offer_applied = updatedData.posa_offer_applied;
				item.posa_is_offer = updatedData.posa_is_offer;
				item.posa_is_replace = updatedData.posa_is_replace;
				item.is_free_item = updatedData.is_free_item;
				item.qty = flt(updatedData.qty);
				item.rate = flt(updatedData.rate);
				item.uom = updatedData.uom;
				item.amount = flt(updatedData.qty) * flt(updatedData.rate);
				item.conversion_factor = updatedData.conversion_factor;
				item.serial_no = updatedData.serial_no;
				item.discount_percentage = flt(updatedData.discount_percentage);
				item.discount_amount = flt(updatedData.discount_amount);
				item.batch_no = updatedData.batch_no;
				item.posa_notes = updatedData.posa_notes;
				item.posa_delivery_date = this.formatDateForDisplay(updatedData.posa_delivery_date);
				item.price_list_rate = updatedData.price_list_rate;
				Items.push(item);
			}
		});

		doc.items = Items;
		const newItems = [...doc.items];
		const existingItemCodes = new Set(newItems.map((item) => item.item_code));
		updatedItemsData.forEach((updatedItem) => {
			if (!existingItemCodes.has(updatedItem.item_code)) {
				newItems.push(updatedItem);
			}
		});
		doc.items = newItems;
		// For restaurant mode, disable stock update to avoid validation issues
		doc.update_stock = this.pos_profile.posa_enable_restaurant_mode ? 0 : 1;
		doc.is_pos = 1;
		doc.payments = this.get_payments();
		return doc;
	},

	// Prepare items array for invoice doc
	get_invoice_items() {
		const items_list = [];
		const isReturn = this.isReturnInvoice;
		const usesPosInvoice = this.pos_profile.create_pos_invoice_instead_of_sales_invoice;

		this.items.forEach((item) => {
			const new_item = {
				item_code: item.item_code,
				// Retain the item name for offline invoices
				// Fallback to item_code if item_name is not available
				item_name: item.item_name || item.item_code,
				name_overridden: item.name_overridden ? 1 : 0,
				posa_row_id: item.posa_row_id,
				posa_offers: item.posa_offers,
				posa_offer_applied: item.posa_offer_applied,
				posa_is_offer: item.posa_is_offer,
				posa_is_replace: item.posa_is_replace,
				is_free_item: item.is_free_item,
				qty: flt(item.qty),
				uom: item.uom,
				conversion_factor: item.conversion_factor,
				serial_no: item.serial_no,
				// Link to original invoice item when doing returns
				// Needed for backend validation that the item exists in
				// the referenced Sales or POS Invoice
				...(item.sales_invoice_item && { sales_invoice_item: item.sales_invoice_item }),
				...(item.pos_invoice_item && { pos_invoice_item: item.pos_invoice_item }),
				discount_percentage: flt(item.discount_percentage),
				batch_no: item.batch_no,
				posa_notes: item.posa_notes,
				posa_delivery_date: this.formatDateForBackend(item.posa_delivery_date),
			};
			if (isReturn) {
				const refField = usesPosInvoice ? "pos_invoice_item" : "sales_invoice_item";
				if (!new_item[refField] && item.name) {
					new_item[refField] = item.name;
				}
			}

			// Handle currency conversion for rates and amounts
			const baseCurrency = this.price_list_currency || this.pos_profile.currency;
			if (this.selected_currency !== baseCurrency) {
				// If exchange rate is 300 PKR = 1 USD
				// item.rate is in USD (e.g. 10 USD)
				// base_rate should be in PKR (e.g. 3000 PKR)
				new_item.rate = flt(item.rate); // Keep rate in USD

				// Use pre-stored base_rate if available, otherwise calculate
				new_item.base_rate = item.base_rate || flt(item.rate / this.exchange_rate);

				new_item.price_list_rate = flt(item.price_list_rate); // Keep price list rate in USD
				new_item.base_price_list_rate =
					item.base_price_list_rate || flt(item.price_list_rate / this.exchange_rate);

				// Calculate amounts
				new_item.amount = flt(item.qty) * new_item.rate; // Amount in USD
				new_item.base_amount = new_item.amount / this.exchange_rate; // Convert to base currency

				// Handle discount amount
				new_item.discount_amount = flt(item.discount_amount); // Keep discount in USD
				new_item.base_discount_amount =
					item.base_discount_amount || flt(item.discount_amount / this.exchange_rate);
			} else {
				// Same currency (base currency), make sure we use base rates if available
				new_item.rate = flt(item.rate);
				new_item.base_rate = item.base_rate || flt(item.rate);
				new_item.price_list_rate = flt(item.price_list_rate);
				new_item.base_price_list_rate = item.base_price_list_rate || flt(item.price_list_rate);
				new_item.amount = flt(item.qty) * new_item.rate;
				new_item.base_amount = new_item.amount;
				new_item.discount_amount = flt(item.discount_amount);
				new_item.base_discount_amount = item.base_discount_amount || flt(item.discount_amount);
			}

			// For returns, ensure all amounts are negative
			if (isReturn) {
				new_item.qty = -Math.abs(new_item.qty);
				new_item.amount = -Math.abs(new_item.amount);
				new_item.base_amount = -Math.abs(new_item.base_amount);
				new_item.discount_amount = -Math.abs(new_item.discount_amount);
				new_item.base_discount_amount = -Math.abs(new_item.base_discount_amount);
			}

			items_list.push(new_item);
		});

		return items_list;
	},

	// Prepare items array for order doc
	get_order_items() {
		const items_list = [];
		this.items.forEach((item) => {
			const new_item = {
				item_code: item.item_code,
				// Retain item name to show on offline order documents
				// Use item_code if item_name is missing
				item_name: item.item_name || item.item_code,
				name_overridden: item.name_overridden ? 1 : 0,
				posa_row_id: item.posa_row_id,
				posa_offers: item.posa_offers,
				posa_offer_applied: item.posa_offer_applied,
				posa_is_offer: item.posa_is_offer,
				posa_is_replace: item.posa_is_replace,
				is_free_item: item.is_free_item,
				qty: flt(item.qty),
				rate: flt(item.rate),
				uom: item.uom,
				amount: flt(item.qty) * flt(item.rate),
				conversion_factor: item.conversion_factor,
				serial_no: item.serial_no,
				discount_percentage: flt(item.discount_percentage),
				discount_amount: flt(item.discount_amount),
				batch_no: item.batch_no,
				posa_notes: item.posa_notes,
				posa_delivery_date: item.posa_delivery_date,
				price_list_rate: item.price_list_rate,
			};
			items_list.push(new_item);
		});

		return items_list;
	},

	// Prepare payments array for invoice doc
	get_payments() {
		const payments = [];
		// Use this.subtotal which is already in selected currency and includes all calculations
		const total_amount = this.subtotal;
		let remaining_amount = total_amount;

		this.pos_profile.payments.forEach((payment, index) => {
			// For the first payment method, assign the full remaining amount
			const payment_amount = index === 0 ? remaining_amount : payment.amount || 0;

			// For return invoices, ensure payment amounts are negative
			const adjusted_amount = this.isReturnInvoice ? -Math.abs(payment_amount) : payment_amount;

			// Handle currency conversion
			// If selected_currency is USD and base is PKR:
			// amount is in USD (e.g. 10 USD)
			// base_amount should be in PKR (e.g. 3000 PKR)
			// So multiply by exchange rate to get base_amount
			const baseCurrency = this.price_list_currency || this.pos_profile.currency;
			const base_amount =
				this.selected_currency !== baseCurrency
					? this.flt(adjusted_amount / (this.exchange_rate || 1), this.currency_precision)
					: adjusted_amount;

			payments.push({
				amount: adjusted_amount, // Keep in selected currency (e.g. USD)
				base_amount: base_amount, // Convert to base currency (e.g. PKR)
				mode_of_payment: payment.mode_of_payment,
				default: payment.default,
				account: payment.account || "",
				type: payment.type || "Cash",
				currency: this.selected_currency || this.pos_profile.currency,
				conversion_rate: this.conversion_rate || 1,
			});

			remaining_amount -= payment_amount;
		});

		console.log("Generated payments:", {
			currency: this.selected_currency,
			exchange_rate: this.exchange_rate,
			payments: payments.map((p) => ({
				mode: p.mode_of_payment,
				amount: p.amount,
				base_amount: p.base_amount,
			})),
		});

		return payments;
	},

	// Convert amount to selected currency
	convert_amount(amount) {
		const baseCurrency = this.price_list_currency || this.pos_profile.currency;
		if (this.selected_currency === baseCurrency) {
			return amount;
		}
		return this.flt(amount * this.exchange_rate, this.currency_precision);
	},

	// Update invoice in backend
	update_invoice(doc) {
		var vm = this;
		if (isOffline()) {
			// When offline, simply merge the passed doc with the current invoice_doc
			// to allow offline invoice creation without server calls
			vm.invoice_doc = Object.assign({}, vm.invoice_doc || {}, doc);
			return vm.invoice_doc;
		}
		frappe.call({
			method:
				doc.doctype === "Sales Order" && this.pos_profile.posa_create_only_sales_order
					? "posawesome.posawesome.api.sales_orders.update_sales_order"
					: "posawesome.posawesome.api.invoices.update_invoice",
			args: {
				data: doc,
			},
			async: false,
			callback: function (r) {
				if (r.message) {
					vm.invoice_doc = r.message;
					if (r.message.exchange_rate_date) {
						vm.exchange_rate_date = r.message.exchange_rate_date;
						const posting_backend = vm.formatDateForBackend(vm.posting_date_display);
						if (posting_backend !== vm.exchange_rate_date) {
							vm.eventBus.emit("show_message", {
								title: __(
									"Exchange rate date " +
										vm.exchange_rate_date +
										" differs from posting date " +
										posting_backend,
								),
								color: "warning",
							});
						}
					}
				}
			},
		});
		return this.invoice_doc;
	},

	// Update invoice from order in backend
	update_invoice_from_order(doc) {
		var vm = this;
		if (isOffline()) {
			// Offline mode - merge doc locally without server update
			vm.invoice_doc = Object.assign({}, vm.invoice_doc || {}, doc);
			return vm.invoice_doc;
		}
		frappe.call({
			method: "posawesome.posawesome.api.invoices.update_invoice_from_order",
			args: {
				data: doc,
			},
			async: false,
			callback: function (r) {
				if (r.message) {
					vm.invoice_doc = r.message;
					if (r.message.exchange_rate_date) {
						vm.exchange_rate_date = r.message.exchange_rate_date;
						const posting_backend = vm.formatDateForBackend(vm.posting_date_display);
						if (posting_backend !== vm.exchange_rate_date) {
							vm.eventBus.emit("show_message", {
								title: __(
									"Exchange rate date " +
										vm.exchange_rate_date +
										" differs from posting date " +
										posting_backend,
								),
								color: "warning",
							});
						}
					}
				}
			},
		});
		return this.invoice_doc;
	},

	// Update submitted restaurant order with new items
	async update_submitted_order(doc) {
		var vm = this;
		if (isOffline()) {
			// Offline mode - merge doc locally without server update
			vm.invoice_doc = Object.assign({}, vm.invoice_doc || {}, doc);
			return vm.invoice_doc;
		}
		
		try {
			// Debug: Log the complete state before the update
			console.log("=== DEBUG: update_submitted_order called ===");
			console.log("doc parameter:", JSON.stringify({
				name: doc.name,
				doctype: doc.doctype,
				docstatus: doc.docstatus,
				items_count: doc.items?.length || 0,
				is_return: doc.is_return,
			}, null, 2));
			console.log("this.invoice_doc:", JSON.stringify({
				name: this.invoice_doc?.name,
				doctype: this.invoice_doc?.doctype,
				docstatus: this.invoice_doc?.docstatus,
			}, null, 2));
			console.log("this.invoiceType:", this.invoiceType);
			console.log("this.invoiceTypes:", this.invoiceTypes);
			
			// Ensure we're working with a Sales Order
			console.log("Updating order with doc:", {
				name: doc.name,
				doctype: doc.doctype,
				items_count: doc.items?.length || 0
			});
			
			// Check if this is actually a Sales Order
			if (doc.doctype !== "Sales Order") {
				console.error("Expected Sales Order but got:", doc.doctype);
				vm.eventBus.emit("show_message", {
					title: __("Invalid document type for order update. Expected Sales Order, got {0}", [doc.doctype]),
					color: "error",
				});
				return false;
			}
			
			// Validate order name format
			if (!doc.name || !doc.name.startsWith('SAL-ORD-')) {
				console.error("Invalid Sales Order name format:", doc.name);
				vm.eventBus.emit("show_message", {
					title: __("Invalid Sales Order name format: {0}", [doc.name || 'undefined']),
					color: "error",
				});
				return false;
			}
			
			const r = await frappe.call({
				method: "posawesome.posawesome.api.restaurant_orders.update_submitted_order_items",
				args: {
					order_name: doc.name,
					items_data: doc.items,
				},
			});

			if (r.message) {
				vm.invoice_doc = r.message;
				// Ensure the updated document maintains the correct doctype
				vm.invoice_doc.doctype = "Sales Order";
				console.log("Order updated successfully:", vm.invoice_doc.name);
				vm.eventBus.emit("show_message", {
					title: __("Order {0} updated successfully", [r.message.name]),
					color: "success",
				});
			}
			
			return vm.invoice_doc;
		} catch (error) {
			console.error("Error updating submitted order:", error);
			
			// Handle specific error cases with more detailed messages
			if (error.message && error.message.includes("not found")) {
				vm.eventBus.emit("show_message", {
					title: __("Sales Order {0} not found. It may have been deleted or converted to an invoice.", [doc.name]),
					color: "error",
				});
			} else if (error.message && error.message.includes("Sales Invoice")) {
				vm.eventBus.emit("show_message", {
					title: __("Error: Attempting to update a Sales Invoice as Sales Order. Order {0} may have been converted.", [doc.name]),
					color: "error",
				});
			} else {
				vm.eventBus.emit("show_message", {
					title: __("Error updating order: {0}", [error.message || "Unknown error"]),
					color: "error",
				});
			}
			return false;
		}
	},

	// Create restaurant order
	create_restaurant_order(doc) {
		var vm = this;
		if (isOffline()) {
			// Offline mode - merge doc locally without server update
			vm.invoice_doc = Object.assign({}, vm.invoice_doc || {}, doc);
			return vm.invoice_doc;
		}
		
		frappe.call({
			method: "posawesome.posawesome.api.restaurant_orders.create_restaurant_order",
			args: {
				order_data: doc,
			},
			async: false,
			callback: async function (r) {
				if (r.message) {
					// Handle different response formats
					let orderDoc;
					let kotData = null;
					let autoKot = false;

					if (r.message.sales_order) {
						// Response includes KOT data
						orderDoc = r.message.sales_order;
						kotData = r.message.kot_data;
						autoKot = r.message.auto_print_kot;
					} else {
						// Simple response format
						orderDoc = r.message;
					}

					vm.invoice_doc = orderDoc;
					vm.eventBus.emit("show_message", {
						title: __("Restaurant order {0} created successfully", [orderDoc.name]),
						color: "success",
					});

					// Handle KOT printing if data is available
					if (kotData && autoKot) {
						// Auto-print KOT
						try {
							const { printKot } = await import('../../plugins/kot_print.js');
							await printKot(kotData);
						} catch (error) {
							console.error("Error auto-printing KOT:", error);
						}
					} else if (kotData) {
						// Ask user if they want to print KOT
						const printKot = await new Promise((resolve) => {
							frappe.confirm(
								__("Order created successfully. Print KOT for kitchen?"),
								() => resolve(true),
								() => resolve(false)
							);
						});

						if (printKot) {
							try {
								const { printKot: printKotFn } = await import('../../plugins/kot_print.js');
								await printKotFn(kotData);
							} catch (error) {
								console.error("Error printing KOT:", error);
								vm.eventBus.emit("show_message", {
									title: __("Error printing KOT"),
									color: "error",
								});
							}
						}
					}
				} else {
					vm.eventBus.emit("show_message", {
						title: __("Error creating restaurant order"),
						color: "error",
					});
				}
			},
		});
		return this.invoice_doc;
	},

	// Process and save invoice (handles update or create)
	process_invoice() {
		const doc = this.get_invoice_doc();
		try {
			const updated_doc = this.update_invoice(doc);
			if (updated_doc && updated_doc.posting_date) {
				this.posting_date = this.formatDateForBackend(updated_doc.posting_date);
			}
			return updated_doc;
		} catch (error) {
			console.error("Error in process_invoice:", error);
			this.eventBus.emit("show_message", {
				title: __(error.message || "Error processing invoice"),
				color: "error",
			});
			return false;
		}
	},

	// Update invoice while preserving Sales Order references
	update_invoice_preserve_so_refs(invoice_doc) {
		try {
			console.log("Updating invoice while preserving Sales Order references");
			
			// Store the original Sales Order references from the invoice items
			const original_so_refs = {};
			if (invoice_doc.items) {
				invoice_doc.items.forEach((item, index) => {
					original_so_refs[index] = {
						sales_order: item.sales_order,
						so_detail: item.so_detail
					};
				});
			}
			
			// Update the invoice with current data
			const updated_doc = this.update_invoice(invoice_doc);
			
			// Restore the Sales Order references
			if (updated_doc && updated_doc.items && Object.keys(original_so_refs).length > 0) {
				updated_doc.items.forEach((item, index) => {
					if (original_so_refs[index]) {
						item.sales_order = original_so_refs[index].sales_order;
						item.so_detail = original_so_refs[index].so_detail;
					}
				});
				console.log("Restored Sales Order references in updated invoice");
			}
			
			return updated_doc;
		} catch (error) {
			console.error("Error updating invoice with SO refs preservation:", error);
			return invoice_doc; // Return original if update fails
		}
	},

	// Process and save invoice from order
	async process_invoice_from_order() {
		const doc = await this.get_invoice_from_order_doc();
		var up_invoice;
		if (doc.name) {
			up_invoice = await this.update_invoice_from_order(doc);
			return up_invoice;
		} else {
			return this.update_invoice_from_order(doc);
		}
	},

	// Show payment dialog after validation and processing
	async show_payment() {
		try {
			console.log("Starting show_payment process");
			console.log("Invoice state before payment:", {
				invoiceType: this.invoiceType,
				is_return: this.invoice_doc ? this.invoice_doc.is_return : false,
				items_count: this.items.length,
				customer: this.customer,
				invoice_doc_name: this.invoice_doc ? this.invoice_doc.name : null,
				invoice_doc_doctype: this.invoice_doc ? this.invoice_doc.doctype : null,
			});

			if (!this.customer) {
				console.log("Customer validation failed");
				this.eventBus.emit("show_message", {
					title: __(`Select a customer`),
					color: "error",
				});
				return;
			}

			if (!this.items.length) {
				console.log("Items validation failed - no items");
				this.eventBus.emit("show_message", {
					title: __(`Select items to sell`),
					color: "error",
				});
				return;
			}

			console.log("Basic validations passed, proceeding to main validation");
			const isValid = this.validate();
			console.log("Main validation result:", isValid);

			if (!isValid) {
				console.log("Main validation failed");
				return;
			}

			let invoice_doc;
			
			console.log("Determining processing path:", {
				has_invoice_doc: !!this.invoice_doc,
				invoice_doc_name: this.invoice_doc?.name,
				invoice_doc_doctype: this.invoice_doc?.doctype,
				invoiceType: this.invoiceType,
				restaurant_mode: this.pos_profile.posa_enable_restaurant_mode
			});
			
			// Handle existing Sales Order editing scenario (restaurant mode)
			if (this.pos_profile.posa_enable_restaurant_mode &&
				this.invoice_doc &&
				this.invoice_doc.name &&
				(this.invoice_doc.doctype === "Sales Order" || this.invoiceType === "Order")) {
				
				console.log("Processing existing Sales Order for payment in restaurant mode");
				
				// CRITICAL FIX: Check if we already have a Sales Invoice (conversion already done)
				const doc = this.get_invoice_doc();
				console.log("Document analysis:", {
					name: doc.name,
					doctype: doc.doctype,
					docstatus: doc.docstatus,
					invoice_doc_name: this.invoice_doc.name,
					invoice_doc_doctype: this.invoice_doc.doctype
				});
				
				// If we already have a Sales Invoice, skip the conversion process
				if (doc.name && doc.name.startsWith('ACC-SINV-') && doc.doctype === 'Sales Invoice') {
					console.log("SKIP CONVERSION: Already have Sales Invoice, proceeding directly to payment");
					invoice_doc = doc;
					
					// Ensure invoice type is set correctly for payment
					this.invoiceType = "Invoice";
					this.invoiceTypes = ["Invoice"];
					this.eventBus.emit("change_invoice_type", "Invoice");
					console.log("Changed invoice type to 'Invoice' for existing Sales Invoice");
				} else {
					// We have a Sales Order that needs to be processed
					let originalSalesOrderName = null;
					
					// Extract original Sales Order name from document
					if (doc.name && doc.name.startsWith('SAL-ORD-')) {
						originalSalesOrderName = doc.name;
						console.log("PRESERVE: Original Sales Order name:", originalSalesOrderName);
					} else {
						// This shouldn't happen now, but handle gracefully
						console.warn("UNEXPECTED: Document doesn't have Sales Order format, using as-is");
						originalSalesOrderName = doc.name;
					}
					
					if (this.invoice_doc.docstatus === 1) {
						// For submitted orders, use the special update method
						console.log("Updating submitted Sales Order");
						invoice_doc = await this.update_submitted_order(doc);
					} else {
						// For draft orders, just update without submitting
						// Submission will happen when user clicks SUBMIT button
						console.log("Updating draft Sales Order (keeping draft status)");
						invoice_doc = this.update_invoice(doc);
					}
					
					// For draft orders, we'll handle submission in the payment window
					// Don't block draft orders from entering payment process
					
					if (!invoice_doc && !originalSalesOrderName) {
						console.log("Failed to update Sales Order");
						return;
					}
					
					// Use the original Sales Order name for conversion
					const orderNameForConversion = originalSalesOrderName || (invoice_doc && invoice_doc.name);
					
					// Handle draft vs submitted orders differently
					if (invoice_doc && invoice_doc.docstatus === 0) {
						// Draft order - go to payment window as-is (user will click SUBMIT ORDER there)
						console.log("Draft order - going to payment window without conversion:", orderNameForConversion);
						// No conversion needed - the payment window will handle submission
					} else {
						// Submitted order - convert to Sales Invoice for payment
						console.log("Converting submitted Sales Order to Sales Invoice:", orderNameForConversion);
						try {
							const invoiceResult = await frappe.call({
								method: "posawesome.posawesome.api.restaurant_orders.convert_order_to_invoice",
								args: {
									sales_order_name: orderNameForConversion,
								},
							});
							
							if (invoiceResult.message) {
								invoice_doc = invoiceResult.message;
								console.log("Successfully converted Sales Order to Sales Invoice for payment:", invoice_doc.name);
								
								// Change invoice type to "Invoice" after conversion
								this.invoiceType = "Invoice";
								this.invoiceTypes = ["Invoice"];
								this.eventBus.emit("change_invoice_type", "Invoice");
								console.log("Changed invoice type to 'Invoice' to activate payment buttons");
							} else {
								throw new Error("Failed to convert Sales Order to Sales Invoice");
							}
						} catch (error) {
							console.error("Error converting Sales Order to Invoice:", error);
							this.eventBus.emit("show_message", {
								title: __("Error converting order to invoice for payment"),
								color: "error",
							});
							return;
						}
					}
				}
			} else if (
				this.invoiceType === "Order" &&
				this.pos_profile.posa_create_only_sales_order &&
				!this.new_delivery_date &&
				!this.invoice_doc.posa_delivery_date
			) {
				console.log("Building local Sales Order doc for payment");
				invoice_doc = this.get_invoice_doc();
			} else if (this.invoice_doc.doctype == "Sales Order" && this.invoiceType === "Invoice") {
				console.log("Processing Sales Order payment");
				invoice_doc = await this.process_invoice_from_order();
			} else if (invoice_doc && invoice_doc.name && invoice_doc.doctype === 'Sales Invoice') {
				// CRITICAL: If we already have a converted Sales Invoice with Sales Order references, use it
				console.log("Using existing converted Sales Invoice:", invoice_doc.name);
				// Just update the existing invoice with current data, but preserve Sales Order references
				const updated_doc = this.update_invoice_preserve_so_refs(invoice_doc);
				invoice_doc = updated_doc || invoice_doc;
			} else {
				console.log("Processing regular invoice");
				invoice_doc = this.process_invoice();
			}

			if (!invoice_doc) {
				console.log("Failed to process invoice");
				return;
			}

			// Update invoice_doc with current currency info and ensure all required fields are set
			invoice_doc.currency = this.selected_currency || this.pos_profile.currency;
			invoice_doc.conversion_rate = this.conversion_rate || 1;
			invoice_doc.plc_conversion_rate = this.exchange_rate || 1;
			
			// Ensure critical fields are set for payment button activation
			invoice_doc.is_pos = 1;
			// For restaurant mode, disable stock update to avoid validation issues
			invoice_doc.update_stock = this.pos_profile.posa_enable_restaurant_mode ? 0 : 1;
			invoice_doc.company = invoice_doc.company || this.pos_profile.company;
			invoice_doc.customer = invoice_doc.customer || this.customer;
			invoice_doc.pos_profile = invoice_doc.pos_profile || this.pos_profile.name;
			
			// Ensure totals are properly set
			if (!invoice_doc.grand_total && this.subtotal) {
				invoice_doc.grand_total = this.subtotal;
			}
			if (!invoice_doc.rounded_total && this.subtotal) {
				invoice_doc.rounded_total = this.pos_profile.disable_rounded_total ?
					this.flt(this.subtotal, this.currency_precision) :
					this.roundAmount(this.subtotal);
			}
			
			console.log("Final invoice_doc for payment:", {
				name: invoice_doc.name,
				doctype: invoice_doc.doctype,
				is_pos: invoice_doc.is_pos,
				grand_total: invoice_doc.grand_total,
				rounded_total: invoice_doc.rounded_total,
				customer: invoice_doc.customer,
				company: invoice_doc.company,
				currency: invoice_doc.currency,
				pos_profile: invoice_doc.pos_profile
			});

			// Preserve totals calculated on the server to ensure taxes are included
			// The process_invoice method already updates the invoice with taxes and
			// totals via the backend. Overriding those values here caused the
			// payment dialog to display amounts without taxes applied. Simply use
			// the values returned from the server instead of recalculating them on
			// the client side.

			// Update totals on the client has been disabled. The original code is
			// kept below for reference and is intentionally commented out to avoid
			// overriding the server calculated values.
			// invoice_doc.total = this.Total;
			// invoice_doc.grand_total = this.subtotal;

			// if (this.pos_profile.disable_rounded_total) {
			//   invoice_doc.rounded_total = flt(this.subtotal, this.currency_precision);
			// } else {
			//   invoice_doc.rounded_total = this.roundAmount(this.subtotal);
			// }
			// invoice_doc.base_total = this.Total * (1 / this.exchange_rate || 1);
			// invoice_doc.base_grand_total = this.subtotal * (1 / this.exchange_rate || 1);
			// if (this.pos_profile.disable_rounded_total) {
			//   invoice_doc.base_rounded_total = flt(invoice_doc.base_grand_total, this.currency_precision);
			// } else {
			//   invoice_doc.base_rounded_total = this.roundAmount(invoice_doc.base_grand_total);
			// }

			// Check if this is a return invoice
			if (this.isReturnInvoice || invoice_doc.is_return) {
				console.log("Preparing RETURN invoice for payment with:", {
					is_return: invoice_doc.is_return,
					invoiceType: this.invoiceType,
					return_against: invoice_doc.return_against,
					items: invoice_doc.items.length,
					grand_total: invoice_doc.grand_total,
				});

				// For return invoices, explicitly ensure all amounts are negative
				invoice_doc.is_return = 1;
				if (invoice_doc.grand_total > 0) invoice_doc.grand_total = -Math.abs(invoice_doc.grand_total);
				if (invoice_doc.rounded_total > 0)
					invoice_doc.rounded_total = -Math.abs(invoice_doc.rounded_total);
				if (invoice_doc.total > 0) invoice_doc.total = -Math.abs(invoice_doc.total);
				if (invoice_doc.base_grand_total > 0)
					invoice_doc.base_grand_total = -Math.abs(invoice_doc.base_grand_total);
				if (invoice_doc.base_rounded_total > 0)
					invoice_doc.base_rounded_total = -Math.abs(invoice_doc.base_rounded_total);
				if (invoice_doc.base_total > 0) invoice_doc.base_total = -Math.abs(invoice_doc.base_total);

				// Ensure all items have negative quantity and amount
				if (invoice_doc.items && invoice_doc.items.length) {
					invoice_doc.items.forEach((item) => {
						if (item.qty > 0) item.qty = -Math.abs(item.qty);
						if (item.stock_qty > 0) item.stock_qty = -Math.abs(item.stock_qty);
						if (item.amount > 0) item.amount = -Math.abs(item.amount);
					});
				}
			}

			// Get payments with correct sign (positive/negative)
			invoice_doc.payments = this.get_payments();
			console.log("Final payment data:", invoice_doc.payments);

			// Double-check return invoice payments are negative
			if ((this.isReturnInvoice || invoice_doc.is_return) && invoice_doc.payments.length) {
				invoice_doc.payments.forEach((payment) => {
					if (payment.amount > 0) payment.amount = -Math.abs(payment.amount);
					if (payment.base_amount > 0) payment.base_amount = -Math.abs(payment.base_amount);
				});
				console.log("Ensured negative payment amounts for return:", invoice_doc.payments);
			}

			console.log("Showing payment dialog with currency:", invoice_doc.currency);
			this.eventBus.emit("show_payment", "true");
			this.eventBus.emit("send_invoice_doc_payment", invoice_doc);
		} catch (error) {
			console.error("Error in show_payment:", error);
			this.eventBus.emit("show_message", {
				title: __("Error processing payment"),
				color: "error",
				message: error.message,
			});
		}
	},

	// Validate invoice before payment/submit (return logic, quantity, rates, etc)
	async validate() {
		console.log("Starting return validation");

		// For all returns, check if amounts are negative
		if (this.isReturnInvoice) {
			console.log("Validating return invoice values");

			// Check if quantities are negative
			const positiveItems = this.items.filter((item) => item.qty >= 0 || item.stock_qty >= 0);
			if (positiveItems.length > 0) {
				console.log(
					"Found positive quantities in return items:",
					positiveItems.map((i) => i.item_code),
				);
				this.eventBus.emit("show_message", {
					title: __(`Return items must have negative quantities`),
					color: "error",
				});

				// Fix the quantities to be negative
				positiveItems.forEach((item) => {
					item.qty = -Math.abs(item.qty);
					item.stock_qty = -Math.abs(item.stock_qty);
				});

				// Force update to reflect changes
				this.$forceUpdate();
			}

			// Ensure total amount is negative
			if (this.subtotal > 0) {
				console.log("Return has positive subtotal:", this.subtotal);
				this.eventBus.emit("show_message", {
					title: __(`Return total must be negative`),
					color: "warning",
				});
			}
		}

		// For return with reference to existing invoice
		if (this.invoice_doc.is_return && this.invoice_doc.return_against) {
			console.log("Return doc:", this.invoice_doc);
			console.log("Current items:", this.items);

			try {
				// Get original invoice items for comparison
				const original_items = await new Promise((resolve, reject) => {
					frappe.call({
						method: "frappe.client.get",
						args: {
							doctype: this.pos_profile.create_pos_invoice_instead_of_sales_invoice
								? "POS Invoice"
								: "Sales Invoice",
							name: this.invoice_doc.return_against,
						},
						callback: (r) => {
							if (r.message) {
								console.log("Original invoice data:", r.message);
								resolve(r.message.items || []);
							} else {
								reject(new Error("Original invoice not found"));
							}
						},
					});
				});

				console.log("Original invoice items:", original_items);
				console.log(
					"Original item codes:",
					original_items.map((item) => ({
						item_code: item.item_code,
						qty: item.qty,
						rate: item.rate,
					})),
				);

				// Validate each return item
				for (const item of this.items) {
					console.log("Validating return item:", {
						item_code: item.item_code,
						rate: item.rate,
						qty: item.qty,
					});

					// Normalize item codes by trimming and converting to uppercase
					const normalized_return_item_code = item.item_code.trim().toUpperCase();

					// Find matching item in original invoice
					const original_item = original_items.find(
						(orig) => orig.item_code.trim().toUpperCase() === normalized_return_item_code,
					);

					if (!original_item) {
						console.log("Item not found in original invoice:", {
							return_item_code: normalized_return_item_code,
							original_items: original_items.map((i) => i.item_code.trim().toUpperCase()),
						});

						this.eventBus.emit("show_message", {
							title: __(`Item ${item.item_code} not found in original invoice`),
							color: "error",
						});
						return false;
					}

					// Compare rates with precision
					const rate_diff = Math.abs(original_item.rate - item.rate);
					console.log("Rate comparison:", {
						return_rate: item.rate,
						orig_rate: original_item.rate,
						difference: rate_diff,
					});

					if (rate_diff > 0.01) {
						this.eventBus.emit("show_message", {
							title: __(`Rate mismatch for item ${item.item_code}`),
							color: "error",
						});
						return false;
					}

					// Compare quantities
					const return_qty = Math.abs(item.qty);
					const orig_qty = original_item.qty;
					console.log("Quantity comparison:", {
						return_qty: return_qty,
						orig_qty: orig_qty,
					});

					if (return_qty > orig_qty) {
						this.eventBus.emit("show_message", {
							title: __(
								`Return quantity cannot be greater than original quantity for item ${item.item_code}`,
							),
							color: "error",
						});
						return false;
					}
				}
			} catch (error) {
				console.error("Error in validation:", error);
				this.eventBus.emit("show_message", {
					title: __(`Error validating return: ${error.message}`),
					color: "error",
				});
				return false;
			}
		}
		return true;
	},

	// Get draft invoices from backend
	get_draft_invoices() {
		var vm = this;
		frappe.call({
			method: "posawesome.posawesome.api.invoices.get_draft_invoices",
			args: {
				pos_opening_shift: this.pos_opening_shift.name,
				doctype: this.pos_profile.create_pos_invoice_instead_of_sales_invoice
					? "POS Invoice"
					: "Sales Invoice",
			},
			async: false,
			callback: function (r) {
				if (r.message) {
					vm.eventBus.emit("open_drafts", r.message);
				}
			},
		});
	},

	// Get draft orders from backend
	get_draft_orders() {
		var vm = this;
		frappe.call({
			method: "posawesome.posawesome.api.sales_orders.search_orders",
			args: {
				company: this.pos_profile.company,
				currency: this.pos_profile.currency,
			},
			async: false,
			callback: function (r) {
				if (r.message) {
					vm.eventBus.emit("open_orders", r.message);
				}
			},
		});
	},

	// Open returns dialog
	open_returns() {
		this.eventBus.emit("open_returns", this.pos_profile.company);
	},

	// Close payment dialog
	close_payments() {
		this.eventBus.emit("show_payment", "false");
	},

	// Update details for all items (fetch from backend)
	async update_items_details(items) {
		if (!items?.length) return;
		if (!this.pos_profile) return;

		try {
			const response = await frappe.call({
				method: "posawesome.posawesome.api.items.get_items_details",
				args: {
					pos_profile: JSON.stringify(this.pos_profile),
					items_data: JSON.stringify(items),
					price_list: this.selected_price_list || this.pos_profile.selling_price_list,
				},
			});

			if (response?.message) {
				items.forEach((item) => {
					const updated_item = response.message.find(
						(element) => element.posa_row_id == item.posa_row_id,
					);
					if (updated_item) {
						item.actual_qty = updated_item.actual_qty;
						item.item_uoms = updated_item.item_uoms;
						item.has_batch_no = updated_item.has_batch_no;
						item.has_serial_no = updated_item.has_serial_no;
						item.batch_no_data = updated_item.batch_no_data;
						item.serial_no_data = updated_item.serial_no_data;
                                               if (updated_item.rate !== undefined) {
                                                       if (!item.locked_price && !item.posa_offer_applied) {
                                                               if (updated_item.rate !== 0 || !item.rate) {
                                                                       item.rate = updated_item.rate;
                                                                       item.price_list_rate =
                                                                               updated_item.price_list_rate || updated_item.rate;
                                                               }
                                                       } else if (!item.price_list_rate) {
                                                               item.price_list_rate =
                                                                       updated_item.price_list_rate || updated_item.rate;
                                                       }
                                               }
						if (updated_item.currency) {
							item.currency = updated_item.currency;
						}
					}
				});
			}
		} catch (error) {
			console.error("Error updating items:", error);
			this.eventBus.emit("show_message", {
				title: __("Error updating item details"),
				color: "error",
			});
		}
	},

	// Update details for a single item (fetch from backend)
	update_item_detail(item, force_update = false) {
		console.log("update_item_detail request", {
			code: item.item_code,
			force_update,
		});
		if (!item.item_code) {
			return;
		}
		var vm = this;

		// If a manual rate was set (e.g. via explicit UOM pricing), don't
		// overwrite it on expand unless explicitly forced.
		if (item._manual_rate_set && !force_update) {
			return;
		}

		// Remove this block which was causing the issue - rates should persist regardless of currency
		// if (item.price_list_rate && !item.posa_offer_applied) {
		//   item.rate = item.price_list_rate;
		//   this.$forceUpdate();
		// }

		const currentDoc = this.get_invoice_doc();
		console.log("update_item_detail - currentDoc info:", {
			name: currentDoc.name,
			doctype: currentDoc.doctype,
			docstatus: currentDoc.docstatus
		});
		
		frappe.call({
			method: "posawesome.posawesome.api.items.get_item_detail",
			args: {
				warehouse: item.warehouse || this.pos_profile.warehouse,
				doc: currentDoc,
				price_list: this.selected_price_list || this.pos_profile.selling_price_list,
				item: {
					item_code: item.item_code,
					customer: this.customer,
					doctype: currentDoc.doctype,
					name: currentDoc.name || `New ${currentDoc.doctype} 1`,
					company: this.pos_profile.company,
					conversion_rate: 1,
					currency: this.pos_profile.currency,
					qty: item.qty,
					price_list_rate: item.base_price_list_rate || item.price_list_rate,
					child_docname: `New ${currentDoc.doctype} Item 1`,
					cost_center: this.pos_profile.cost_center,
					pos_profile: this.pos_profile.name,
					uom: item.uom,
					tax_category: "",
					transaction_type: "selling",
					update_stock: this.pos_profile.posa_enable_restaurant_mode ? 0 : this.pos_profile.update_stock,
					price_list: this.get_price_list(),
					has_batch_no: item.has_batch_no,
					has_serial_no: item.has_serial_no,
					serial_no: item.serial_no,
					batch_no: item.batch_no,
					is_stock_item: item.is_stock_item,
				},
			},
			callback: function (r) {
				console.log("=== get_item_detail API response ===", r);
				if (r.message) {
					const data = r.message;
					if (!item.warehouse) {
						item.warehouse = vm.pos_profile.warehouse;
					}
					// Ensure price list currency is synced from server response
					if (data.price_list_currency) {
						vm.price_list_currency = data.price_list_currency;
					}

					if (!item.original_currency) {
						item.original_currency =
							data.price_list_currency || vm.price_list_currency || vm.selected_currency;
					}
					if (!item.original_rate) {
						item.original_rate = data.price_list_rate;
					}
					if (data.serial_no_data) {
						item.serial_no_data = data.serial_no_data;
					}
					if (data.batch_no_data) {
						item.batch_no_data = data.batch_no_data;
					}
					if (
						item.has_batch_no &&
						vm.pos_profile.posa_auto_set_batch &&
						!item.batch_no &&
						data.batch_no_data &&
						data.batch_no_data.length > 0
					) {
						item.batch_no_data = data.batch_no_data;
						// Pass null instead of undefined to avoid console warning
						vm.set_batch_qty(item, null, false);
					}

					if (!item.locked_price) {
						// First save base rates if not exists or when force update is requested
						// Avoid overriding existing base rates when the selected currency
						// matches the POS Profile currency. This prevents manual or offer
						// adjusted rates from being reset whenever an item row is expanded.
						if (force_update || !item.base_rate) {
							// Always store base rates from server in base currency
							if (data.price_list_rate !== 0 || !item.base_price_list_rate) {
								item.base_price_list_rate = data.price_list_rate;
								if (!item.posa_offer_applied) {
									item.base_rate = data.price_list_rate;
								}
							}
						}

						// Only update rates if no offer is applied
						if (!item.posa_offer_applied) {
							const companyCurrency = vm.pos_profile.currency;
							const baseCurrency = companyCurrency;

							if (
								vm.selected_currency === vm.price_list_currency &&
								vm.selected_currency !== companyCurrency
							) {
								const conv = vm.conversion_rate || 1;
								item.price_list_rate = vm.flt(
									item.base_price_list_rate / conv,
									vm.currency_precision,
								);

								if (!item._manual_rate_set) {
									item.rate = vm.flt(item.base_rate / conv, vm.currency_precision);
								}
							} else if (vm.selected_currency !== baseCurrency) {
								const exchange_rate = vm.exchange_rate || 1;
								item.price_list_rate = vm.flt(
									item.base_price_list_rate * exchange_rate,
									vm.currency_precision,
								);

								item.rate = vm.flt(item.base_rate * exchange_rate, vm.currency_precision);
							} else {
								item.price_list_rate = item.base_price_list_rate;

								if (!item._manual_rate_set) {
									item.rate = item.base_rate;
								}
							}
                                               } else {
                                                       // Preserve discounted price when an offer is applied so the
                                                       // rate doesn't revert to the original price list value.
                                                       const baseCurrency = vm.price_list_currency || vm.pos_profile.currency;
                                                       if (vm.selected_currency !== baseCurrency) {
                                                               item.price_list_rate = vm.flt(
                                                                       item.base_rate * vm.exchange_rate,
                                                                       vm.currency_precision,
                                                               );
                                                       } else {
                                                               item.price_list_rate = item.base_rate;
                                                       }
                                               }

						// Handle customer discount only if no offer is applied
						if (
							!item.posa_offer_applied &&
							vm.pos_profile.posa_apply_customer_discount &&
							vm.customer_info.posa_discount > 0 &&
							vm.customer_info.posa_discount <= 100 &&
							item.posa_is_offer == 0 &&
							!item.posa_is_replace
						) {
							const discount_percent =
								item.max_discount > 0
									? Math.min(item.max_discount, vm.customer_info.posa_discount)
									: vm.customer_info.posa_discount;

							item.discount_percentage = discount_percent;

							// Calculate discount in selected currency
							const discount_amount = vm.flt(
								(item.price_list_rate * discount_percent) / 100,
								vm.currency_precision,
							);
							item.discount_amount = discount_amount;

							// Also store base discount amount
							item.base_discount_amount = vm.flt(
								(item.base_price_list_rate * discount_percent) / 100,
								vm.currency_precision,
							);

							// Update rates with discount
							item.rate = vm.flt(item.price_list_rate - discount_amount, vm.currency_precision);
							item.base_rate = vm.flt(
								item.base_price_list_rate - item.base_discount_amount,
								vm.currency_precision,
							);
						}
					}

					// Update other item details
					item.last_purchase_rate = data.last_purchase_rate;
					item.projected_qty = data.projected_qty;
					item.reserved_qty = data.reserved_qty;
					item.conversion_factor = data.conversion_factor;
					item.stock_qty = data.stock_qty;
					item.actual_qty = data.actual_qty;
					item.stock_uom = data.stock_uom;
					item.has_serial_no = data.has_serial_no;
					item.has_batch_no = data.has_batch_no;

					// Calculate final amount
					item.amount = vm.flt(item.qty * item.rate, vm.currency_precision);
					item.base_amount = vm.flt(item.qty * item.base_rate, vm.currency_precision);

					// Log updated rates for debugging
					console.log(`Updated rates for ${item.item_code} on expand:`, {
						base_rate: item.base_rate,
						rate: item.rate,
						base_price_list_rate: item.base_price_list_rate,
						price_list_rate: item.price_list_rate,
						exchange_rate: vm.exchange_rate,
						selected_currency: vm.selected_currency,
						default_currency: vm.pos_profile.currency,
					});

					// Force update UI immediately
					vm.$forceUpdate();
				}
			},
			error: function(r) {
				console.error("=== get_item_detail API ERROR ===", r);
				console.error("Error details:", {
					status: r.status,
					statusText: r.statusText,
					responseText: r.responseText,
					currentDoc: currentDoc,
					item_code: item.item_code
				});
			}
		});
	},

	// Fetch customer details (info, price list, etc)
	async fetch_customer_details() {
		var vm = this;
		if (!this.customer) return;

                if (isOffline()) {
                        try {
                                const list = await getCustomerStorage();
                                const cached = (list || []).find(
                                        (c) => c.name === vm.customer || c.customer_name === vm.customer,
                                );
				if (cached) {
					vm.customer_info = { ...cached };
					if (vm.pos_profile.posa_force_reload_items && cached.customer_price_list) {
						vm.selected_price_list = cached.customer_price_list;
						vm.eventBus.emit("update_customer_price_list", cached.customer_price_list);
						vm.apply_cached_price_list(cached.customer_price_list);
					}
					return;
				}
				const queued = (getOfflineCustomers() || [])
					.map((e) => e.args)
					.find((c) => c.customer_name === vm.customer);
				if (queued) {
					vm.customer_info = { ...queued, name: queued.customer_name };
					if (vm.pos_profile.posa_force_reload_items && queued.customer_price_list) {
						vm.selected_price_list = queued.customer_price_list;
						vm.eventBus.emit("update_customer_price_list", queued.customer_price_list);
						vm.apply_cached_price_list(queued.customer_price_list);
					}
					return;
				}
			} catch (error) {
				console.error("Failed to fetch cached customer", error);
			}
		}

		try {
			const r = await frappe.call({
				method: "posawesome.posawesome.api.customers.get_customer_info",
				args: {
					customer: vm.customer,
				},
			});
			const message = r.message;
			if (!r.exc) {
				vm.customer_info = {
					...message,
				};
			}
			// When force reload is enabled, automatically switch to the
			// customer's default price list so that item rates are fetched
			// correctly from the server.
			if (vm.pos_profile.posa_force_reload_items && message.customer_price_list) {
				vm.selected_price_list = message.customer_price_list;
				vm.eventBus.emit("update_customer_price_list", message.customer_price_list);
				vm.apply_cached_price_list(message.customer_price_list);
			}
		} catch (error) {
			console.error("Failed to fetch customer details", error);
		}
	},

	// Get price list for current customer
	get_price_list() {
		// Use the currently selected price list if available,
		// otherwise fall back to the POS Profile selling price list
		return this.selected_price_list || this.pos_profile.selling_price_list;
	},

	// Update price list for customer
	update_price_list() {
		// Only set the POS Profile price list if it has changed
		const price_list = this.pos_profile.selling_price_list;
		if (this.selected_price_list !== price_list) {
			this.selected_price_list = price_list;
			// Clear any customer specific price list to avoid reloading items
			this.eventBus.emit("update_customer_price_list", null);
		}
	},

	// Apply cached price list rates to existing invoice items
	async apply_cached_price_list(price_list) {
		const cached = await getCachedPriceListItems(price_list);
		if (!Array.isArray(cached) || !cached.length) {
			return;
		}

		const map = {};
		cached.forEach((ci) => {
			map[ci.item_code] = ci;
		});

		this.items.forEach((item) => {
			const ci = map[item.item_code];
			if (!ci) return;

			const newRate = ci.rate || ci.price_list_rate;
			const priceCurrency = ci.currency || this.selected_currency;

			if (!item.original_currency) {
				item.original_currency = priceCurrency;
			}
			if (!item.original_rate) {
				item.original_rate = newRate;
			}

			if (priceCurrency === this.selected_currency) {
				const companyCurrency = this.pos_profile.currency;
				if (priceCurrency !== companyCurrency) {
					const conv = this.conversion_rate || 1;
					item.base_price_list_rate = newRate * conv;
					if (!item._manual_rate_set) {
						item.base_rate = newRate * conv;
					}
				} else {
					item.base_price_list_rate = newRate;
					if (!item._manual_rate_set) {
						item.base_rate = newRate;
					}
				}
				item.price_list_rate = newRate;
				if (!item._manual_rate_set) {
					item.rate = newRate;
				}
			} else {
				// Rate in base currency
				if (newRate !== 0 || !item.base_price_list_rate) {
					item.base_price_list_rate = newRate;
					if (!item._manual_rate_set) {
						item.base_rate = newRate;
					}
				}

				const baseCurrency = this.pos_profile.currency;
				if (this.selected_currency !== baseCurrency) {
					const conv = this.exchange_rate || 1;
					const convRate = this.flt(newRate * conv, this.currency_precision);
					if (newRate !== 0 || !item.price_list_rate) {
						item.price_list_rate = convRate;
					}
					if (!item._manual_rate_set && (newRate !== 0 || !item.rate)) {
						item.rate = convRate;
					}
				} else {
					if (newRate !== 0 || !item.price_list_rate) {
						item.price_list_rate = newRate;
					}
					if (!item._manual_rate_set && (newRate !== 0 || !item.rate)) {
						item.rate = newRate;
					}
				}
			}

			// Recalculate final amounts
			item.amount = this.flt(item.qty * item.rate, this.currency_precision);
			item.base_amount = this.flt(item.qty * item.base_rate, this.currency_precision);
		});

		this.$forceUpdate();
	},

	// Update additional discount amount based on percentage
	update_discount_umount() {
		return updateDiscountAmount(this);
	},

	// Calculate prices and discounts for an item based on field change
	calc_prices(item, value, $event) {
		return calcPrices(item, value, $event, this);
	},

	// Calculate item price and discount fields
	calc_item_price(item) {
		return calcItemPrice(item, this);
	},

	// Update UOM (unit of measure) for an item and recalculate prices
	calc_uom(item, value) {
		return calcUom(item, value, this);
	},

	// Calculate stock quantity for an item with stock validation
	calc_stock_qty(item, value) {
		calcStockQty(item, value, this);
		
		// CRITICAL FIX: Only apply stock validation to stock items
		if (item.is_stock_item) {
			if (this.update_qty_limits) {
				this.update_qty_limits(item);
			}
			if (item.max_qty !== undefined && flt(item.qty) > flt(item.max_qty)) {
				const blockSale =
					!this.stock_settings.allow_negative_stock ||
					this.pos_profile.posa_block_sale_beyond_available_qty;
				if (blockSale) {
					item.qty = item.max_qty;
					calcStockQty(item, item.qty, this);
					this.$forceUpdate();
					this.eventBus.emit("show_message", {
						title: __(`Maximum available quantity is {0}. Quantity adjusted to match stock.`, [
							this.formatFloat(item.max_qty),
						]),
						color: "error",
					});
				} else {
					this.eventBus.emit("show_message", {
						title: __("Stock is lower than requested. Proceeding may create negative stock."),
						color: "warning",
					});
				}
			}
		}
		// For non-stock items, no stock validation is needed
	},

	// Update quantity limits based on available stock
	update_qty_limits(item) {
		// CRITICAL FIX: Only apply stock validation to stock items
		if (item && item.available_qty !== undefined && item.is_stock_item) {
			item.max_qty = flt(item.available_qty / (item.conversion_factor || 1));

			if (item.max_qty !== undefined && flt(item.qty) > flt(item.max_qty)) {
				const blockSale =
					!this.stock_settings.allow_negative_stock ||
					this.pos_profile.posa_block_sale_beyond_available_qty;
				if (blockSale) {
					item.qty = item.max_qty;
					calcStockQty(item, item.qty, this);
					this.$forceUpdate();
					this.eventBus.emit("show_message", {
						title: __(`Maximum available quantity is {0}. Quantity adjusted to match stock.`, [
							this.formatFloat(item.max_qty),
						]),
						color: "error",
					});
				} else {
					this.eventBus.emit("show_message", {
						title: __("Stock is lower than requested. Proceeding may create negative stock."),
						color: "warning",
					});
				}
			}

			item.disable_increment =
				(!this.stock_settings.allow_negative_stock ||
					this.pos_profile.posa_block_sale_beyond_available_qty) &&
				item.qty >= item.max_qty;
		} else if (item && !item.is_stock_item) {
			// For non-stock items, don't apply any stock limits
			item.max_qty = undefined;
			item.disable_increment = false;
		}
	},

	// Fetch available stock for an item and cache it
	async fetch_available_qty(item) {
		// CRITICAL FIX: Only fetch stock for stock items
		if (!item || !item.item_code || !item.warehouse || !item.is_stock_item) {
			// For non-stock items, set unlimited availability
			if (item && !item.is_stock_item) {
				item.available_qty = undefined; // No stock limits
				item.max_qty = undefined;
				item.disable_increment = false;
			}
			return;
		}
		
		const key = `${item.item_code}:${item.warehouse}:${item.batch_no || ""}:${item.uom}`;
		const cached = this.available_stock_cache[key];
		const now = Date.now();
		if (cached && now - cached.ts < 60000) {
			item.available_qty = cached.qty;
			this.update_qty_limits(item);
			return;
		}
		try {
			const r = await frappe.call({
				method: "posawesome.posawesome.api.items.get_available_qty",
				args: {
					items: JSON.stringify([
						{
							item_code: item.item_code,
							warehouse: item.warehouse,
							batch_no: item.batch_no,
						},
					]),
				},
			});
			const qty = r.message && r.message.length ? flt(r.message[0].available_qty) : 0;
			this.available_stock_cache[key] = { qty, ts: now };
			item.available_qty = qty;
			this.update_qty_limits(item);
		} catch (e) {
			console.error("Failed to fetch available qty", e);
		}
	},

	// Set serial numbers for an item (and update qty)
	set_serial_no(item) {
		return setSerialNo(item, this);
	},

	// Set batch number for an item (and update batch data)
	set_batch_qty(item, value, update = true) {
		return setBatchQty(item, value, update, this);
	},

	change_price_list_rate(item) {
		const vm = this;

		const d = new frappe.ui.Dialog({
			title: __("Change Price"),
			fields: [
				{
					fieldname: "new_rate",
					fieldtype: "Float",
					label: __("New Price List Rate"),
					default: item.price_list_rate || item.rate,
					reqd: 1,
				},
			],
			primary_action_label: __("Update"),
			primary_action(values) {
				const rate = flt(values.new_rate);
				frappe.call({
					method: "posawesome.posawesome.api.items.update_price_list_rate",
					args: {
						item_code: item.item_code,
						price_list: vm.get_price_list(),
						rate: rate,
						uom: item.uom,
					},
					callback(r) {
						if (!r.exc) {
							item.price_list_rate = rate;
							item.base_price_list_rate = rate;
							if (!item._manual_rate_set) {
								item.rate = rate;
								item.base_rate = rate;
							}
							vm.calc_item_price(item);
							vm.eventBus.emit("show_message", {
								title: r.message || __("Item price updated"),
								color: "success",
							});
						}
					},
				});
				d.hide();
			},
		});

		d.get_field("new_rate").$input.on("keydown", function (e) {
			if (e.key === "Enter") {
				d.get_primary_btn().click();
			}
		});

		d.show();
	},
};
