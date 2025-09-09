<template>
	<v-card
		:class="['cards mb-0 mt-3 py-2 px-3 rounded-lg resizable', isDarkTheme ? '' : 'bg-grey-lighten-4']"
		:style="(isDarkTheme ? 'background-color:#1E1E1E;' : '') + 'resize: vertical; overflow: auto;'"
	>
		<!-- First Row: Total, Make Order/Pay, Show Orders -->
		<v-row dense class="mb-1">
			<v-col cols="4">
				<v-text-field
					:model-value="formatFloat(subtotal)"
					:label="frappe._('Total')"
					prepend-inner-icon="mdi-cash"
					variant="solo"
					density="compact"
					readonly
					color="success"
					class="summary-field"
				/>
			</v-col>
			<!-- In Direct Order modes, show PAY button instead of Make Order -->
			<v-col cols="4" v-if="isDirectOrderMode">
				<v-btn
					block
					color="success"
					theme="dark"
					prepend-icon="mdi-cash-multiple"
					@click="handleShowPayment"
					class="summary-btn pay-btn"
					:loading="paymentLoading"
				>
					{{ __("PAY") }}
				</v-btn>
			</v-col>
			<!-- Standard restaurant mode - Make Order button -->
			<v-col cols="4" v-else-if="isStandardRestaurantMode">
				<v-btn
					block
					color="accent"
					theme="dark"
					prepend-icon="mdi-receipt"
					@click="handleSaveAndClear"
					class="summary-btn"
					:loading="saveLoading"
				>
					{{ hasExistingOrder ? __("Update Order") : __("Make Order") }}
				</v-btn>
			</v-col>
			<!-- Regular POS mode - Save & Clear button -->
			<v-col cols="4" v-else>
				<v-btn
					block
					color="accent"
					theme="dark"
					prepend-icon="mdi-content-save"
					@click="handleSaveAndClear"
					class="summary-btn"
					:loading="saveLoading"
				>
					{{ __("Save & Clear") }}
				</v-btn>
			</v-col>
			<!-- Show Orders button (only in standard restaurant mode) -->
			<v-col cols="4" v-if="isStandardRestaurantMode">
				<v-btn
					block
					color="info"
					theme="dark"
					prepend-icon="mdi-view-list"
					@click="handleShowOrders"
					class="summary-btn"
					:loading="showOrdersLoading"
				>
					{{ __("Show Orders") }}
				</v-btn>
			</v-col>
			<!-- Select Sales Order button (for non-restaurant mode with custom flag) -->
			<v-col cols="4" v-else-if="!pos_profile.posa_enable_restaurant_mode && pos_profile.custom_allow_select_sales_order == 1">
				<v-btn
					block
					color="info"
					theme="dark"
					prepend-icon="mdi-file-search"
					@click="handleSelectOrder"
					class="summary-btn"
					:loading="selectOrderLoading"
				>
					{{ __("Select S.O") }}
				</v-btn>
			</v-col>
			<!-- Spacer for direct order modes to maintain layout -->
			<v-col cols="4" v-else-if="isDirectOrderMode">
				<!-- Empty spacer column -->
			</v-col>
		</v-row>

		<!-- Second Row: Cancel Sale, Sales Return, PAY (only in standard modes) -->
		<v-row dense>
			<v-col cols="4">
				<v-btn
					block
					color="error"
					theme="dark"
					prepend-icon="mdi-cancel"
					@click="handleCancelSale"
					class="summary-btn"
					:loading="cancelLoading"
				>
					{{ __("Cancel Sale") }}
				</v-btn>
			</v-col>
			<v-col cols="4" v-if="pos_profile.posa_allow_return == 1">
				<v-btn
					block
					color="secondary"
					theme="dark"
					prepend-icon="mdi-undo-variant"
					@click="handleOpenReturns"
					class="summary-btn"
					:loading="returnsLoading"
				>
					{{ __("Sales Return") }}
				</v-btn>
			</v-col>
			<v-col cols="4" v-else-if="pos_profile.posa_allow_print_draft_invoices">
				<v-btn
					block
					color="primary"
					theme="dark"
					prepend-icon="mdi-printer"
					@click="handlePrintDraft"
					class="summary-btn"
					:loading="printLoading"
				>
					{{ __("Print Draft") }}
				</v-btn>
			</v-col>
			<!-- PAY button (only shown in standard modes, hidden in direct order modes since PAY is in first row) -->
			<v-col cols="4" v-if="!isDirectOrderMode">
				<v-btn
					block
					color="success"
					theme="dark"
					prepend-icon="mdi-cash-multiple"
					@click="handleShowPayment"
					class="summary-btn pay-btn"
					:loading="paymentLoading"
				>
					{{ __("PAY") }}
				</v-btn>
			</v-col>
		</v-row>
	</v-card>
