<template>
	<!-- Main Invoice Wrapper -->
	<div class="pa-0">
		<!-- Cancel Sale Confirmation Dialog -->
		<CancelSaleDialog v-model="cancel_dialog" @confirm="cancel_invoice" />

		<!-- Main Invoice Card (contains all invoice content) -->
		<v-card
			ref="invoiceCard"
			:style="{
				height: invoiceHeight || 'var(--container-height)',
				maxHeight: invoiceHeight || 'var(--container-height)',
				backgroundColor: isDarkTheme ? '#121212' : '',
				resize: 'vertical',
				overflow: 'auto',
			}"
			:class="[
				'cards my-0 py-0 mt-3 resizable',
				isDarkTheme ? '' : 'bg-grey-lighten-5',
				{ 'return-mode': isReturnInvoice },
				{ 'edit-mode': isEditingExistingOrder },
			]"
			@mouseup="saveInvoiceHeight"
			@touchend="saveInvoiceHeight"
		>
			<!-- Dynamic padding wrapper -->
			<div class="dynamic-padding">
				<v-alert
					type="info"
					density="compact"
					class="mb-2"
					v-if="pos_profile.create_pos_invoice_instead_of_sales_invoice"
				>
					{{ __("Invoices saved as POS Invoices") }}
				</v-alert>
				<!-- Top Row: Customer Selection and Invoice Type -->
				<v-row align="center" class="items px-3 py-2">
					<v-col :cols="pos_profile.posa_allow_sales_order && !pos_profile.posa_enable_restaurant_mode ? 9 : 12" class="pb-0 pr-0">
						<!-- Customer selection component -->
						<Customer />
					</v-col>
					<!-- Invoice Type Selection (Only shown if sales orders are allowed and NOT in restaurant mode) -->
					<v-col v-if="pos_profile.posa_allow_sales_order && !pos_profile.posa_enable_restaurant_mode" cols="3" class="pb-4">
						<v-select
							density="compact"
							hide-details
							variant="solo"
							color="primary"
							:bg-color="isDarkTheme ? '#1E1E1E' : 'white'"
							class="dark-field sleek-field"
							:items="invoiceTypes"
							:label="frappe._('Type')"
							v-model="invoiceType"
							:disabled="invoiceType == 'Return'"
						></v-select>
					</v-col>
				</v-row>

				<!-- Restaurant Order Type Section (Only if restaurant mode is enabled) -->
				<RestaurantOrderType
					:pos_profile="pos_profile"
					:order_types="restaurant_order_types"
					:available_tables="available_tables"
					:selected_order_type="selected_order_type"
					:selected_table="selected_table"
					:order_status="order_status"
					:readonly="readonly"
					@update:selected_order_type="
						(val) => {
							selected_order_type = val;
							update_order_type();
						}
					"
					@update:selected_table="
						(val) => {
							selected_table = val;
							update_table_selection();
						}
					"
				/>

				<!-- Delivery Charges Section (Only if enabled in POS profile) -->
				<DeliveryCharges
					:pos_profile="pos_profile"
					:delivery_charges="delivery_charges"
					:selected_delivery_charge="selected_delivery_charge"
					:delivery_charges_rate="delivery_charges_rate"
					:deliveryChargesFilter="deliveryChargesFilter"
					:formatCurrency="formatCurrency"
					:currencySymbol="currencySymbol"
					:readonly="readonly"
					@update:selected_delivery_charge="
						(val) => {
							selected_delivery_charge = val;
							update_delivery_charges();
						}
					"
				/>

				<!-- Posting Date and Customer Balance Section -->
				<PostingDateRow
					:pos_profile="pos_profile"
					:posting_date_display="posting_date_display"
					:customer_balance="customer_balance"
					:price-list="selected_price_list"
					:price-lists="price_lists"
					:formatCurrency="formatCurrency"
					@update:posting_date_display="
						(val) => {
							posting_date_display = val;
						}
					"
					@update:priceList="
						(val) => {
							selected_price_list = val;
						}
					"
				/>

				<!-- Multi-Currency Section (Only if enabled in POS profile) -->
				<MultiCurrencyRow
					:pos_profile="pos_profile"
					:selected_currency="selected_currency"
					:plc_conversion_rate="exchange_rate"
					:conversion_rate="conversion_rate"
					:available_currencies="available_currencies"
					:isNumber="isNumber"
					:price_list_currency="price_list_currency"
					@update:selected_currency="
						(val) => {
							selected_currency = val;
							update_currency(val);
						}
					"
					@update:plc_conversion_rate="
						(val) => {
							exchange_rate = val;
							update_exchange_rate();
						}
					"
					@update:conversion_rate="
						(val) => {
							conversion_rate = val;
							update_conversion_rate();
						}
					"
				/>

				<!-- Items Table Section (Main items list for invoice) -->
				<div class="items-table-wrapper">
					<!-- Column selector button moved outside the table -->
					<div class="column-selector-container">
						<v-btn
							density="compact"
							variant="text"
							color="primary"
							prepend-icon="mdi-cog-outline"
							@click="toggleColumnSelection"
							class="column-selector-btn"
						>
							{{ __("Columns") }}
						</v-btn>

						<v-dialog v-model="show_column_selector" max-width="500px">
							<v-card>
								<v-card-title class="text-h6 pa-4 d-flex align-center">
									<span>{{ __("Select Columns to Display") }}</span>
									<v-spacer></v-spacer>
									<v-btn
										icon="mdi-close"
										variant="text"
										density="compact"
										@click="show_column_selector = false"
									></v-btn>
								</v-card-title>
								<v-divider></v-divider>
								<v-card-text class="pa-4">
									<v-row dense>
										<v-col
											cols="12"
											v-for="column in available_columns.filter((col) => !col.required)"
											:key="column.key"
										>
											<v-switch
												v-model="temp_selected_columns"
												:label="column.title"
												:value="column.key"
												hide-details
												density="compact"
												color="primary"
												class="column-switch mb-1"
												:disabled="column.required"
											></v-switch>
										</v-col>
									</v-row>
									<div class="text-caption mt-2">
										{{ __("Required columns cannot be hidden") }}
									</div>
								</v-card-text>
								<v-card-actions class="pa-4 pt-0">
									<v-btn color="error" variant="text" @click="cancelColumnSelection">{{
										__("Cancel")
									}}</v-btn>
									<v-spacer></v-spacer>
									<v-btn color="primary" variant="tonal" @click="updateSelectedColumns">{{
										__("Apply")
									}}</v-btn>
								</v-card-actions>
							</v-card>
						</v-dialog>
					</div>

					<!-- ItemsTable component with reorder event handler -->
					<ItemsTable
						ref="itemsTable"
						:headers="items_headers"
						:items="items"
						v-model:expanded="expanded"
						:itemsPerPage="itemsPerPage"
						:itemSearch="itemSearch"
						:pos_profile="pos_profile"
						:invoice_doc="invoice_doc"
						:invoiceType="invoiceType"
						:stock_settings="stock_settings"
						:displayCurrency="displayCurrency"
						:formatFloat="formatFloat"
						:formatCurrency="formatCurrency"
						:currencySymbol="currencySymbol"
						:isNumber="isNumber"
						:setFormatedQty="setFormatedQty"
						:setFormatedCurrency="setFormatedCurrency"
						:calcPrices="calc_prices"
						:calcUom="calc_uom"
						:setSerialNo="set_serial_no"
						:setBatchQty="set_batch_qty"
						:validateDueDate="validate_due_date"
						:removeItem="remove_item"
						:subtractOne="subtract_one"
						:addOne="add_one"
						:toggleOffer="toggleOffer"
						:changePriceListRate="change_price_list_rate"
						:isNegative="isNegative"
						@update:expanded="handleExpandedUpdate"
						@reorder-items="handleItemReorder"
						@add-item-from-drag="handleItemDrop"
						@show-drop-feedback="showDropFeedback"
						@item-dropped="showDropFeedback(false)"
						@view-packed="openPackedItems"
					/>
					<v-dialog v-model="show_packed_dialog" max-width="800px">
						<v-card>
							<v-card-title class="d-flex align-center">
								<span>{{ __("Packing List") }} ({{ packed_dialog_items.length }})</span>
								<v-spacer></v-spacer>
								<v-btn
									icon="mdi-close"
									variant="text"
									density="compact"
									@click="show_packed_dialog = false"
								></v-btn>
							</v-card-title>
							<v-divider></v-divider>
							<v-card-text>
								<v-alert type="warning" density="compact" class="mb-2">
									{{
										__(
											"For 'Product Bundle' items, Warehouse, Serial No and Batch No will be considered from the 'Packing List' table. If Warehouse and Batch No are same for all packing items for any 'Product Bundle' item, those values can be entered in the main Item table; values will be copied to 'Packing List' table.",
										)
									}}
								</v-alert>
								<v-data-table
									:headers="packedItemsHeaders"
									:items="packed_dialog_items"
									class="elevation-1"
									hide-default-footer
									density="compact"
								>
									<template v-slot:item.index="{ index }">
										{{ index + 1 }}
									</template>
									<template v-slot:item.qty="{ item }">
										{{ formatFloat(item.qty) }}
									</template>
									<template v-slot:item.rate="{ item }">
										<div class="currency-display">
											<span class="currency-symbol">{{
												currencySymbol(displayCurrency)
											}}</span>
											<span class="amount-value">{{ formatCurrency(item.rate) }}</span>
										</div>
									</template>
									<template v-slot:item.warehouse="{ item }">
										<v-text-field
											v-model="item.warehouse"
											hide-details
											density="compact"
										/>
									</template>
									<template v-slot:item.batch_no="{ item }">
										<v-text-field
											v-model="item.batch_no"
											hide-details
											density="compact"
										/>
									</template>
									<template v-slot:item.serial_no="{ item }">
										<v-text-field
											v-model="item.serial_no"
											hide-details
											density="compact"
										/>
									</template>
								</v-data-table>
							</v-card-text>
						</v-card>
					</v-dialog>
				</div>
			</div>
		</v-card>
		<!-- Payment Section -->
		<InvoiceSummary
			:pos_profile="pos_profile"
			:invoice_doc="invoice_doc"
			:total_qty="total_qty"
			:additional_discount="additional_discount"
			:additional_discount_percentage="additional_discount_percentage"
			:total_items_discount_amount="total_items_discount_amount"
			:subtotal="subtotal"
			:displayCurrency="displayCurrency"
			:formatFloat="formatFloat"
			:formatCurrency="formatCurrency"
			:currencySymbol="currencySymbol"
			:discount_percentage_offer_name="discount_percentage_offer_name"
			:isNumber="isNumber"
			:restaurant_add_items_context="restaurant_add_items_context"
			@update:additional_discount="(val) => (additional_discount = val)"
			@update:additional_discount_percentage="(val) => (additional_discount_percentage = val)"
			@update_discount_umount="update_discount_umount"
			@save-and-clear="handle_save_and_clear"
			@load-drafts="get_draft_invoices"
			@select-order="get_draft_orders"
			@show-orders="show_restaurant_orders"
			@submit-order="submit_restaurant_order"
			@cancel-sale="cancel_dialog = true"
			@open-returns="open_returns"
			@print-draft="print_draft_invoice"
			@show-payment="show_payment"
		/>
	</div>
