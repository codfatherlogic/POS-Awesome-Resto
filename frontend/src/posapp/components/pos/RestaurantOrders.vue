<template>
	<v-row justify="center">
		<v-dialog v-model="ordersDialog" max-width="1200px">
			<v-card>
				<v-card-title class="d-flex align-center">
					<span class="text-h5 text-primary">{{ __("Restaurant Orders") }}</span>
					<v-spacer></v-spacer>
					<v-btn
						icon="mdi-close"
						variant="text"
						density="compact"
						@click="close_dialog"
					></v-btn>
				</v-card-title>
				
				<v-card-text class="pa-0">
					<v-container>
						<!-- Filters Row -->
						<v-row class="mb-4">
							<v-col cols="12" md="3">
								<v-select
									color="primary"
									:label="frappe._('Order Type')"
									:bg-color="isDarkTheme ? '#1E1E1E' : 'white'"
									hide-details
									v-model="filter_order_type"
									:items="order_type_options"
									density="compact"
									clearable
									class="mx-2"
									@update:model-value="filter_orders"
								></v-select>
							</v-col>
							<v-col cols="12" md="3">
								<v-select
									color="primary"
									:label="frappe._('Status')"
									:bg-color="isDarkTheme ? '#1E1E1E' : 'white'"
									hide-details
									v-model="filter_status"
									:items="status_options"
									density="compact"
									clearable
									class="mx-2"
									@update:model-value="filter_orders"
								></v-select>
							</v-col>
							<v-col cols="12" md="2">
								<v-text-field
									color="primary"
									:label="frappe._('Date')"
									:bg-color="isDarkTheme ? '#1E1E1E' : 'white'"
									hide-details
									v-model="filter_date"
									type="date"
									density="compact"
									class="mx-2"
									@update:model-value="filter_orders"
								></v-text-field>
							</v-col>
							<v-col cols="12" md="3">
								<v-text-field
									color="primary"
									:label="frappe._('Search Order/Customer')"
									:bg-color="isDarkTheme ? '#1E1E1E' : 'white'"
									hide-details
									v-model="search_text"
									density="compact"
									clearable
									class="mx-2"
									prepend-inner-icon="mdi-magnify"
									@input="filter_orders"
								></v-text-field>
							</v-col>
							<v-col cols="12" md="2">
								<v-btn
									variant="text"
									color="primary"
									theme="dark"
									@click="refresh_orders"
									class="mx-2"
									:loading="loading"
								>
									<v-icon>mdi-refresh</v-icon>
									{{ __("Refresh") }}
								</v-btn>
							</v-col>
						</v-row>
						
						<!-- Orders Table -->
						<v-row no-gutters>
							<v-col cols="12" class="pa-1">
								<v-data-table
									:headers="headers"
									:items="filtered_orders"
									item-key="name"
									class="elevation-1"
									show-select
									v-model="selected"
									return-object
									:select-strategy="multiSelectMode ? 'page' : 'single'"
									:loading="loading"
									density="compact"
									show-expand
									:expanded="expanded"
									@update:expanded="expanded = $event"
								>
									<template v-slot:item.transaction_date="{ item }">
										{{ formatDate(item.transaction_date) }}
									</template>
									
									<template v-slot:item.grand_total="{ item }">
										{{ currencySymbol(item.currency) }}
										{{ formatCurrency(item.grand_total) }}
									</template>
									
									<template v-slot:item.order_status="{ item }">
										<v-chip
											:color="getStatusColor(item)"
											size="small"
											variant="flat"
										>
											<v-icon start size="small">{{ getStatusIcon(item) }}</v-icon>
											{{ getOrderStatus(item) }}
										</v-chip>
									</template>
									
									<template v-slot:item.table_number="{ item }">
										<v-chip
											v-if="item.table_number"
											color="info"
											size="small"
											variant="outlined"
										>
											<v-icon start size="small">mdi-table-furniture</v-icon>
											{{ item.table_number }}
										</v-chip>
										<span v-else class="text-grey">-</span>
									</template>
									
									<template v-slot:item.order_type_name="{ item }">
										<v-chip
											:color="getOrderTypeColor(item.order_type_name)"
											size="small"
											variant="tonal"
										>
											{{ item.order_type_name || 'N/A' }}
										</v-chip>
									</template>
									
									<template v-slot:item.actions="{ item }">
										<!-- Reprint KOT Button - Available for all orders -->
										<v-btn
											size="small"
											color="orange-darken-1"
											variant="tonal"
											@click="reprint_kot(item)"
											class="mr-1"
											:loading="kotReprintLoading[item.name]"
										>
											<v-icon size="small">mdi-silverware-fork-knife</v-icon>
											{{ __("Reprint KOT") }}
										</v-btn>
										
										<v-btn
											v-if="canEdit(item)"
											size="small"
											color="primary"
											variant="tonal"
											@click="edit_order(item)"
											class="mr-1"
										>
											<v-icon size="small">mdi-pencil</v-icon>
											{{ __("Edit") }}
										</v-btn>
										
										<!-- Void Items Button - Available for draft orders -->
										<v-btn
											v-if="canEdit(item)"
											size="small"
											color="warning"
											variant="tonal"
											@click="void_items(item)"
											class="mr-1"
										>
											<v-icon size="small">mdi-close-circle</v-icon>
											{{ __("Void Items") }}
										</v-btn>
										
										<v-btn
											v-if="canDelete(item)"
											size="small"
											color="error"
											variant="tonal"
											@click="delete_order(item)"
											class="mr-1"
										>
											<v-icon size="small">mdi-delete</v-icon>
											{{ __("Delete") }}
										</v-btn>
										
										<v-btn
											v-else-if="canCancel(item)"
											size="small"
											color="error"
											variant="tonal"
											@click="cancel_order(item)"
										>
											<v-icon size="small">mdi-cancel</v-icon>
											{{ __("Cancel") }}
										</v-btn>
									</template>

									<!-- Expandable row content -->
									<template v-slot:expanded-row="{ item }">
										<td :colspan="headers.length + 2">
												<v-card flat class="ma-2">
													<v-card-title class="text-h6 text-primary">
														<v-icon class="mr-2">mdi-receipt</v-icon>
														{{ __("Order Details: {0}", [item.name]) }}
													</v-card-title>
													<v-card-text>
														<v-row>
															<v-col cols="12" md="6">
																<div class="text-subtitle-2 mb-2">{{ __("Order Information") }}</div>
																<v-list density="compact">
																	<v-list-item>
																		<template v-slot:prepend>
																			<v-icon>mdi-calendar</v-icon>
																		</template>
																		<v-list-item-title>{{ __("Date") }}: {{ formatDate(item.transaction_date) }}</v-list-item-title>
																	</v-list-item>
																	<v-list-item>
																		<template v-slot:prepend>
																			<v-icon>mdi-account</v-icon>
																		</template>
																		<v-list-item-title>{{ __("Customer") }}: {{ item.customer }}</v-list-item-title>
																	</v-list-item>
																	<v-list-item v-if="item.table_number">
																		<template v-slot:prepend>
																			<v-icon>mdi-table-furniture</v-icon>
																		</template>
																		<v-list-item-title>{{ __("Table") }}: {{ item.table_number }}</v-list-item-title>
																	</v-list-item>
																	<v-list-item>
																		<template v-slot:prepend>
																			<v-icon>mdi-food</v-icon>
																		</template>
																		<v-list-item-title>{{ __("Order Type") }}: {{ item.order_type_name || 'N/A' }}</v-list-item-title>
																	</v-list-item>
																</v-list>
															</v-col>
															<v-col cols="12" md="6">
																<div class="text-subtitle-2 mb-2">{{ __("Items") }}</div>
																<v-table density="compact" v-if="item.items && item.items.length">
																	<thead>
																		<tr>
																			<th class="text-left">{{ __("Item") }}</th>
																			<th class="text-center">{{ __("Qty") }}</th>
																			<th class="text-right">{{ __("Rate") }}</th>
																			<th class="text-right">{{ __("Amount") }}</th>
																		</tr>
																	</thead>
																	<tbody>
																		<tr v-for="orderItem in item.items" :key="orderItem.name">
																			<td class="text-left">{{ orderItem.item_name || orderItem.item_code }}</td>
																			<td class="text-center">{{ orderItem.qty }} {{ orderItem.uom || '' }}</td>
																			<td class="text-right">{{ currencySymbol(item.currency) }}{{ formatCurrency(orderItem.rate) }}</td>
																			<td class="text-right">{{ currencySymbol(item.currency) }}{{ formatCurrency(orderItem.amount) }}</td>
																		</tr>
																	</tbody>
																</v-table>
																<div v-else class="text-grey text-center py-4">
																	{{ __("No items available") }}
																</div>
															</v-col>
														</v-row>
														<v-divider class="my-3"></v-divider>
														<v-row>
															<v-col cols="12" md="8">
																<!-- Empty space for layout balance -->
															</v-col>
															<v-col cols="12" md="4">
																<v-table density="compact">
																	<tbody>
																		<tr>
																			<td class="text-right font-weight-medium">{{ __("Subtotal") }}:</td>
																			<td class="text-right">{{ currencySymbol(item.currency) }}{{ formatCurrency(item.net_total || 0) }}</td>
																		</tr>
																		<tr v-if="item.total_taxes_and_charges">
																			<td class="text-right font-weight-medium">{{ __("Tax") }}:</td>
																			<td class="text-right">{{ currencySymbol(item.currency) }}{{ formatCurrency(item.total_taxes_and_charges) }}</td>
																		</tr>
																		<tr v-if="item.discount_amount">
																			<td class="text-right font-weight-medium">{{ __("Discount") }}:</td>
																			<td class="text-right text-error">-{{ currencySymbol(item.currency) }}{{ formatCurrency(item.discount_amount) }}</td>
																		</tr>
																		<tr class="font-weight-bold">
																			<td class="text-right">{{ __("Total") }}:</td>
																			<td class="text-right text-primary">{{ currencySymbol(item.currency) }}{{ formatCurrency(item.grand_total) }}</td>
																		</tr>
																	</tbody>
																</v-table>
															</v-col>
														</v-row>
													</v-card-text>
												</v-card>
											</td>
									</template>
								</v-data-table>
							</v-col>
						</v-row>
					</v-container>
				</v-card-text>
				
				<v-card-actions>
					<v-btn
						color="secondary"
						variant="outlined"
						@click="toggleMultiSelect"
						class="mr-2"
					>
						<v-icon start>{{ multiSelectMode ? 'mdi-checkbox-multiple-marked' : 'mdi-checkbox-multiple-blank' }}</v-icon>
						{{ multiSelectMode ? __("Single Select") : __("Multi Select") }}
					</v-btn>
					<v-spacer></v-spacer>
					<v-btn color="error" theme="dark" @click="close_dialog">
						{{ __("Close") }}
					</v-btn>
					<v-btn
						v-if="selected.length === 1 && canConvertToPayment(selected[0])"
						color="success"
						theme="dark"
						@click="convert_to_payment"
						:loading="converting"
					>
						{{ __("Convert to Payment") }}
					</v-btn>
					<v-btn
						v-if="selected.length > 1 && canConvertMultipleToInvoice()"
						color="primary"
						theme="dark"
						@click="convert_multiple_to_payment"
						:loading="converting"
					>
						{{ __("Add {0} Draft Orders to Cart", [selected.length]) }}
					</v-btn>
					<v-btn
						v-if="selected.length === 1 && canEdit(selected[0])"
						color="warning"
						theme="dark"
						@click="edit_order(selected[0])"
						:loading="converting"
						class="mr-2"
					>
						{{ __("Edit Order") }}
					</v-btn>
				</v-card-actions>
			</v-card>
		</v-dialog>

		<!-- Void Items Dialog -->
		<v-dialog v-model="voidItemsDialog" max-width="800px">
			<v-card>
				<v-card-title class="d-flex align-center">
					<span class="text-h6 text-warning">{{ __("Void Items") }}</span>
					<v-spacer></v-spacer>
					<v-btn
						icon="mdi-close"
						variant="text"
						density="compact"
						@click="voidItemsDialog = false"
					></v-btn>
				</v-card-title>
				
				<v-card-text v-if="selectedOrderForVoid">
					<v-container>
						<v-row class="mb-4">
							<v-col cols="12">
								<v-alert type="warning" border="start" variant="tonal">
									{{ __("Select items to void from order: ") + selectedOrderForVoid.name }}
								</v-alert>
							</v-col>
						</v-row>
						
						<v-row>
							<v-col cols="12">
								<v-data-table
									:headers="voidItemHeaders"
									:items="selectedOrderForVoid.items || []"
									item-value="idx"
									show-select
									v-model="selectedItemsToVoid"
									density="compact"
									:loading="voidLoading"
									return-object
								>
									<template v-slot:item.rate="{ item }">
										{{ formatCurrency(item.rate) }}
									</template>
									<template v-slot:item.amount="{ item }">
										{{ formatCurrency(item.amount) }}
									</template>
								</v-data-table>
							</v-col>
						</v-row>
					</v-container>
				</v-card-text>
				
				<v-card-actions>
					<v-spacer></v-spacer>
					<v-btn
						color="grey"
						variant="text"
						@click="voidItemsDialog = false"
					>
						{{ __("Cancel") }}
					</v-btn>
					<v-btn
						color="warning"
						variant="flat"
						@click="confirmVoidItems(selectedOrderForVoid, selectedItemsToVoid)"
						:loading="voidLoading"
						:disabled="!selectedItemsToVoid || selectedItemsToVoid.length === 0"
					>
						{{ __("Void Selected Items") }}
					</v-btn>
				</v-card-actions>
			</v-card>
		</v-dialog>
	</v-row>