</template>

<script>
export default {
	props: {
		pos_profile: Object,
		invoice_doc: Object,
		total_qty: [Number, String],
		additional_discount: Number,
		additional_discount_percentage: Number,
		total_items_discount_amount: Number,
		subtotal: Number,
		displayCurrency: String,
		formatFloat: Function,
		formatCurrency: Function,
		currencySymbol: Function,
		discount_percentage_offer_name: [String, Number],
		isNumber: Function,
		restaurant_add_items_context: Object,
	},
	data() {
		return {
			// Loading states for better UX
			saveLoading: false,
			loadDraftsLoading: false,
			selectOrderLoading: false,
			showOrdersLoading: false,
			submitOrderLoading: false,
			cancelLoading: false,
			returnsLoading: false,
			printLoading: false,
			paymentLoading: false,
		};
	},
	emits: [
		"update:additional_discount",
		"update:additional_discount_percentage",
		"update_discount_umount",
		"save-and-clear",
		"load-drafts",
		"select-order",
		"show-orders",
		"submit-order",
		"cancel-sale",
		"open-returns",
		"print-draft",
		"show-payment",
	],
	computed: {
		isDarkTheme() {
			return this.$theme?.current === "dark";
		},
		// Check if we're in standard restaurant mode (not direct order modes)
		isStandardRestaurantMode() {
			return this.pos_profile.posa_enable_restaurant_mode && 
				   (!this.pos_profile.posa_order_mode || this.pos_profile.posa_order_mode === 'Standard');
		},
		// Check if we're in any direct order mode
		isDirectOrderMode() {
			return this.pos_profile.posa_enable_restaurant_mode && 
				   (this.pos_profile.posa_order_mode === 'Direct Order' || this.pos_profile.posa_order_mode === 'Direct Order + KOT');
		},
		// Check if we're in standard restaurant mode (not direct order modes)
		isStandardRestaurantMode() {
			return this.pos_profile.posa_enable_restaurant_mode && 
				   (!this.pos_profile.posa_order_mode || this.pos_profile.posa_order_mode === 'Standard');
		},
		// Check if we're in any direct order mode
		isDirectOrderMode() {
			return this.pos_profile.posa_enable_restaurant_mode && 
				   (this.pos_profile.posa_order_mode === 'Direct Order' || this.pos_profile.posa_order_mode === 'Direct Order + KOT');
		},
		// Check if we're in direct order with KOT mode  
		isDirectOrderWithKOT() {
			return this.pos_profile.posa_enable_restaurant_mode && 
				   this.pos_profile.posa_order_mode === 'Direct Order + KOT';
		},
		hide_qty_decimals() {
			try {
				const saved = localStorage.getItem("posawesome_item_selector_settings");
				if (saved) {
					const opts = JSON.parse(saved);
					return !!opts.hide_qty_decimals;
				}
			} catch (e) {
				console.error("Failed to load item selector settings:", e);
			}
			return false;
		},
		hasExistingOrder() {
			// Check if we have an existing order loaded OR if we're adding items to an existing order
			return !!(this.invoice_doc && this.invoice_doc.name) || 
					 !!(this.restaurant_add_items_context && this.restaurant_add_items_context.is_updating_order);
		},
	},
	methods: {
		// Debounced handlers for better performance
		handleAdditionalDiscountUpdate(value) {
			this.$emit("update:additional_discount", value);
		},

		handleAdditionalDiscountPercentageUpdate(value) {
			this.$emit("update:additional_discount_percentage", value);
		},

		async handleSaveAndClear() {
			this.saveLoading = true;
			try {
				await this.$emit("save-and-clear");
			} finally {
				this.saveLoading = false;
			}
		},

		async handleLoadDrafts() {
			this.loadDraftsLoading = true;
			try {
				await this.$emit("load-drafts");
			} finally {
				this.loadDraftsLoading = false;
			}
		},

		async handleSelectOrder() {
			this.selectOrderLoading = true;
			try {
				await this.$emit("select-order");
			} finally {
				this.selectOrderLoading = false;
			}
		},

		async handleShowOrders() {
			this.showOrdersLoading = true;
			try {
				await this.$emit("show-orders");
			} finally {
				this.showOrdersLoading = false;
			}
		},

		async handleSubmitOrder() {
			this.submitOrderLoading = true;
			try {
				await this.$emit("submit-order");
			} finally {
				this.submitOrderLoading = false;
			}
		},

		async handleCancelSale() {
			this.cancelLoading = true;
			try {
				await this.$emit("cancel-sale");
			} finally {
				this.cancelLoading = false;
			}
		},

		async handleOpenReturns() {
			this.returnsLoading = true;
			try {
				await this.$emit("open-returns");
			} finally {
				this.returnsLoading = false;
			}
		},

		async handlePrintDraft() {
			this.printLoading = true;
			try {
				await this.$emit("print-draft");
			} finally {
				this.printLoading = false;
			}
		},

		async handleShowPayment() {
			this.paymentLoading = true;
			try {
				await this.$emit("show-payment");
			} finally {
				this.paymentLoading = false;
			}
		},
	},
};
</script>

