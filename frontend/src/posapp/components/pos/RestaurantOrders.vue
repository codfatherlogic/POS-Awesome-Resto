<template>
	<v-row justify="center">
		<v-dialog v-model="ordersDialog" max-width="1400px" max-height="90vh">
			<v-card style="height: 85vh;">
				<v-card-title class="d-flex align-center pa-4">
					<span class="text-h4 text-primary font-weight-bold">{{ __("Restaurant Orders") }}</span>
					<v-spacer></v-spacer>
					<v-btn
						icon="mdi-close"
						variant="text"
						density="compact"
						size="large"
						@click="close_dialog"
					></v-btn>
				</v-card-title>
				
				<v-card-text class="pa-0" style="height: calc(85vh - 80px); overflow-y: auto;">
					<v-container fluid class="pa-4">
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
										<div class="d-flex flex-wrap gap-1">
											<v-btn
												v-if="canEdit(item)"
												size="default"
												color="primary"
												variant="flat"
												@click="edit_order(item)"
												class="ma-1 text-caption"
												min-width="90"
											>
												<v-icon start size="small">mdi-pencil</v-icon>
												{{ __("Edit") }}
											</v-btn>
											
											<v-btn
												v-if="canAddItems(item)"
												size="default"
												color="success"
												variant="flat"
												@click="add_items_to_table(item)"
												class="ma-1 text-caption"
												min-width="110"
											>
												<v-icon start size="small">mdi-plus-circle</v-icon>
												{{ __("Add Items") }}
											</v-btn>
											
											<v-btn
												v-if="canReprintKot(item)"
												size="default"
												color="info"
												variant="flat"
												@click="reprint_kot(item)"
												class="ma-1 text-caption"
												min-width="100"
											>
												<v-icon start size="small">mdi-printer</v-icon>
												{{ __("Reprint KOT") }}
											</v-btn>
											
											<v-btn
												v-if="canVoidItems(item)"
												size="default"
												color="orange"
												variant="flat"
												@click="void_items(item)"
												class="ma-1 text-caption"
												min-width="100"
											>
												<v-icon start size="small">mdi-close-circle</v-icon>
												{{ __("Void Items") }}
											</v-btn>
											
											<v-btn
												v-if="canDelete(item)"
												size="default"
												color="error"
												variant="flat"
												@click="delete_order(item)"
												class="ma-1 text-caption"
												min-width="80"
											>
												<v-icon start size="small">mdi-delete</v-icon>
												{{ __("Delete") }}
											</v-btn>
											
											<v-btn
												v-else-if="canCancel(item)"
												size="default"
												color="error"
												variant="flat"
												@click="cancel_order(item)"
												class="ma-1 text-caption"
												min-width="80"
											>
												<v-icon start size="small">mdi-cancel</v-icon>
												{{ __("Cancel") }}
											</v-btn>
										</div>
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
		<v-dialog v-model="voidItemsDialog" max-width="600px">
			<v-card>
				<v-card-title class="d-flex align-center">
					<span class="text-h5 text-primary">{{ __("Void Items") }}</span>
					<v-spacer></v-spacer>
					<v-btn
						icon="mdi-close"
						variant="text"
						density="compact"
						@click="voidItemsDialog = false"
					></v-btn>
				</v-card-title>
				
				<v-card-text v-if="selectedOrderForVoid">
					<v-alert type="warning" variant="tonal" class="mb-4">
						<v-icon start>mdi-alert-triangle</v-icon>
						{{ __("Select items and specify quantities to void from order {0}. Voided items will generate a KOT for kitchen notification.", [selectedOrderForVoid.name]) }}
					</v-alert>
					
					<v-data-table
						:headers="[
							{ title: __('Select'), key: 'select', align: 'center', sortable: false, width: '80px' },
							{ title: __('Item'), key: 'item_name', sortable: false },
							{ title: __('Available Qty'), key: 'qty', align: 'center', sortable: false, width: '120px' },
							{ title: __('Void Qty'), key: 'void_qty', align: 'center', sortable: false, width: '120px' },
							{ title: __('Rate'), key: 'rate', align: 'end', sortable: false, width: '100px' },
							{ title: __('Amount'), key: 'amount', align: 'end', sortable: false, width: '100px' }
						]"
						:items="voidItemsData"
						density="compact"
						class="elevation-1"
						hide-default-footer
					>
						<template v-slot:item.select="{ item }">
							<v-checkbox
								v-model="item.selected"
								hide-details
								density="compact"
								@change="updateVoidSelection(item)"
							></v-checkbox>
						</template>
						
						<template v-slot:item.void_qty="{ item }">
							<v-text-field
								v-model.number="item.void_qty"
								type="number"
								:min="1"
								:max="item.original_qty"
								density="compact"
								hide-details
								style="width: 80px;"
								:disabled="!item.selected"
								@input="validateVoidQty(item)"
							></v-text-field>
						</template>
						
						<template v-slot:item.rate="{ item }">
							{{ currencySymbol(selectedOrderForVoid.currency) }}{{ formatCurrency(item.rate) }}
						</template>
						<template v-slot:item.amount="{ item }">
							{{ currencySymbol(selectedOrderForVoid.currency) }}{{ formatCurrency(item.amount) }}
						</template>
					</v-data-table>
					
					<div class="mt-4">
						<v-alert v-if="getSelectedVoidItems().length === 0" type="info" variant="tonal">
							{{ __("Please select items and specify quantities to void") }}
						</v-alert>
						<v-alert v-else type="success" variant="tonal">
							{{ __("Selected {0} item(s) for voiding with total quantity: {1}", [getSelectedVoidItems().length, getTotalVoidQty()]) }}
						</v-alert>
					</div>
				</v-card-text>
				
				<v-card-actions>
					<v-spacer></v-spacer>
					<v-btn 
						color="error" 
						@click="voidItemsDialog = false"
					>
						{{ __("Cancel") }}
					</v-btn>
					<v-btn
						color="warning"
						:loading="voidLoading"
						:disabled="getSelectedVoidItems().length === 0"
						@click="confirmVoidItems(selectedOrderForVoid, getSelectedVoidItems())"
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
		filter_status: "Draft", // Default to Draft status
		filter_date: null,
		search_text: "",
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
			// Void Items Dialog Data
			voidItemsDialog: false,
			selectedOrderForVoid: null,
			selectedItemsToVoid: [],
			voidItemsData: [], // Enhanced void items data with selection and quantity controls
			voidLoading: false,
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
					
					// Check if any orders have invalid names (empty or undefined)
					const invalidOrders = r.message.filter(o => !o.name || o.name.trim() === '');
					if (invalidOrders.length > 0) {
						console.error("CRITICAL: API returned orders with empty names:");
						invalidOrders.forEach(order => {
							console.error("  INVALID ORDER:", order);
						});
					}
				}
				console.log("=== END FETCH ORDERS DEBUG ===");
				
				console.log("API response:", r);
				
				if (r.message) {
					// Accept all restaurant orders regardless of naming series
					// No need to filter by naming convention
					const validOrders = r.message.filter(order => {
						const isValid = order.name && order.name.trim() !== '';
						if (!isValid) {
							console.warn("Filtering out invalid order entry:", order.name);
						}
						return isValid;
					});
					
					this.orders_data = validOrders;
					console.log("Orders data (all naming series accepted):", this.orders_data);
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
			// Only submitted orders that are not fully billed can be cancelled
			return order.docstatus === 1 && order.per_billed < 100;
		},

		canDelete(order) {
			return order.docstatus === 0; // Only draft orders can be deleted
		},

		canAddItems(order) {
			// Allow adding items only to orders that are not fully billed and have a table (dine-in orders)
			// Exclude fully billed orders (per_billed >= 100)
			return (order.docstatus === 0 || order.docstatus === 1) && 
			       order.table_number && 
			       order.per_billed < 100;
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
			
			// FIXED: Accept all valid order names, not just SAL-ORD- prefix
			// Valid restaurant order should have a name and be in our orders_data
			let validOrderName = order.name;
			const isValidOrder = order.name && 
				this.orders_data.some(o => o.name === order.name) && 
				order.restaurant_order_type; // Must be a restaurant order
			
			if (!isValidOrder) {
				console.error("CRITICAL: Selected order is invalid, attempting to find correct order...");
				
				// Try to find the order in orders_data by matching other properties
				const correctOrder = this.orders_data.find(o => 
					o.customer === order.customer && 
					Math.abs(o.grand_total - order.grand_total) < 0.01 &&
					o.restaurant_order_type // Must be a restaurant order
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
				
				// Validate that this is actually a restaurant order with a valid name
				if (!order.name || !order.restaurant_order_type) {
					this.eventBus.emit("show_message", {
						title: __("Invalid order format. Expected valid restaurant order."),
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

		async add_items_to_table(order) {
			try {
				console.log("Adding items to table for order:", order.name);
				
				// Close the restaurant orders dialog first
				this.close_dialog();
				
				// Set the order type and table information in the POS interface
				// This will prepare the POS for updating the existing order
				this.eventBus.emit("set_restaurant_context", {
					order_type: order.order_type_name,
					table_number: order.table_number,
					customer: order.customer,
					customer_name: order.customer_name,
					original_order: order.name,
					order_status: order.docstatus, // Pass the order status for API selection
					is_updating_order: true // Flag to indicate we're updating existing order
				});
				
				// Show success message with instructions
				this.eventBus.emit("show_message", {
					title: __("Ready to add items to {0}. Select items and click 'Update Order' to add items to existing order with KOT print.", [order.table_number]),
					color: "info",
					timeout: 6000
				});
				
			} catch (error) {
				console.error("Failed to prepare additional items order", error);
				this.eventBus.emit("show_message", {
					title: __("Error preparing additional order"),
					color: "error",
				});
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

		// Void Items Methods
		canVoidItems(order) {
			// Only allow voiding items from draft orders with items
			return order.docstatus === 0 && order.items && order.items.length > 0;
		},

		// KOT Reprint Methods
		canReprintKot(order) {
			// Allow reprint KOT for any order with items (draft or submitted)
			return order.items && order.items.length > 0;
		},

		async reprint_kot(order) {
			try {
				console.log("Reprinting KOT for order:", order.name);
				
				const r = await frappe.call({
					method: "posawesome.posawesome.api.restaurant_orders.reprint_kot",
					args: {
						order_name: order.name
					}
				});
				
				if (r.message) {
					// Open KOT in new window for printing
					const printWindow = window.open('', '_blank');
					printWindow.document.write(r.message);
					printWindow.document.close();
					printWindow.focus();
					printWindow.print();
					
					// Close the print window after printing
					setTimeout(() => {
						printWindow.close();
					}, 1000);
					
					this.eventBus.emit("show_message", {
						title: __("KOT reprinted successfully for order {0}", [order.name]),
						color: "success"
					});
				}
				
			} catch (error) {
				console.error("Error reprinting KOT:", error);
				this.eventBus.emit("show_message", {
					title: __("Error reprinting KOT: {0}", [error.message || "Unknown error"]),
					color: "error"
				});
			}
		},

		async void_items(order) {
			console.log("Opening void items dialog for order:", order);
			
			try {
				// Fetch full order details including items
				const r = await frappe.call({
					method: "frappe.client.get",
					args: {
						doctype: "Sales Order",
						name: order.name
					}
				});
				
				if (r.message) {
					this.selectedOrderForVoid = r.message;
					this.selectedItemsToVoid = [];
					this.voidItemsData = this.prepareVoidItemsData(r.message.items || []);
					this.voidLoading = false;
					this.voidItemsDialog = true;
				}
			} catch (error) {
				console.error("Error fetching order for voiding:", error);
				this.eventBus.emit("show_message", {
					title: __("Error fetching order details"),
					color: "error"
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
						color: "warning"
					});
					return;
				}
				
				// Map items for API call with void quantities
				const items_to_void = itemsToVoid.map(item => ({
					idx: item.idx,
					item_code: item.item_code,
					qty: item.qty // This is now the void_qty from the selection
				}));
				
				const r = await frappe.call({
					method: "posawesome.posawesome.api.restaurant_orders.void_order_items",
					args: {
						order_name: order.name,
						items_to_void: items_to_void
					}
				});
				
				if (r.message) {
					// Show success message
					this.eventBus.emit("show_message", {
						title: __("Items voided successfully"),
						color: "success"
					});
					
					// Handle KOT printing if available
					if (r.message.print_void_kot && r.message.void_kot_data) {
						console.log("Void KOT data:", r.message.void_kot_data);
						
						// Auto-print void KOT without confirmation
						await this.printVoidKot(r.message.void_kot_data);
					}
					
					// Reset dialog
					this.expanded = [];
					this.selectedOrderForVoid = null;
					this.voidItemsData = [];
					this.voidItemsDialog = false;
					await this.fetch_orders();
					
					// Update the specific order in the list
					const orderIndex = this.orders_data.findIndex(o => o.name === order.name);
					if (orderIndex !== -1) {
						try {
							const updated_order = await frappe.call({
								method: "frappe.client.get",
								args: {
									doctype: "Sales Order",
									name: order.name
								}
							});
							
							if (updated_order.message) {
								this.orders_data[orderIndex] = {
									...this.orders_data[orderIndex],
									items: updated_order.message.items,
									grand_total: updated_order.message.grand_total,
									net_total: updated_order.message.net_total
								};
								this.filter_orders();
							}
						} catch (update_error) {
							console.error("Error updating order in list:", update_error);
						}
					}
					
					// Close dialog
					this.voidItemsDialog = false;
					this.selectedOrderForVoid = null;
					this.selectedItemsToVoid = [];
				}
			} catch (error) {
				console.error("Error voiding items:", error);
				this.eventBus.emit("show_message", {
					title: __("Error voiding items: ") + (error.message || error),
					color: "error"
				});
			} finally {
				this.voidLoading = false;
				this.selectedItemsToVoid = [];
				this.voidItemsData = [];
			}
		},

		// Enhanced Void Items Methods
		prepareVoidItemsData(orderItems) {
			// Transform order items into void items data with selection controls
			return orderItems.map(item => ({
				...item,
				original_qty: item.qty,
				void_qty: 1, // Default void quantity
				selected: false
			}));
		},

		updateVoidSelection(item) {
			// When item is selected/deselected, reset void quantity
			if (item.selected) {
				item.void_qty = Math.min(1, item.original_qty);
			} else {
				item.void_qty = 1;
			}
		},

		validateVoidQty(item) {
			// Ensure void quantity is within valid range
			if (item.void_qty < 1) {
				item.void_qty = 1;
			} else if (item.void_qty > item.original_qty) {
				item.void_qty = item.original_qty;
			}
		},

		getSelectedVoidItems() {
			// Get items that are selected for voiding with their void quantities
			return this.voidItemsData.filter(item => item.selected && item.void_qty > 0).map(item => ({
				idx: item.idx,
				item_code: item.item_code,
				item_name: item.item_name,
				qty: item.void_qty,
				rate: item.rate,
				amount: item.void_qty * item.rate
			}));
		},

		getTotalVoidQty() {
			// Calculate total quantity being voided
			return this.getSelectedVoidItems().reduce((total, item) => total + item.qty, 0);
		},

		async printVoidKot(voidKotData) {
			try {
				// Import the KOT print utility
				const { printVoidKot } = await import("../../plugins/kot_print.js");
				
				// Use the utility function to print
				printVoidKot(voidKotData, { autoPrint: true });
				
			} catch (error) {
				console.error("Error printing void KOT:", error);
				this.eventBus.emit("show_message", {
					title: __("Error printing void KOT"),
					color: "error"
				});
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