</template>

<script>
import format from "../../format";

export default {
	mixins: [format],
	data() {
		return {
			ordersDialog: false,
			pos_profile: {},
			pos_opening_shift: null,
			selected: [],
			orders_data: [],
			filtered_orders: [],
			loading: false,
			converting: false,
			multiSelectMode: false,
			expanded: [], // Track expanded rows
			filter_order_type: null,
			filter_status: null,
			filter_date: null,
			search_text: "",
			kotReprintLoading: {}, // Track loading state for each order's KOT reprint
			voidItemsDialog: false,
			selectedOrderForVoid: null,
			voidLoading: false,
			selectedItemsToVoid: [],
			voidItemHeaders: [
				{
					title: __("Item"),
					key: "item_name",
					align: "start",
					sortable: false,
				},
				{
					title: __("Qty"),
					key: "qty",
					align: "center",
					sortable: false,
				},
				{
					title: __("Rate"),
					key: "rate",
					align: "end",
					sortable: false,
				},
				{
					title: __("Amount"),
					key: "amount",
					align: "end",
					sortable: false,
				},
			],
			headers: [
				{
					title: __("Order"),
					key: "name",
					align: "start",
					sortable: true,
				},
				{
					title: __("Customer"),
					key: "customer_name",
					align: "start",
					sortable: true,
				},
				{
					title: __("Date"),
					align: "start",
					sortable: true,
					key: "transaction_date",
				},
				{
					title: __("Order Type"),
					key: "order_type_name",
					align: "start",
					sortable: true,
				},
				{
					title: __("Table"),
					key: "table_number",
					align: "center",
					sortable: true,
				},
				{
					title: __("Status"),
					key: "order_status",
					align: "center",
					sortable: true,
				},
				{
					title: __("Amount"),
					key: "grand_total",
					align: "end",
					sortable: false,
				},
				{
					title: __("Actions"),
					key: "actions",
					align: "center",
					sortable: false,
				},
			],
			order_type_options: [],
			status_options: [
				{ title: __("Draft"), value: "Draft" },
				{ title: __("Submitted"), value: "Submitted" },
				{ title: __("Billed"), value: "Billed" },
				{ title: __("Cancelled"), value: "Cancelled" },
			],
		};
	},
	computed: {
		isDarkTheme() {
			return this.$theme?.current === "dark";
		},
	},
	watch: {
		filter_status() {
			if (this.ordersDialog) {
				this.fetch_orders();
			}
		},
		filter_date() {
			if (this.ordersDialog) {
				this.fetch_orders();
			}
		},
		selectedItemsToVoid: {
			handler(newVal, oldVal) {
				console.log("selectedItemsToVoid changed:", {
					new: newVal,
					old: oldVal,
					count: newVal?.length || 0
				});
			},
			deep: true
		},
	},
	methods: {
		async open_orders_dialog() {
			this.ordersDialog = true;
			this.clearSelected();
			
			// Set today's date as default if not already set
			if (!this.filter_date) {
				const today = new Date();
				this.filter_date = today.toISOString().split('T')[0]; // Format as YYYY-MM-DD
			}
			
			await this.fetch_orders();
		},

		close_dialog() {
			this.ordersDialog = false;
			this.clearSelected();
		},

		clearSelected() {
			this.selected = [];
		},

		async fetch_orders() {
			this.loading = true;
			try {
				console.log("Fetching orders with filters:", {
					pos_opening_shift: this.pos_opening_shift?.name || null,
					status: this.filter_status || null,
					date_filter: this.filter_date || null,
				});
				
				const r = await frappe.call({
					method: "posawesome.posawesome.api.restaurant_orders.get_restaurant_orders",
					args: {
						pos_opening_shift: this.pos_opening_shift?.name || null,
						status: this.filter_status || null,
						date_filter: this.filter_date || null,
					},
				});
				
				console.log("=== FETCH ORDERS DEBUG ===");
				console.log("Raw API response:", r);
				console.log("Response message:", r.message);
				if (r.message && r.message.length > 0) {
					console.log("First few orders from API:");
					r.message.slice(0, 5).forEach((order, index) => {
						console.log(`  Order ${index + 1}:`, {
							name: order.name,
							doctype: order.doctype || 'not specified',
							customer: order.customer,
							docstatus: order.docstatus
						});
					});
					
					// Check if any orders have invalid names
					const invalidOrders = r.message.filter(o => !o.name || !o.name.startsWith('SAL-ORD-'));
					if (invalidOrders.length > 0) {
						console.error("CRITICAL: API returned orders with invalid names:");
						invalidOrders.forEach(order => {
							console.error("  INVALID ORDER:", order);
						});
					}
				}
				console.log("=== END FETCH ORDERS DEBUG ===");
				
				console.log("API response:", r);
				
				if (r.message) {
					// Filter out any entries that don't have proper Sales Order names
					// This prevents corrupted data from showing in the list
					const validOrders = r.message.filter(order => {
						const isValid = order.name && order.name.startsWith('SAL-ORD-');
						if (!isValid) {
							console.warn("Filtering out invalid order entry:", order.name);
						}
						return isValid;
					});
					
					this.orders_data = validOrders;
					console.log("Orders data (filtered):", this.orders_data);
					this.filter_orders();
					
					// Extract unique order types for filter
					const orderTypes = [...new Set(validOrders.map(o => o.order_type_name).filter(Boolean))];
					this.order_type_options = orderTypes.map(type => ({ title: type, value: type }));
				}
			} catch (error) {
				console.error("Failed to fetch restaurant orders", error);
				this.eventBus.emit("show_message", {
					title: __("Error fetching orders"),
					color: "error",
				});
			} finally {
				this.loading = false;
			}
		},

		async refresh_orders() {
			await this.fetch_orders();
			this.eventBus.emit("show_message", {
				title: __("Orders refreshed"),
				color: "success",
			});
		},

		filter_orders() {
			let filtered = [...this.orders_data];
			
			// Filter by order type
			if (this.filter_order_type) {
				filtered = filtered.filter(order => order.order_type_name === this.filter_order_type);
			}
			
			// Filter by status
			if (this.filter_status) {
				filtered = filtered.filter(order => this.getOrderStatus(order) === this.filter_status);
			}
			
			// Filter by date
			if (this.filter_date) {
				filtered = filtered.filter(order => {
					const orderDate = new Date(order.transaction_date).toISOString().split('T')[0];
					return orderDate === this.filter_date;
				});
			}
			
			// Filter by search text
			if (this.search_text) {
				const searchLower = this.search_text.toLowerCase();
				filtered = filtered.filter(order => 
					order.name.toLowerCase().includes(searchLower) ||
					order.customer_name.toLowerCase().includes(searchLower)
				);
			}
			
			this.filtered_orders = filtered;
		},

		getOrderStatus(order) {
			if (order.docstatus === 0) return "Draft";
			if (order.docstatus === 1 && order.per_billed < 100) return "Submitted";
			if (order.per_billed >= 100) return "Billed";
			return "Unknown";
		},

		getStatusColor(order) {
			const status = this.getOrderStatus(order);
			const statusColors = {
				'Draft': 'orange',
				'Submitted': 'blue',
				'Billed': 'success',
			};
			return statusColors[status] || 'grey';
		},

		getStatusIcon(order) {
			const status = this.getOrderStatus(order);
			const statusIcons = {
				'Draft': 'mdi-file-document-outline',
				'Submitted': 'mdi-check-circle-outline',
				'Billed': 'mdi-receipt',
			};
			return statusIcons[status] || 'mdi-information-outline';
		},

		getOrderTypeColor(orderType) {
			const colors = {
				'Dine In': 'purple',
				'Take Away': 'orange',
				'Delivery': 'green',
			};
			return colors[orderType] || 'grey';
		},

		canConvertToPayment(order) {
			// Allow conversion to payment for both Draft (0) and Submitted (1) orders that are not fully billed
			const canConvert = (order.docstatus === 0 || order.docstatus === 1) && order.per_billed < 100;
			console.log("Can convert to payment:", {
				order: order.name,
				docstatus: order.docstatus,
				per_billed: order.per_billed,
				canConvert
			});
			return canConvert;
		},

		canEdit(order) {
			return order.docstatus === 0; // Only allow editing draft orders to avoid the Sales Invoice error
		},

		canCancel(order) {
			return order.docstatus === 1; // Only submitted orders can be cancelled
		},

		canDelete(order) {
			return order.docstatus === 0; // Only draft orders can be deleted
		},

		canConvertMultipleToInvoice() {
			if (!this.selected || this.selected.length === 0) {
				console.log("No orders selected for multiple conversion");
				return false;
			}
			
			if (this.selected.length < 2) {
				console.log("Need at least 2 orders for multiple conversion");
				return false;
			}
			
			console.log("Checking multiple selection:", {
				selected_count: this.selected.length,
				multiSelectMode: this.multiSelectMode,
				selected_orders: this.selected.map(o => ({
					name: o.name,
					customer: o.customer,
					customer_name: o.customer_name,
					docstatus: o.docstatus,
					per_billed: o.per_billed,
					status: this.getOrderStatus(o)
				}))
			});
			
			// Check if all selected orders are from the same customer
			const firstCustomer = this.selected[0].customer;
			const sameCustomer = this.selected.every(order => order.customer === firstCustomer);
			
			console.log("Same customer check:", {
				firstCustomer,
				sameCustomer,
				customers: this.selected.map(o => o.customer)
			});
			
			if (!sameCustomer) {
				console.log("Orders are not from the same customer");
				return false;
			}
			
			// Check if all orders are eligible - ONLY DRAFT ORDERS for multi-editing
			const allEligible = this.selected.every(order => {
				const eligible = order.docstatus === 0; // Only draft orders
				console.log(`Order ${order.name} eligible for multi-edit:`, {
					docstatus: order.docstatus,
					status: this.getOrderStatus(order),
					eligible
				});
				return eligible;
			});
			
			console.log("All draft orders check:", allEligible);
			
			if (!allEligible) {
				console.log("Some orders are not draft - multi-edit only supports draft orders");
			}
			
			return allEligible;
		},

		toggleMultiSelect() {
			this.multiSelectMode = !this.multiSelectMode;
			this.clearSelected();
		},


		async convert_to_payment() {
			if (!this.selected.length) return;
			
			const order = this.selected[0];
			
			// DEBUG: Log the complete order object to see what we're dealing with
			console.log("=== CONVERT TO PAYMENT DEBUG ===");
			console.log("Selected order object:", JSON.stringify(order, null, 2));
			console.log("Order name:", order.name);
			console.log("Order doctype (if available):", order.doctype);
			console.log("All orders data:", JSON.stringify(this.orders_data.map(o => ({name: o.name, docstatus: o.docstatus})), null, 2));
			console.log("=== END DEBUG ===");
			
			// CRITICAL FIX: If the selected order has an invalid name but we can find the correct order in orders_data, use that
			let validOrderName = order.name;
			if (!order.name || !order.name.startsWith('SAL-ORD-')) {
				console.error("CRITICAL: Selected order has invalid name, attempting to find correct order...");
				
				// Try to find the order in orders_data by matching other properties
				const correctOrder = this.orders_data.find(o => 
					o.customer === order.customer && 
					Math.abs(o.grand_total - order.grand_total) < 0.01 &&
					o.name && o.name.startsWith('SAL-ORD-')
				);
				
				if (correctOrder) {
					console.log("RECOVERY: Found correct order:", correctOrder.name);
					validOrderName = correctOrder.name;
					// Update the selected order with correct data
					Object.assign(order, correctOrder);
				} else {
					console.error("RECOVERY FAILED: Could not find correct order");
					this.eventBus.emit("show_message", {
						title: __("Invalid order format: {0}. Please refresh the orders list and try again.", [order.name || 'undefined']),
						color: "error",
					});
					return;
				}
			}
			
			this.converting = true;
			
			try {
				// Use the validated order name
				console.log("Using validated order name:", validOrderName);
				
				// NEW WORKFLOW: Handle Draft and Submitted orders differently
				if (order.docstatus === 0) {
					// Draft Order - Load directly into cart for editing/payment WITHOUT submitting
					console.log("Loading draft order into cart for editing:", validOrderName);
					
					// First, fetch the complete order data with items
					const orderResult = await frappe.call({
						method: "frappe.client.get",
						args: {
							doctype: "Sales Order",
							name: validOrderName,
						},
					});

					if (orderResult.message) {
						const orderData = orderResult.message;
						console.log("Fetched complete order data:", orderData);
						
						// Switch to Order mode for editing
						this.eventBus.emit("change_invoice_type", "Order");
						
						// Load the complete draft order data into cart for editing
						this.eventBus.emit("load_invoice", orderData);
						
						// Close dialog
						this.close_dialog();
						
						// Show success message
						this.eventBus.emit("show_message", {
							title: __("Draft Order {0} loaded for editing. Make changes and click SUBMIT when ready.", [validOrderName]),
							color: "success",
						});
					} else {
						throw new Error("Failed to fetch order data");
					}
				} else {
					// Submitted Order - Convert to Sales Invoice for payment
					console.log("Converting submitted order to invoice for payment:", validOrderName);
					
					const invoiceResult = await frappe.call({
						method: "posawesome.posawesome.api.restaurant_orders.convert_order_to_invoice",
						args: {
							sales_order_name: validOrderName,
							pos_profile_name: this.pos_profile?.name || null,
						},
					});
					
					if (invoiceResult.message) {
						// Switch to Invoice mode for payment processing
						this.eventBus.emit("change_invoice_type", "Invoice");
						
						// Load the invoice into cart for payment
						this.eventBus.emit("load_invoice", invoiceResult.message);
						
						// Close dialog
						this.close_dialog();
						
						// Show success message
						this.eventBus.emit("show_message", {
							title: __("Order {0} converted to invoice for payment. Review items and click PAY when ready.", [validOrderName]),
							color: "success",
						});
					}
				}
			} catch (error) {
				console.error("Failed to convert order to payment", error);
				this.eventBus.emit("show_message", {
					title: __("Error converting order to payment: {0}", [error.message || "Unknown error"]),
					color: "error",
				});
			} finally {
				this.converting = false;
			}
		},

		async edit_order(order) {
			try {
				console.log("Loading order for editing:", order.name);
				
				// Validate that this is actually a Sales Order
				if (!order.name.startsWith('SAL-ORD-')) {
					this.eventBus.emit("show_message", {
						title: __("Invalid order format. Expected Sales Order name."),
						color: "error",
					});
					return;
				}
				
				// Load the Sales Order for editing
				const r = await frappe.call({
					method: "frappe.client.get",
					args: {
						doctype: "Sales Order",
						name: order.name,
					},
				});
				
				if (r.message) {
					// Additional validation - ensure the loaded document is consistent
					if (r.message.doctype !== "Sales Order") {
						console.error("Loaded document has wrong doctype:", r.message.doctype);
						this.eventBus.emit("show_message", {
							title: __("Error: Loaded document is not a Sales Order. Expected Sales Order, got {0}", [r.message.doctype]),
							color: "error",
						});
						return;
					}
					
					console.log("Successfully loaded Sales Order:", r.message.name, "doctype:", r.message.doctype);
					
					// Ensure invoice type is set to "Order" before loading
					this.eventBus.emit("change_invoice_type", "Order");
					
					// Emit event to load the order in the main invoice
					this.eventBus.emit("load_order", r.message);
					this.close_dialog();
					
					const statusText = order.docstatus === 1 ? "editing (submitted)" : "editing";
					this.eventBus.emit("show_message", {
						title: __("Order {0} loaded for {1}", [order.name, statusText]),
						color: "success",
					});
				}
			} catch (error) {
				console.error("Failed to load Sales Order for editing", error);
				
				// Provide specific error messages based on error type
				if (error.message && error.message.includes("not found")) {
					this.eventBus.emit("show_message", {
						title: __("Sales Order {0} not found. It may have been deleted or moved.", [order.name]),
						color: "error",
					});
				} else if (error.message && error.message.includes("Sales Invoice")) {
					this.eventBus.emit("show_message", {
						title: __("Error: Trying to load Sales Invoice instead of Sales Order. Order {0} should be a Sales Order.", [order.name]),
						color: "error",
					});
				} else {
					this.eventBus.emit("show_message", {
						title: __("Error loading Sales Order: {0}", [error.message || "Unknown error"]),
						color: "error",
					});
				}
			}
		},

		async convert_multiple_to_payment() {
			if (!this.selected.length) return;
			
			console.log(`Loading ${this.selected.length} draft orders for editing...`);
			
			// Validate all selected orders are draft
			const draftOrderNames = [];
			for (const order of this.selected) {
				if (order.docstatus !== 0) {
					this.eventBus.emit("show_message", {
						title: __("Order {0} is not in draft status. Only draft orders can be loaded for editing.", [order.name]),
						color: "error",
					});
					return;
				}
				draftOrderNames.push(order.name);
			}
			
			// Validate that all orders are from the same customer
			const firstCustomer = this.selected[0].customer;
			const sameCustomer = this.selected.every(order => order.customer === firstCustomer);
			
			if (!sameCustomer) {
				this.eventBus.emit("show_message", {
					title: __("All selected orders must be from the same customer"),
					color: "error",
				});
				return;
			}
			
			this.converting = true;
			
			try {
				console.log("Calling backend API with order names:", draftOrderNames);
				console.log("Selected orders data for debugging:", JSON.stringify(this.selected.map(o => ({
					name: o.name,
					customer: o.customer,
					customer_name: o.customer_name,
					docstatus: o.docstatus
				})), null, 2));
				
				// Load draft orders for editing (without submitting them)
				const r = await frappe.call({
					method: "posawesome.posawesome.api.restaurant_orders.load_multiple_draft_orders_for_editing",
					args: {
						sales_order_names: draftOrderNames,
						pos_profile_name: this.pos_profile?.name || null,
					},
				});
				
				console.log("Backend API response:", r);
				console.log("Response message properties:", r.message ? Object.keys(r.message) : 'No message');
				
				if (r && r.message) {
					console.log("Successfully received consolidated order data from backend");
					
					// Switch to Order mode for editing (keep as draft)
					this.eventBus.emit("change_invoice_type", "Order");
					
					// Load the consolidated draft order into cart for editing
					this.eventBus.emit("load_invoice", r.message);
					
					// Close dialog
					this.close_dialog();
					
					// Show success message with editing instructions
					// Use customer_name from the response data, fallback to customer field, or use generic message
					const customerName = r.message.customer_name || r.message.customer || this.selected[0].customer_name || this.selected[0].customer || "customer";
					this.eventBus.emit("show_message", {
						title: __("✅ {0} draft orders consolidated for payment. IMPORTANT: Original orders remain as drafts. When you complete payment, a new invoice will be created while keeping original orders unchanged.", [draftOrderNames.length]),
						color: "success",
						timeout: 8000,  // Show longer message for important info
					});
					
					console.log(`Successfully loaded ${draftOrderNames.length} draft orders for editing`);
				} else {
					console.error("Backend API returned empty response");
					throw new Error("No data returned from backend");
				}
			} catch (error) {
				console.error("Failed to load draft orders for editing", error);
				this.eventBus.emit("show_message", {
					title: __("Error loading draft orders: {0}", [error.message || "Unknown error"]),
					color: "error",
				});
			} finally {
				this.converting = false;
			}
		},

		async cancel_order(order) {
			// Show confirmation dialog
			const confirmed = await new Promise((resolve) => {
				frappe.confirm(
					__("Are you sure you want to cancel order {0}?", [order.name]),
					() => resolve(true),
					() => resolve(false)
				);
			});
			
			if (!confirmed) return;
			
			try {
				const r = await frappe.call({
					method: "posawesome.posawesome.api.restaurant_orders.cancel_restaurant_order",
					args: {
						sales_order_name: order.name,
					},
				});
				
				if (r.message && r.message.success) {
					this.eventBus.emit("show_message", {
						title: r.message.message,
						color: "success",
					});
					
					// Refresh orders list
					await this.fetch_orders();
				}
			} catch (error) {
				console.error("Failed to cancel order", error);
				this.eventBus.emit("show_message", {
					title: __("Error cancelling order"),
					color: "error",
				});
			}
		},

		async delete_order(order) {
			// Show confirmation dialog
			const confirmed = await new Promise((resolve) => {
				frappe.confirm(
					__("Are you sure you want to delete order {0}?", [order.name]),
					() => resolve(true),
					() => resolve(false)
				);
			});
			
			if (!confirmed) return;
			
			try {
				const r = await frappe.call({
					method: "posawesome.posawesome.api.restaurant_orders.delete_restaurant_order",
					args: {
						sales_order_name: order.name,
					},
				});
				
				if (r.message && r.message.success) {
					this.eventBus.emit("show_message", {
						title: r.message.message,
						color: "success",
					});
					
					// Refresh orders list
					await this.fetch_orders();
				}
			} catch (error) {
				console.error("Failed to delete order", error);
				this.eventBus.emit("show_message", {
					title: __("Error deleting order"),
					color: "error",
				});
			}
		},

		formatDate(date) {
			if (!date) return "";
			return frappe.datetime.str_to_user(date);
		},

		async reprint_kot(order) {
			// Set loading state for this specific order
			this.$set(this.kotReprintLoading, order.name, true);
			
			try {
				console.log("Reprinting KOT for order:", order.name);
				
				// Call the KOT generation API to get HTML for reprint
				const response = await frappe.call({
					method: "posawesome.posawesome.api.restaurant_orders.reprint_kot",
					args: {
						order_name: order.name,
					},
				});

				if (response.message) {
					// Import the KOT print module dynamically
					const kotPrintModule = await import("../../plugins/kot_print.js");
					
					// Print the KOT HTML directly
					await kotPrintModule.printKOTHTML(response.message);
					
					this.eventBus.emit("show_message", {
						title: __("KOT reprinted successfully"),
						color: "success",
					});
				}
			} catch (error) {
				console.error("Error reprinting KOT:", error);
				this.eventBus.emit("show_message", {
					title: __("Error reprinting KOT: ") + (error.message || error),
					color: "error",
				});
			} finally {
				this.$set(this.kotReprintLoading, order.name, false);
			}
		},

		async void_items(order) {
			console.log("Opening void items dialog for order:", order);
			
			try {
				// Fetch the complete order data with items
				const orderResult = await frappe.call({
					method: "frappe.client.get",
					args: {
						doctype: "Sales Order",
						name: order.name,
					},
				});

				if (orderResult.message) {
					this.selectedOrderForVoid = orderResult.message;
					this.selectedItemsToVoid = []; // Clear previous selection
					this.voidLoading = false; // Reset loading state
					this.voidItemsDialog = true;
				} else {
					throw new Error("Failed to fetch order details");
				}
			} catch (error) {
				console.error("Error fetching order for voiding:", error);
				this.eventBus.emit("show_message", {
					title: __("Error fetching order details"),
					color: "error",
				});
			}
		},

		async confirmVoidItems(order, itemsToVoid) {
			this.voidLoading = true;
			
			try {
				console.log("Voiding items from order:", order.name, itemsToVoid);
				
				if (!itemsToVoid || itemsToVoid.length === 0) {
					this.eventBus.emit("show_message", {
						title: __("Please select items to void"),
						color: "warning",
					});
					return;
				}
				
				// Map selected items to their idx values for backend processing
				const itemsData = itemsToVoid.map(item => ({
					idx: item.idx,
					item_code: item.item_code,
					qty: item.qty
				}));
				
				// Call backend to void specific items
				const response = await frappe.call({
					method: "posawesome.posawesome.api.restaurant_orders.void_order_items",
					args: {
						order_name: order.name,
						items_to_void: itemsData,
					},
				});

				if (response.message) {
					this.eventBus.emit("show_message", {
						title: __("Items voided successfully"),
						color: "success",
					});
					
					// Clear expanded rows to force fresh data load when expanded again
					this.expanded = [];
					
					// Clear the cached order data to ensure fresh fetch
					this.selectedOrderForVoid = null;
					
					// Force a complete refresh of the orders list
					await this.fetch_orders();
					
					// Also update the order in our local data if it exists
					const orderIndex = this.orders_data.findIndex(o => o.name === order.name);
					if (orderIndex !== -1) {
						// Fetch the updated order data
						try {
							const updatedOrderResult = await frappe.call({
								method: "frappe.client.get",
								args: {
									doctype: "Sales Order",
									name: order.name,
								},
							});
							if (updatedOrderResult.message) {
								// Update the order in our local data array
								this.orders_data[orderIndex] = {
									...this.orders_data[orderIndex],
									items: updatedOrderResult.message.items,
									grand_total: updatedOrderResult.message.grand_total,
									net_total: updatedOrderResult.message.net_total,
								};
								// Refilter to update the display
								this.filter_orders();
							}
						} catch (fetchError) {
							console.log("Could not update local order data:", fetchError);
						}
					}
					
					// Force refresh the Sales Order document if it's open in Frappe
					try {
						if (window.frappe && window.frappe.get_route && window.frappe.get_route()[0] === 'Form' && window.frappe.get_route()[1] === 'Sales Order') {
							// If a Sales Order form is currently open, refresh it
							const current_route = window.frappe.get_route();
							if (current_route[2] === order.name) {
								// This is the same order that was voided, refresh the form
								window.frappe.set_route('Form', 'Sales Order', order.name);
							}
						}
					} catch (refresh_error) {
						console.log("Could not refresh Sales Order form:", refresh_error);
					}
					
					// Close the void dialog
					this.voidItemsDialog = false;
					this.selectedOrderForVoid = null;
					this.selectedItemsToVoid = [];
				}
			} catch (error) {
				console.error("Error voiding items:", error);
				this.eventBus.emit("show_message", {
					title: __("Error voiding items: ") + (error.message || error),
					color: "error",
				});
			} finally {
				this.voidLoading = false;
			}
		},
	},
	
	created() {
		this.eventBus.on("open_restaurant_orders", () => {
			this.open_orders_dialog();
		});
	},
	
	mounted() {
		this.eventBus.on("register_pos_profile", (data) => {
			this.pos_profile = data.pos_profile;
			this.pos_opening_shift = data.pos_opening_shift;
		});
	},
	
	beforeUnmount() {
		this.eventBus.off("open_restaurant_orders");
		this.eventBus.off("register_pos_profile");
	},
};
</script>

<style scoped>
:deep([data-theme="dark"]) .v-card,
:deep(.v-theme--dark) .v-card {
	background-color: #1e1e1e !important;
}

:deep([data-theme="dark"]) .v-data-table,
:deep(.v-theme--dark) .v-data-table {
	background-color: #1e1e1e !important;
}

.v-chip {
	font-weight: 500;
}
</style>