</template>

<script>
/* global frappe, __ */
import format from "../../format";
import Customer from "./Customer.vue";
import RestaurantOrderType from "./RestaurantOrderType.vue";
import DeliveryCharges from "./DeliveryCharges.vue";
import PostingDateRow from "./PostingDateRow.vue";
import MultiCurrencyRow from "./MultiCurrencyRow.vue";
import CancelSaleDialog from "./CancelSaleDialog.vue";
import InvoiceSummary from "./InvoiceSummary.vue";
import ItemsTable from "./ItemsTable.vue";
import invoiceItemMethods from "./invoiceItemMethods";
import invoiceComputed from "./invoiceComputed";
import invoiceWatchers from "./invoiceWatchers";
import offerMethods from "./invoiceOfferMethods";
import shortcutMethods from "./invoiceShortcuts";

export default {
	name: "POSInvoice",
	mixins: [format],
	data() {
		return {
			// POS profile settings
			pos_profile: "",
			pos_opening_shift: "",
			stock_settings: "",
			invoice_doc: "",
			return_doc: "",
			customer: "",
			customer_info: "",
			customer_balance: 0,
			discount_amount: 0,
			additional_discount: 0,
			additional_discount_percentage: 0,
			total_tax: 0,
			items: [], // List of invoice items
			packed_items: [], // Packed items for bundles
			packed_dialog_items: [], // Packed items displayed in dialog
			show_packed_dialog: false, // Packing list dialog visibility
                        posOffers: [], // All available offers
                        posa_offers: [], // Offers applied to this invoice
                        posa_coupons: [], // Coupons applied
                        isApplyingOffer: false, // Flag to prevent offer watcher loops
                        allItems: [], // All items for offer logic
			discount_percentage_offer_name: null, // Track which offer is applied
			invoiceTypes: ["Invoice", "Order"], // Types of invoices
			invoiceType: "Invoice", // Current invoice type
			itemsPerPage: 1000, // Items per page in table
			expanded: [], // Array of expanded row IDs
			singleExpand: true, // Only one row expanded at a time
			cancel_dialog: false, // Cancel dialog visibility
			float_precision: 6, // Float precision for calculations
			currency_precision: 6, // Currency precision for display
			new_line: false, // Add new line for item
			available_stock_cache: {},
			delivery_charges: [], // List of delivery charges
			delivery_charges_rate: 0, // Selected delivery charge rate
			selected_delivery_charge: "", // Selected delivery charge object
			invoice_posting_date: false, // Posting date dialog
			posting_date: frappe.datetime.nowdate(), // Invoice posting date
			posting_date_display: "", // Display value for date picker
			items_headers: [],
			packedItemsHeaders: [
				{ title: __("No."), key: "index" },
				{ title: __("Parent Item"), key: "parent_item" },
				{ title: __("Item Code"), key: "item_code" },
				{ title: __("Description"), key: "item_name" },
				{ title: __("Qty"), key: "qty" },
				{ title: __("Rate"), key: "rate" },
				{ title: __("Warehouse"), key: "warehouse" },
				{ title: __("Batch"), key: "batch_no" },
				{ title: __("Serial"), key: "serial_no" },
			],
			selected_currency: "", // Currently selected currency
			exchange_rate: 1, // Current exchange rate
			conversion_rate: 1, // Currency to company rate
			exchange_rate_date: frappe.datetime.nowdate(), // Date of fetched exchange rate
			company: null, // Company doc with default currency
			available_currencies: [], // List of available currencies
			price_lists: [], // Available selling price lists
			selected_price_list: "", // Currently selected price list
			price_list_currency: "", // Currency of the selected price list
			selected_columns: [], // Selected columns for items table
			temp_selected_columns: [], // Temporary array for column selection
			available_columns: [], // All available columns
			show_column_selector: false, // Column selector dialog visibility
			invoiceHeight: null,
			// Restaurant order fields
			restaurant_order_types: [],
			available_tables: [],
			selected_order_type: null, // Always start with null - no default selection
			selected_table: null,
			order_status: null,
			restaurant_add_items_context: null, // Store context for updating existing orders
		};
	},

	components: {
		Customer,
		RestaurantOrderType,
		DeliveryCharges,
		PostingDateRow,
		MultiCurrencyRow,
		InvoiceSummary,
		CancelSaleDialog,
		ItemsTable,
	},
	computed: {
		...invoiceComputed,
		isDarkTheme() {
			return this.$theme.current === "dark";
		},
		isEditingExistingOrder() {
			// Check if we're editing an existing order (has a name and is in restaurant mode)
			return !!(
				this.pos_profile?.posa_enable_restaurant_mode &&
				this.invoice_doc?.name &&
				this.invoiceType === "Order"
			);
		},
	},

	methods: {
		...shortcutMethods,
		...offerMethods,
		...invoiceItemMethods,
		initializeItemsHeaders() {
			// Define all available columns - optimized for compact cart view
			this.available_columns = [
				{ title: __("Item"), align: "start", sortable: true, key: "item_name", required: true, width: "40%" },
				{ title: __("Qty"), key: "qty", align: "center", required: true, width: "15%" },
				{ title: __("Rate"), key: "rate", align: "end", required: true, width: "20%" },
				{ title: __("Total"), key: "amount", align: "end", required: true, width: "25%" },
				{ title: __("UOM"), key: "uom", align: "start", required: false },
				{ title: __("Discount %"), key: "discount_value", align: "start", required: false },
				{ title: __("Discount Amount"), key: "discount_amount", align: "start", required: false },
				{ title: __("Offer?"), key: "posa_is_offer", align: "center", required: false },
			];

			// Initialize selected columns if empty
			if (!this.selected_columns || this.selected_columns.length === 0) {
				// By default, select only essential columns for compact cart view
				this.selected_columns = this.available_columns
					.filter((col) => {
						if (col.required) return true;
						// Hide optional columns by default for compact view
						return false;
					})
					.map((col) => col.key);
			}

			// Generate headers based on selected columns
			this.updateHeadersFromSelection();
		},
		// Handle item dropped from ItemsSelector to ItemsTable
		handleItemDrop(item) {
			console.log("Item dropped:", item);

			// Use the existing add_item method to add the dropped item
			this.add_item(item);

			// Show success feedback
			this.eventBus.emit("show_message", {
				title: __(`Item {0} added to invoice`, [item.item_name]),
				color: "success",
			});
		},

		// Show visual feedback when item is being dragged over drop zone
		showDropFeedback(isDragging) {
			// Add visual feedback class to the items table
			const itemsTable = this.$el.querySelector(".modern-items-table");
			if (itemsTable) {
				if (isDragging) {
					itemsTable.classList.add("drag-over");
				} else {
					itemsTable.classList.remove("drag-over");
				}
			}
		},
		openPackedItems(bundle_id) {
			this.packed_dialog_items = this.packed_items.filter((it) => it.bundle_id === bundle_id);
			this.show_packed_dialog = true;
		},
		toggleColumnSelection() {
			// Create a copy of selected columns for temporary editing
			this.temp_selected_columns = [...this.selected_columns];
			this.show_column_selector = true;
		},

		cancelColumnSelection() {
			// Discard changes
			this.show_column_selector = false;
		},

		updateHeadersFromSelection() {
			// Generate headers based on selected columns (without closing dialog)
			this.items_headers = this.available_columns.filter(
				(col) => this.selected_columns.includes(col.key) || col.required,
			);
		},

		updateSelectedColumns() {
			// Apply the temporary selection
			this.selected_columns = [...this.temp_selected_columns];

			// Add required columns if they're not already included
			const requiredKeys = this.available_columns.filter((col) => col.required).map((col) => col.key);

			requiredKeys.forEach((key) => {
				if (!this.selected_columns.includes(key)) {
					this.selected_columns.push(key);
				}
			});

			// Update headers
			this.updateHeadersFromSelection();

			// Save preferences
			this.saveColumnPreferences();

			// Close dialog
			this.show_column_selector = false;
		},

		saveColumnPreferences() {
			try {
				localStorage.setItem("posawesome_selected_columns", JSON.stringify(this.selected_columns));
			} catch (e) {
				console.error("Failed to save column preferences:", e);
			}
		},

		loadColumnPreferences() {
			try {
				const saved = localStorage.getItem("posawesome_selected_columns");
				if (saved) {
					this.selected_columns = JSON.parse(saved);
				}
			} catch (e) {
				console.error("Failed to load column preferences:", e);
			}
		},

		saveInvoiceHeight() {
			if (this.$refs.invoiceCard) {
				this.invoiceHeight = this.$refs.invoiceCard.clientHeight + "px";
				try {
					localStorage.setItem("posawesome_invoice_height", this.invoiceHeight);
				} catch (e) {
					console.error("Failed to save invoice height:", e);
				}
			}
		},

		loadInvoiceHeight() {
			try {
				const saved = localStorage.getItem("posawesome_invoice_height");
				if (saved) {
					this.invoiceHeight = saved;
				} else {
					this.invoiceHeight =
						getComputedStyle(document.documentElement).getPropertyValue("--container-height") ||
						"68vh";
				}
			} catch (e) {
				console.error("Failed to load invoice height:", e);
				this.invoiceHeight =
					getComputedStyle(document.documentElement).getPropertyValue("--container-height") ||
					"68vh";
			}
		},
		makeid(length) {
			let result = "";
			const characters = "abcdefghijklmnopqrstuvwxyz0123456789";
			const charactersLength = characters.length;
			for (var i = 0; i < length; i++) {
				result += characters.charAt(Math.floor(Math.random() * charactersLength));
			}
			return result;
		},

		handleExpandedUpdate(ids) {
			this.expanded = Array.isArray(ids) ? ids.slice(-1) : [];
		},

		print_draft_invoice() {
			if (!this.pos_profile.posa_allow_print_draft_invoices) {
				this.eventBus.emit("show_message", {
					title: __(`You are not allowed to print draft invoices`),
					color: "error",
				});
				return;
			}
			let invoice_name = this.invoice_doc.name;
			frappe.run_serially([
				() => {
					const invoice_doc = this.save_and_clear_invoice();
					invoice_name = invoice_doc.name ? invoice_doc.name : invoice_name;
				},
				() => {
					this.load_print_page(invoice_name);
				},
			]);
		},
		async set_delivery_charges() {
			var vm = this;
			if (!this.pos_profile || !this.customer || !this.pos_profile.posa_use_delivery_charges) {
				this.delivery_charges = [];
				this.delivery_charges_rate = 0;
				this.selected_delivery_charge = "";
				return;
			}
			this.delivery_charges_rate = 0;
			this.selected_delivery_charge = "";
			try {
				const r = await frappe.call({
					method: "posawesome.posawesome.api.offers.get_applicable_delivery_charges",
					args: {
						company: this.pos_profile.company,
						pos_profile: this.pos_profile.name,
						customer: this.customer,
					},
				});
				if (r.message && r.message.length) {
					console.log(r.message);
					vm.delivery_charges = r.message;
				}
			} catch (error) {
				console.error("Failed to fetch delivery charges", error);
			}
		},
		deliveryChargesFilter(itemText, queryText, itemRow) {
			const item = itemRow.raw;
			console.log("dl charges", item);
			const textOne = item.name.toLowerCase();
			const searchText = queryText.toLowerCase();
			return textOne.indexOf(searchText) > -1;
		},
		update_delivery_charges() {
			if (this.selected_delivery_charge) {
				this.delivery_charges_rate = this.selected_delivery_charge.rate;
			} else {
				this.delivery_charges_rate = 0;
			}
		},
		updatePostingDate(date) {
			if (!date) return;
			this.posting_date = date;
			this.$forceUpdate();
		},
		// Override setFormatedFloat for qty field to handle stock limits and return mode
		setFormatedQty(item, field_name, precision, no_negative, value) {
			// Parse and set the value using the mixin's formatter
			let parsedValue = this.setFormatedFloat(item, field_name, precision, no_negative, value);

			// CRITICAL FIX: Only enforce stock limits for stock items
			if (item.is_stock_item && item.max_qty !== undefined && this.flt(item[field_name]) > this.flt(item.max_qty)) {
				const blockSale =
					!this.stock_settings.allow_negative_stock ||
					this.pos_profile.posa_block_sale_beyond_available_qty;
				if (blockSale) {
					item[field_name] = item.max_qty;
					parsedValue = item.max_qty;
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

			// Ensure negative value for return invoices
			if (this.isReturnInvoice && parsedValue > 0) {
				parsedValue = -Math.abs(parsedValue);
				item[field_name] = parsedValue;
			}

			// Recalculate stock quantity with the adjusted value
			this.calc_stock_qty(item, item[field_name]);
			if (field_name === "qty" && item.is_bundle) {
				this.packed_items
					.filter((it) => it.bundle_id === item.bundle_id)
					.forEach((ch) => {
						ch.qty = item.qty * (ch.child_qty_per_bundle || 1);
						this.calc_stock_qty(ch, ch.qty);
					});
			}
			return parsedValue;
		},
		async fetch_available_currencies() {
			try {
				console.log("Fetching available currencies...");
				const r = await frappe.call({
					method: "posawesome.posawesome.api.invoices.get_available_currencies",
				});

				if (r.message) {
					console.log("Received currencies:", r.message);

					// Get base currency for reference
					const baseCurrency = this.pos_profile.currency;

					// Create simple currency list with just names
					this.available_currencies = r.message.map((currency) => {
						return {
							value: currency.name,
							title: currency.name,
						};
					});

					// Sort currencies - base currency first, then others alphabetically
					this.available_currencies.sort((a, b) => {
						if (a.value === baseCurrency) return -1;
						if (b.value === baseCurrency) return 1;
						return a.value.localeCompare(b.value);
					});

					// Set default currency if not already set
					if (!this.selected_currency) {
						this.selected_currency = baseCurrency;
					}

					return this.available_currencies;
				}

				return [];
			} catch (error) {
				console.error("Error fetching currencies:", error);
				// Set default currency as fallback
				const defaultCurrency = this.pos_profile.currency;
				this.available_currencies = [
					{
						value: defaultCurrency,
						title: defaultCurrency,
					},
				];
				this.selected_currency = defaultCurrency;
				return this.available_currencies;
			}
		},

		async fetch_price_lists() {
			if (this.pos_profile.posa_enable_price_list_dropdown) {
				try {
					const r = await frappe.call({
						method: "posawesome.posawesome.api.utilities.get_selling_price_lists",
					});
					if (r && r.message) {
						this.price_lists = r.message.map((pl) => pl.name);
					}
				} catch (error) {
					console.error("Failed fetching price lists", error);
					this.price_lists = [this.pos_profile.selling_price_list];
				}
			} else {
				// Fallback to the price list defined in the POS Profile
				this.price_lists = [this.pos_profile.selling_price_list];
			}

			if (!this.selected_price_list) {
				this.selected_price_list = this.pos_profile.selling_price_list;
			}

			// Fetch and store currency for the applied price list
			try {
				const r = await frappe.call({
					method: "posawesome.posawesome.api.invoices.get_price_list_currency",
					args: { price_list: this.selected_price_list },
				});
				if (r && r.message) {
					this.price_list_currency = r.message;
				}
			} catch (error) {
				console.error("Failed fetching price list currency", error);
			}

			return this.price_lists;
		},

		async update_currency(currency) {
			if (!currency) return;
			this.selected_currency = currency;
			await this.update_currency_and_rate();
		},

		update_exchange_rate() {
			if (!this.exchange_rate || this.exchange_rate <= 0) {
				this.exchange_rate = 1;
			}

			// Emit currency update
			this.eventBus.emit("update_currency", {
				currency: this.selected_currency || this.pos_profile.currency,
				exchange_rate: this.exchange_rate,
			});

			this.update_item_rates();
		},

		update_conversion_rate() {
			if (!this.conversion_rate || this.conversion_rate <= 0) {
				this.conversion_rate = 1;
			}

			this.sync_exchange_rate();
		},

		update_item_rates() {
			console.log("Updating item rates with exchange rate:", this.exchange_rate);

			this.items.forEach((item) => {
				// Set skip flag to avoid double calculations
				item._skip_calc = true;

				// First ensure base rates exist for all items
				if (!item.base_rate) {
					console.log(`Setting base rates for ${item.item_code} for the first time`);
					const baseCurrency = this.price_list_currency || this.pos_profile.currency;
					if (this.selected_currency === baseCurrency) {
						// When in base currency, base rates = displayed rates
						item.base_rate = item.rate;
						item.base_price_list_rate = item.price_list_rate;
						item.base_discount_amount = item.discount_amount || 0;
					} else {
						// When in another currency, calculate base rates
						item.base_rate = item.rate / this.exchange_rate;
						item.base_price_list_rate = item.price_list_rate / this.exchange_rate;
						item.base_discount_amount = (item.discount_amount || 0) / this.exchange_rate;
					}
				}

				// Currency conversion logic
				const baseCurrency = this.price_list_currency || this.pos_profile.currency;
				if (this.selected_currency === baseCurrency) {
					// When switching back to default currency, restore from base rates
					console.log(`Restoring rates for ${item.item_code} from base rates`);
					item.price_list_rate = item.base_price_list_rate;
					item.rate = item.base_rate;
					item.discount_amount = item.base_discount_amount;
				} else if (item.original_currency === this.selected_currency) {
					// When selected currency matches the price list currency,
					// no conversion should be applied
					console.log(`Using original currency rates for ${item.item_code}`);
					item.price_list_rate = item.base_price_list_rate;
					item.rate = item.base_rate;
					item.discount_amount = item.base_discount_amount;
				} else {
					// When switching to another currency, convert from base rates
					console.log(`Converting rates for ${item.item_code} to ${this.selected_currency}`);

					// Convert base currency values to the selected currency
					const converted_price = this.flt(
						item.base_price_list_rate * this.exchange_rate,
						this.currency_precision,
					);
					const converted_rate = this.flt(
						item.base_rate * this.exchange_rate,
						this.currency_precision,
					);
					const converted_discount = this.flt(
						item.base_discount_amount * this.exchange_rate,
						this.currency_precision,
					);

					// Ensure we don't set values to 0 if they're just very small
					item.price_list_rate = converted_price < 0.000001 ? 0 : converted_price;
					item.rate = converted_rate < 0.000001 ? 0 : converted_rate;
					item.discount_amount = converted_discount < 0.000001 ? 0 : converted_discount;
				}

				// Always recalculate final amounts
				item.amount = this.flt(item.qty * item.rate, this.currency_precision);
				item.base_amount = this.flt(item.qty * item.base_rate, this.currency_precision);

				console.log(`Updated rates for ${item.item_code}:`, {
					price_list_rate: item.price_list_rate,
					base_price_list_rate: item.base_price_list_rate,
					rate: item.rate,
					base_rate: item.base_rate,
					discount: item.discount_amount,
					base_discount: item.base_discount_amount,
					amount: item.amount,
					base_amount: item.base_amount,
				});

				// Apply any other pricing rules if needed
				this.calc_item_price(item);
			});

			// Force UI update after all calculations
			this.$forceUpdate();
		},

		formatCurrency(value, precision = null) {
			const prec = precision != null ? precision : this.currency_precision;
			return this.$options.mixins[0].methods.formatCurrency.call(this, value, prec);
		},

		flt(value, precision = null) {
			// Enhanced float handling for small numbers
			if (precision === null) {
				precision = this.float_precision;
			}

			const _value = Number(value);
			if (isNaN(_value)) {
				return 0;
			}

			// Handle very small numbers to prevent them from becoming 0
			if (Math.abs(_value) < 0.000001) {
				return _value;
			}

			return Number((_value || 0).toFixed(precision));
		},

		// Update currency and exchange rate when currency is changed
		async update_currency_and_rate() {
			if (!this.selected_currency) return;

			const companyCurrency =
				(this.company && this.company.default_currency) || this.pos_profile.currency;
			const priceListCurrency = this.price_list_currency || companyCurrency;

			try {
				// Price list currency to selected currency rate
				if (this.selected_currency === priceListCurrency) {
					this.exchange_rate = 1;
				} else {
					const r = await frappe.call({
						method: "posawesome.posawesome.api.invoices.fetch_exchange_rate_pair",
						args: {
							from_currency: priceListCurrency,
							to_currency: this.selected_currency,
						},
					});
					if (r && r.message) {
						this.exchange_rate = r.message.exchange_rate;
					}
				}

				// Selected currency to company currency rate
				if (this.selected_currency === companyCurrency) {
					this.conversion_rate = 1;
					this.exchange_rate_date = this.formatDateForBackend(this.posting_date_display);
				} else {
					const r2 = await frappe.call({
						method: "posawesome.posawesome.api.invoices.fetch_exchange_rate_pair",
						args: {
							from_currency: this.selected_currency,
							to_currency: companyCurrency,
						},
					});
					if (r2 && r2.message) {
						this.conversion_rate = r2.message.exchange_rate;
						this.exchange_rate_date = r2.message.date;
						const posting_backend = this.formatDateForBackend(this.posting_date_display);
						if (this.exchange_rate_date && posting_backend !== this.exchange_rate_date) {
							this.eventBus.emit("show_message", {
								title: __(
									"Exchange rate date " +
										this.exchange_rate_date +
										" differs from posting date " +
										posting_backend,
								),
								color: "warning",
							});
						}
					}
				}
			} catch (error) {
				console.error("Error updating currency:", error);
				this.eventBus.emit("show_message", {
					title: "Error updating currency",
					color: "error",
				});
			}

			this.sync_exchange_rate();

			// If items already exist, update the invoice on the server so that
			// the document currency and rates remain consistent
			if (this.items.length) {
				const doc = this.get_invoice_doc();
				doc.currency = this.selected_currency;
				doc.price_list_currency = priceListCurrency || this.pos_profile.currency;
				doc.conversion_rate = this.conversion_rate;
				doc.plc_conversion_rate = this.exchange_rate;
				try {
					await this.update_invoice(doc);
				} catch (error) {
					console.error("Error updating invoice currency:", error);
					this.eventBus.emit("show_message", {
						title: "Error updating currency",
						color: "error",
					});
				}
			}
		},

		async update_exchange_rate_on_server() {
			if (this.conversion_rate) {
				if (!this.items.length) {
					this.sync_exchange_rate();
					return;
				}

				const doc = this.get_invoice_doc();
				doc.conversion_rate = this.conversion_rate;
				doc.plc_conversion_rate = this.exchange_rate;
				try {
					const resp = await this.update_invoice(doc);
					if (resp && resp.exchange_rate_date) {
						this.exchange_rate_date = resp.exchange_rate_date;
						const posting_backend = this.formatDateForBackend(this.posting_date_display);
						if (posting_backend !== this.exchange_rate_date) {
							this.eventBus.emit("show_message", {
								title: __(
									"Exchange rate date " +
										this.exchange_rate_date +
										" differs from posting date " +
										posting_backend,
								),
								color: "warning",
							});
						}
					}
					this.sync_exchange_rate();
				} catch (error) {
					console.error("Error updating exchange rate:", error);
					this.eventBus.emit("show_message", {
						title: "Error updating exchange rate",
						color: "error",
					});
				}
			}
		},

		sync_exchange_rate() {
			if (!this.exchange_rate || this.exchange_rate <= 0) {
				this.exchange_rate = 1;
			}
			if (!this.conversion_rate || this.conversion_rate <= 0) {
				this.conversion_rate = 1;
			}

			// Emit currency update
			this.eventBus.emit("update_currency", {
				currency: this.selected_currency || this.pos_profile.currency,
				exchange_rate: this.exchange_rate,
				conversion_rate: this.conversion_rate,
			});

			this.update_item_rates();
		},

		// Add new rounding function
		roundAmount(amount) {
			// Respect POS Profile setting to disable rounding
			if (this.pos_profile.disable_rounded_total) {
				// Use configured precision without applying rounding
				return this.flt(amount, this.currency_precision);
			}
			// If multi-currency is enabled and selected currency is different from base currency
			const baseCurrency = this.price_list_currency || this.pos_profile.currency;
			if (this.pos_profile.posa_allow_multi_currency && this.selected_currency !== baseCurrency) {
				// For multi-currency, just keep 2 decimal places without rounding to nearest integer
				return this.flt(amount, 2);
			}
			// For base currency or when multi-currency is disabled, round to nearest integer
			return Math.round(amount);
		},

		// Increase quantity of an item (handles return logic)
		add_one(item) {
			if (this.isReturnInvoice) {
				// For returns, make quantity more negative
				item.qty--;
			} else {
				const proposed = item.qty + 1;
				
				// CRITICAL FIX: Only apply stock validation to stock items
				if (item.is_stock_item) {
					const blockSale =
						!this.stock_settings.allow_negative_stock ||
						this.pos_profile.posa_block_sale_beyond_available_qty;
					if (blockSale && item.max_qty !== undefined && proposed > item.max_qty) {
						item.qty = item.max_qty;
						this.calc_stock_qty(item, item.qty);
						this.eventBus.emit("show_message", {
							title: __("Maximum available quantity is {0}. Quantity adjusted to match stock.", [
								this.formatFloat(item.max_qty),
							]),
							color: "error",
						});
						return;
					}
				}
				item.qty = proposed;
			}
			if (item.qty == 0) {
				this.remove_item(item);
			}
			this.calc_stock_qty(item, item.qty);
			if (item.is_bundle) {
				this.packed_items
					.filter((it) => it.bundle_id === item.bundle_id)
					.forEach((ch) => {
						ch.qty = item.qty * (ch.child_qty_per_bundle || 1);
						this.calc_stock_qty(ch, ch.qty);
					});
			}
			this.$forceUpdate();
		},

		// Decrease quantity of an item (handles return logic)
		subtract_one(item) {
			if (this.isReturnInvoice) {
				// For returns, move quantity toward zero
				item.qty++;
			} else {
				item.qty--;
			}
			if (item.qty == 0) {
				this.remove_item(item);
			}
			this.calc_stock_qty(item, item.qty);
			if (item.is_bundle) {
				this.packed_items
					.filter((it) => it.bundle_id === item.bundle_id)
					.forEach((ch) => {
						ch.qty = item.qty * (ch.child_qty_per_bundle || 1);
						this.calc_stock_qty(ch, ch.qty);
					});
			}
			this.$forceUpdate();
		},

		// Handle item reordering from drag and drop
		handleItemReorder(reorderData) {
			const { fromIndex, toIndex } = reorderData;

			if (fromIndex === toIndex) return;

			// Create a copy of the items array
			const newItems = [...this.items];

			// Remove the item from its original position
			const [movedItem] = newItems.splice(fromIndex, 1);

			// Insert the item at its new position
			newItems.splice(toIndex, 0, movedItem);

			// Update the items array
			this.items = newItems;

			// Show success feedback
			this.eventBus.emit("show_message", {
				title: __("Item order updated"),
				color: "success",
			});

			// Optionally, you can also update the idx field for each item
			this.items.forEach((item, index) => {
				item.idx = index + 1;
			});
		},

		// Restaurant order methods
		async fetch_restaurant_order_types() {
			if (!this.pos_profile.posa_enable_restaurant_mode) {
				return;
			}
			
			try {
				const r = await frappe.call({
					method: "posawesome.posawesome.api.restaurant_orders.get_restaurant_order_types",
				});
				if (r.message) {
					this.restaurant_order_types = r.message;
					// Do NOT set default order type - keep it empty to force user selection
					// Order Type should be mandatory and user must select it explicitly
				}
			} catch (error) {
				console.error("Failed to fetch restaurant order types", error);
			}
		},

		async fetch_available_tables() {
			if (!this.pos_profile.posa_enable_restaurant_mode) {
				return;
			}
			
			try {
				const r = await frappe.call({
					method: "posawesome.posawesome.api.restaurant_orders.get_available_tables",
				});
				if (r.message) {
					this.available_tables = r.message;
				}
			} catch (error) {
				console.error("Failed to fetch available tables", error);
			}
		},

		update_order_type() {
			// Clear table selection if new order type doesn't require table
			if (!this.selected_order_type || !this.selected_order_type.requires_table) {
				this.selected_table = null;
			}
			// Refresh available tables when order type changes
			if (this.selected_order_type && this.selected_order_type.requires_table) {
				this.fetch_available_tables();
			}
		},

		update_table_selection() {
			// Table selection updated
			console.log("Table selected:", this.selected_table);
		},

		show_restaurant_orders() {
			// Emit event to show restaurant orders dialog
			this.eventBus.emit("open_restaurant_orders");
		},

		handle_save_and_clear() {
			// Route to correct method based on context
			if (this.pos_profile.posa_enable_restaurant_mode) {
				if (this.restaurant_add_items_context && this.restaurant_add_items_context.is_updating_order) {
					console.log("Routing to update_existing_order for order update");
					this.update_existing_order();
				} else {
					console.log("Routing to create_new_restaurant_order for new restaurant order");
					this.create_new_restaurant_order();
				}
			} else {
				console.log("Routing to save_and_clear_invoice for regular POS");
				this.save_and_clear_invoice();
			}
		},

		async submit_restaurant_order() {
			// Debug logging
			console.log("=== SUBMIT RESTAURANT ORDER DEBUG ===");
			console.log("restaurant_add_items_context:", this.restaurant_add_items_context);
			console.log("is_updating_order:", this.restaurant_add_items_context?.is_updating_order);
			console.log("original_order:", this.restaurant_add_items_context?.original_order);
			console.log("==========================================");
			
			// Validate requirements first
			if (!this.validate_restaurant_selection()) {
				return;
			}

			if (!this.customer) {
				this.eventBus.emit("show_message", {
					title: __("Please select a customer"),
					color: "error",
				});
				return;
			}

			if (!this.items.length) {
				this.eventBus.emit("show_message", {
					title: __("Please add items to the order"),
					color: "error",
				});
				return;
			}

			try {
				// Check if we're updating an existing order
				if (this.restaurant_add_items_context && this.restaurant_add_items_context.is_updating_order) {
					console.log("Taking update path...");
					await this.update_existing_order();
				} else {
					console.log("Taking create new order path...");
					await this.create_new_restaurant_order();
				}
			} catch (error) {
				console.error("Error submitting restaurant order:", error);
				this.eventBus.emit("show_message", {
					title: __("Error submitting order"),
					color: "error",
				});
			}
		},

		async create_new_restaurant_order() {
			const doc = this.get_invoice_doc();
			
			if (doc.name) {
				// Update existing order (keep as draft)
				const order_doc = this.update_invoice(doc);
				
				if (order_doc && order_doc.name) {
					this.eventBus.emit("show_message", {
						title: __("Order {0} updated successfully as draft", [order_doc.name]),
						color: "success",
					});
					
					// Clear the current invoice after successful update
					this.clear_invoice();
				}
			} else {
				// Create new restaurant order as draft (this already handles KOT printing)
				const order_doc = this.create_restaurant_order(doc);
				
				if (order_doc && order_doc.name) {
					this.eventBus.emit("show_message", {
						title: __("Draft order {0} created successfully", [order_doc.name]),
						color: "success",
					});
					
					// Clear the current invoice after successful creation
					this.clear_invoice();
				}
			}
		},

		async update_existing_order() {
			const originalOrderName = this.restaurant_add_items_context.original_order;
			
			// Get the current items from the cart
			const currentItems = this.items.map(item => ({
				item_code: item.item_code,
				item_name: item.item_name,
				qty: item.qty,
				rate: item.rate,
				uom: item.uom,
				warehouse: item.warehouse,
				description: item.description,
				discount_percentage: item.discount_percentage || 0,
				discount_amount: item.discount_amount || 0
			}));

			console.log("Adding items to order:", originalOrderName, "with items:", currentItems);

			// Call the appropriate API based on order status
			// For draft orders, use the simpler draft API
			// For submitted orders, use the more complex submitted API
			const isDraftOrder = this.restaurant_add_items_context.order_status === 0;
			const apiMethod = isDraftOrder 
				? "posawesome.posawesome.api.restaurant_orders.add_items_to_draft_order"
				: "posawesome.posawesome.api.restaurant_orders.add_items_to_existing_order";
			
			console.log(`Using API method: ${apiMethod} for ${isDraftOrder ? 'draft' : 'submitted'} order`);
			
			const response = await frappe.call({
				method: apiMethod,
				args: {
					order_name: originalOrderName,
					items_data: currentItems,
				},
			});

			if (response.message) {
				this.eventBus.emit("show_message", {
					title: __("Added {0} new items to order {1} successfully", [currentItems.length, originalOrderName]),
					color: "success",
				});

				// Print KOT for the new items
				try {
					const { printKot } = await import('../../plugins/kot_print.js');
					const kotData = {
						order_name: originalOrderName,
						table_number: this.restaurant_add_items_context.table_number,
						order_type: this.restaurant_add_items_context.order_type,
						items: currentItems.map(item => ({
							item_name: item.item_name,
							qty: item.qty,
							notes: item.notes || ''
						})),
						timestamp: frappe.datetime.now_datetime(),
						is_additional: true // Flag to indicate this is additional items KOT
					};
					await printKot(kotData);
				} catch (error) {
					console.error("Error printing KOT for additional items:", error);
				}

				// Clear the current invoice and context after successful update
				this.clear_invoice();
				this.restaurant_add_items_context = null;
			}
		},

		get_restaurant_invoice_doc() {
			const doc = this.get_invoice_doc();
			
			// Add restaurant-specific fields
			if (this.selected_order_type) {
				doc.restaurant_order_type = this.selected_order_type.name;
			}
			
			if (this.selected_table) {
				doc.table_number = this.selected_table.table_number;
			}
			
			return doc;
		},

		validate_restaurant_selection() {
			if (!this.pos_profile.posa_enable_restaurant_mode) {
				return true;
			}
			
			if (!this.selected_order_type) {
				this.eventBus.emit("show_message", {
					title: __("Please select an Order Type before proceeding"),
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
			
			return true;
		},

		clear_restaurant_selection() {
			this.selected_order_type = null;
			this.selected_table = null;
			this.order_status = null;
			this.restaurant_add_items_context = null;
		},

		async set_restaurant_context(context) {
			try {
				console.log("=== SET RESTAURANT CONTEXT DEBUG ===");
				console.log("Incoming context:", context);
				console.log("is_updating_order flag:", context.is_updating_order);
				console.log("=====================================");
				
				// First, clear any existing cart to start fresh
				this.clear_invoice();
				
				// Store the context AFTER clearing (so it doesn't get cleared)
				this.restaurant_add_items_context = context;
				console.log("Stored context after clear:", this.restaurant_add_items_context);
				
				// Set customer if provided
				if (context.customer) {
					// Emit update_customer event with proper format
					this.eventBus.emit("update_customer", context.customer);
				}
				
				// Get and set order type data
				if (context.order_type) {
					const orderTypes = await frappe.call({
						method: "posawesome.posawesome.api.restaurant_orders.get_restaurant_order_types"
					});
					
					if (orderTypes.message) {
						const orderType = orderTypes.message.find(ot => ot.order_type_name === context.order_type);
						if (orderType) {
							// Set the order type directly
							this.selected_order_type = orderType;
							console.log("Order type set:", orderType);
						}
					}
				}
				
				// Get and set table data if provided
				if (context.table_number) {
					const tables = await frappe.call({
						method: "posawesome.posawesome.doctype.restaurant_table.restaurant_table.get_all_tables"
					});
					
					if (tables.message) {
						const table = tables.message.find(t => t.table_number === context.table_number);
						if (table) {
							// Add the table_display field that the component expects
							table.table_display = table.table_name 
								? `${table.table_number} - ${table.table_name}`
								: table.table_number;
							
							// Set the table directly
							this.selected_table = table;
							console.log("Table set:", table);
						} else {
							console.warn("Table not found:", context.table_number);
						}
					}
				}
				
				// Wait a bit for the components to update, then force refresh
				setTimeout(() => {
					this.$forceUpdate();
				}, 100);
				
				console.log("Restaurant context set:", {
					order_type: this.selected_order_type?.order_type_name,
					table: this.selected_table?.table_number,
					customer: context.customer_name,
					is_updating_order: context.is_updating_order
				});
				
			} catch (error) {
				console.error("Error setting restaurant context:", error);
			}
		},
	},

	mounted() {
		// Load saved column preferences
		this.loadColumnPreferences();
		// Restore saved invoice height
		this.loadInvoiceHeight();
		this.eventBus.on("item-drag-start", () => {
			this.showDropFeedback(true);
		});
		this.eventBus.on("item-drag-end", () => {
			this.showDropFeedback(false);
		});

		// Register event listeners for POS profile, items, customer, offers, etc.
		this.eventBus.on("register_pos_profile", (data) => {
			this.pos_profile = data.pos_profile;
			this.company = data.company || null;
			this.customer = data.pos_profile.customer;
			this.pos_opening_shift = data.pos_opening_shift;
			this.stock_settings = data.stock_settings;
			const prec = parseInt(data.pos_profile.posa_decimal_precision);
			if (!isNaN(prec)) {
				this.float_precision = prec;
				this.currency_precision = prec;
			}
			// In restaurant mode, always use "Order" type to create Sales Orders
			if (this.pos_profile.posa_enable_restaurant_mode) {
				this.invoiceType = "Order";
				this.invoiceTypes = ["Order"]; // Restrict to only Order type in restaurant mode
			} else {
				this.invoiceType = this.pos_profile.posa_default_sales_order ? "Order" : "Invoice";
			}
			this.initializeItemsHeaders();

			// Add this block to handle currency initialization
			if (this.pos_profile.posa_allow_multi_currency) {
				this.fetch_available_currencies()
					.then(async () => {
						// Set default currency after currencies are loaded
						this.selected_currency = this.pos_profile.currency;
						// Fetch proper exchange rate from server
						await this.update_currency_and_rate();
					})
					.catch((error) => {
						console.error("Error initializing currencies:", error);
						this.eventBus.emit("show_message", {
							title: __("Error loading currencies"),
							color: "error",
						});
					});
			}

			this.fetch_price_lists();
			this.update_price_list();
			
			// Initialize restaurant features if enabled
			if (this.pos_profile.posa_enable_restaurant_mode) {
				this.fetch_restaurant_order_types();
				this.fetch_available_tables();
			}
		});
		this.eventBus.on("add_item", (item) => {
			this.add_item(item);
		});
		this.eventBus.on("update_customer", (customer) => {
			this.customer = customer;
		});
		this.eventBus.on("fetch_customer_details", () => {
			this.fetch_customer_details();
		});
		this.eventBus.on("clear_invoice", () => {
			this.clear_invoice();
		});
		this.eventBus.on("validate_restaurant_selection", () => {
			this.validate_restaurant_selection();
		});
		this.eventBus.on("set_restaurant_context", (context) => {
			this.set_restaurant_context(context);
		});
		this.eventBus.on("load_invoice", (data) => {
			this.load_invoice(data);
		});
		this.eventBus.on("load_order", (data) => {
			this.new_order(data);
			// this.eventBus.emit("set_pos_coupons", data.posa_coupons);
		});
		this.eventBus.on("change_invoice_type", (type) => {
			console.log("Changing invoice type to:", type);
			this.invoiceType = type;
			if (type === "Invoice") {
				this.invoiceTypes = ["Invoice"];
			} else if (type === "Order") {
				this.invoiceTypes = ["Order"];
			}
			// Force UI update
			this.$forceUpdate();
			console.log("Invoice type changed and UI updated:", {
				invoiceType: this.invoiceType,
				invoiceTypes: this.invoiceTypes
			});
		});
		this.eventBus.on("set_offers", (data) => {
			this.posOffers = data;
		});
		this.eventBus.on("update_invoice_offers", (data) => {
			this.updateInvoiceOffers(data);
		});
		this.eventBus.on("update_invoice_coupons", (data) => {
			this.posa_coupons = data;
			this.handelOffers();
		});
		this.eventBus.on("set_all_items", (data) => {
			this.allItems = data;
			this.items.forEach((item) => {
				this.update_item_detail(item);
			});
		});
		this.eventBus.on("load_return_invoice", (data) => {
			// Handle loading of return invoice and set all related fields
			console.log("Invoice component received load_return_invoice event with data:", data);
			this.load_invoice(data.invoice_doc);
			// Explicitly mark as return invoice
			this.invoiceType = "Return";
			this.invoiceTypes = ["Return"];
			this.invoice_doc.is_return = 1;
			// Ensure negative values for returns
			if (this.items && this.items.length) {
				this.items.forEach((item) => {
					// Ensure item quantities are negative
					if (item.qty > 0) item.qty = -Math.abs(item.qty);
					if (item.stock_qty > 0) item.stock_qty = -Math.abs(item.stock_qty);
				});
			}
			if (data.return_doc) {
				console.log("Return against existing invoice:", data.return_doc.name);
				this.discount_amount = data.return_doc.discount_amount || 0;
				this.additional_discount = data.return_doc.discount_amount || 0;
				this.return_doc = data.return_doc;
				// Set return_against reference
				this.invoice_doc.return_against = data.return_doc.name;
			} else {
				console.log("Return without invoice reference");
				// For return without invoice, reset discount values
				this.discount_amount = 0;
				this.additional_discount = 0;
				this.additional_discount_percentage = 0;
			}
			console.log("Invoice state after loading return:", {
				invoiceType: this.invoiceType,
				is_return: this.invoice_doc.is_return,
				items: this.items.length,
				customer: this.customer,
			});
		});
		this.eventBus.on("set_new_line", (data) => {
			this.new_line = data;
		});
		if (this.pos_profile.posa_allow_multi_currency) {
			this.fetch_available_currencies();
		}
		// Listen for reset_posting_date to reset posting date after invoice submission
		this.eventBus.on("reset_posting_date", () => {
			this.posting_date = frappe.datetime.nowdate();
		});
		this.eventBus.on("calc_uom", this.calc_uom);
		this.eventBus.on("item-drag-start", () => {
			this.showDropFeedback(true);
		});
		this.eventBus.on("item-drag-end", () => {
			this.showDropFeedback(false);
		});
	},
	// Cleanup event listeners before component is destroyed
	beforeUnmount() {
		// Existing cleanup
		this.eventBus.off("register_pos_profile");
		this.eventBus.off("add_item");
		this.eventBus.off("update_customer");
		this.eventBus.off("fetch_customer_details");
		this.eventBus.off("clear_invoice");
		// Cleanup reset_posting_date listener
		this.eventBus.off("reset_posting_date");
		// Cleanup change_invoice_type listener
		this.eventBus.off("change_invoice_type");
	},
	// Register global keyboard shortcuts when component is created
	created() {
		document.addEventListener("keydown", this.shortOpenPayment.bind(this));
		document.addEventListener("keydown", this.shortDeleteFirstItem.bind(this));
		document.addEventListener("keydown", this.shortOpenFirstItem.bind(this));
		document.addEventListener("keydown", this.shortSelectDiscount.bind(this));
	},
	// Remove global keyboard shortcuts when component is unmounted
	unmounted() {
		document.removeEventListener("keydown", this.shortOpenPayment);
		document.removeEventListener("keydown", this.shortDeleteFirstItem);
		document.removeEventListener("keydown", this.shortOpenFirstItem);
		document.removeEventListener("keydown", this.shortSelectDiscount);
	},
	watch: invoiceWatchers,
};
</script>

<style scoped>
/* Card background adjustments */
.cards {
	background-color: var(--surface-secondary) !important;
}

/* Style for selected checkbox button */
.v-checkbox-btn.v-selected {
	background-color: var(--submit-start) !important;
	color: white;
}

/* Bottom border for elements */
.border_line_bottom {
	border-bottom: 1px solid var(--field-border);
}

/* Disable pointer events for elements */
.disable-events {
	pointer-events: none;
}

/* Style for customer balance field */
:deep(.balance-field) {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	flex-wrap: nowrap;
}

/* Style for balance value text */
:deep(.balance-value) {
	font-size: 1.5rem;
	font-weight: bold;
	color: var(--primary-start);
	margin-left: var(--dynamic-xs);
}

/* Red border and label for return mode card */

/* Red border and label for return mode card */

.return-mode {
	border: 2px solid rgb(var(--v-theme-error)) !important;
	position: relative;
}

/* Label for return mode card */
.return-mode::before {
	content: "RETURN";
	position: absolute;
	top: 0;
	right: 0;
	background-color: rgb(var(--v-theme-error));
	color: white;
	padding: 4px 12px;
	font-weight: bold;
	border-bottom-left-radius: 8px;
	z-index: 1;
}

/* Blue border and label for edit mode card */

.edit-mode {
	border: 2px solid rgb(var(--v-theme-info)) !important;
	position: relative;
}

/* Label for edit mode card */
.edit-mode::before {
	content: "EDIT ORDER";
	position: absolute;
	top: 0;
	right: 0;
	background-color: rgb(var(--v-theme-info));
	color: white;
	padding: 4px 12px;
	font-weight: bold;
	border-bottom-left-radius: 8px;
	z-index: 1;
}

/* Dynamic padding for responsive layout */
.dynamic-padding {
	/* Uniform spacing for better alignment */
	padding: var(--dynamic-sm);
}

/* Responsive breakpoints */
@media (max-width: 768px) {
	.dynamic-padding {
		/* Smaller uniform padding on tablets */
		padding: var(--dynamic-xs);
	}

	.dynamic-padding .v-row {
		margin: 0 -2px;
	}

	.dynamic-padding .v-col {
		padding: 2px 4px;
	}
}

@media (max-width: 480px) {
	.dynamic-padding {
		padding: var(--dynamic-xs);
	}

	.dynamic-padding .v-row {
		margin: 0 -1px;
	}

	.dynamic-padding .v-col {
		padding: 1px 2px;
	}
}

.column-selector-container {
	display: flex;
	justify-content: flex-end;
	padding: 8px 16px;
	background-color: var(--surface-secondary);
	border-radius: 8px 8px 0 0;
	position: absolute;
	top: 0;
	right: 0;
	transform: translateY(-100%);
}

:deep([data-theme="dark"]) .column-selector-container,
:deep(.v-theme--dark) .column-selector-container {
	background-color: #1e1e1e;
}

.column-selector-btn {
	font-size: 0.875rem;
}

.items-table-wrapper {
	position: relative;
	margin-top: var(--dynamic-xl);
}

/* New styles for improved column switches */
:deep(.column-switch) {
	margin: 0;
	padding: 0;
}

:deep(.column-switch .v-switch__track) {
	opacity: 0.7;
}

:deep(.column-switch .v-switch__thumb) {
	transform: scale(0.8);
}

:deep(.column-switch .v-label) {
	opacity: 0.9;
	font-size: 0.95rem;
}
</style>