<style scoped>
.cards {
	background-color: #f5f5f5 !important;
	transition: all 0.3s ease;
}

:deep([data-theme="dark"]) .cards,
:deep([data-theme="dark"]) .cards .v-card__underlay,
:deep(.v-theme--dark) .cards,
:deep(.v-theme--dark) .cards .v-card__underlay,
:deep(.cards.v-theme--dark),
:deep(.cards.v-theme--dark) .v-card__underlay,
::v-deep([data-theme="dark"]) .cards,
::v-deep([data-theme="dark"]) .cards .v-card__underlay,
::v-deep(.v-theme--dark) .cards,
::v-deep(.v-theme--dark) .cards .v-card__underlay,
::v-deep(.cards.v-theme--dark),
::v-deep(.cards.v-theme--dark) .v-card__underlay {
	background-color: #1e1e1e !important;
}

.white-text-btn {
	color: white !important;
}

.white-text-btn :deep(.v-btn__content) {
	color: white !important;
}

/* Enhanced button styling with better performance */
.summary-btn {
	transition: all 0.2s ease !important;
	position: relative;
	overflow: hidden;
	font-size: 0.8rem !important;
}

.summary-btn :deep(.v-btn__content) {
	white-space: normal !important;
	transition: all 0.2s ease;
}

/* Consistent icon sizing for all buttons */
.summary-btn :deep(.v-btn__prepend) .v-icon {
	font-size: 20px !important;
}

.summary-field :deep(.v-field__prepend-inner) .v-icon {
	font-size: 20px !important;
}

.summary-btn:hover {
	transform: translateY(-1px);
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15) !important;
}

.summary-btn:active {
	transform: translateY(0);
}

/* Special styling for the PAY button */
.pay-btn {
	font-weight: 600 !important;
	font-size: 0.9rem !important;
	background: linear-gradient(135deg, #4caf50, #45a049) !important;
	box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3) !important;
}

.pay-btn:hover {
	background: linear-gradient(135deg, #45a049, #3d8b40) !important;
	box-shadow: 0 6px 16px rgba(76, 175, 80, 0.4) !important;
	transform: translateY(-2px);
}

/* Enhanced field styling */
.summary-field {
	transition: all 0.2s ease;
}

.summary-field:hover {
	transform: translateY(-1px);
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Responsive optimizations */
@media (max-width: 768px) {
	.summary-btn {
		font-size: 0.75rem !important;
		padding: 8px 12px !important;
	}

	.pay-btn {
		font-size: 0.8rem !important;
	}

	.summary-field {
		font-size: 0.875rem;
	}
}

@media (max-width: 480px) {
	.summary-btn {
		font-size: 0.7rem !important;
		padding: 6px 8px !important;
	}

	.pay-btn {
		font-size: 0.75rem !important;
	}
}

/* Loading state animations */
.summary-btn:deep(.v-btn__loader) {
	opacity: 0.8;
}

/* Dark theme enhancements */
:deep([data-theme="dark"]) .summary-btn,
:deep(.v-theme--dark) .summary-btn {
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
}

:deep([data-theme="dark"]) .summary-btn:hover,
:deep(.v-theme--dark) .summary-btn:hover {
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
}
</style>
