<template>
	<v-row align="center" class="items px-3 py-2 mt-0" v-if="pos_profile.posa_enable_restaurant_mode">
		<!-- Order Type Selection -->
		<v-col cols="12" sm="6" class="pb-0 mb-0 pr-2 pt-0">
			<v-select
				density="compact"
				variant="solo"
				color="primary"
				:label="frappe._('Order Type') + ' *'"
				:placeholder="frappe._('Select Order Type (Required)')"
				v-model="internal_selected_order_type"
				:items="order_types"
				item-title="order_type_name"
				item-value="name"
				return-object
				:bg-color="isDarkTheme ? '#1E1E1E' : 'white'"
				class="dark-field sleek-field"
				:class="{ 'error-field': !internal_selected_order_type && showValidation }"
				:no-data-text="__('No order types found')"
				hide-details
				:disabled="readonly"
				@update:model-value="onOrderTypeUpdate"
			>
				<template v-slot:item="{ props, item }">
					<v-list-item v-bind="props">
						<v-list-item-title
							class="text-primary text-subtitle-1"
							v-html="item.raw.order_type_name"
						></v-list-item-title>
						<v-list-item-subtitle v-if="item.raw.default_preparation_time">
							{{ __('Prep Time: {0} min', [item.raw.default_preparation_time]) }}
						</v-list-item-subtitle>
					</v-list-item>
				</template>
			</v-select>
		</v-col>

		<!-- Table Selection (Only shown if order type requires table) -->
		<v-col
			v-if="showTableSelection"
			cols="12"
			sm="6"
			class="pb-0 mb-0 pl-2 pt-0"
		>
			<v-select
				density="compact"
				variant="solo"
				color="primary"
				:label="frappe._('Table Number') + ' *'"
				v-model="internal_selected_table"
				:items="available_tables"
				item-title="table_display"
				item-value="table_number"
				return-object
				:bg-color="isDarkTheme ? '#1E1E1E' : 'white'"
				class="dark-field sleek-field"
				:class="{ 'error-field': showTableSelection && !internal_selected_table && showValidation }"
				:no-data-text="__('No tables available')"
				hide-details
				:disabled="readonly"
				@update:model-value="onTableUpdate"
			>
				<template v-slot:item="{ props, item }">
					<v-list-item v-bind="props">
						<v-list-item-title
							class="text-primary text-subtitle-1"
							v-html="item.raw.table_display"
						></v-list-item-title>
						<v-list-item-subtitle v-if="item.raw.capacity">
							{{ __('Capacity: {0} seats', [item.raw.capacity]) }}
							<span v-if="item.raw.location"> • {{ item.raw.location }}</span>
						</v-list-item-subtitle>
					</v-list-item>
				</template>
			</v-select>
		</v-col>

		<!-- Order Status Indicator -->
		<v-col v-if="order_status" cols="12" class="pt-1 pb-0">
			<v-chip
				:color="getStatusColor(order_status)"
				size="small"
				variant="flat"
			>
				<v-icon start size="small">{{ getStatusIcon(order_status) }}</v-icon>
				{{ order_status }}
			</v-chip>
		</v-col>
		
		<!-- Validation Message -->
		<v-col v-if="showValidationMessage" cols="12" class="pt-1 pb-0">
			<v-alert
				type="error"
				density="compact"
				class="mb-0"
				variant="tonal"
			>
				<v-icon start>mdi-alert-circle</v-icon>
				{{ validationMessage }}
			</v-alert>
		</v-col>
		
		<!-- Mandatory Selection Notice -->
		<v-col v-if="!internal_selected_order_type" cols="12" class="pt-1 pb-0">
			<v-alert
				type="info"
				density="compact"
				class="mb-0"
				variant="tonal"
			>
				<v-icon start>mdi-information</v-icon>
				{{ __("Order Type selection is mandatory before adding items to cart") }}
			</v-alert>
		</v-col>
	</v-row>
</template>

<script>
export default {
	props: {
		pos_profile: Object,
		order_types: Array,
		available_tables: Array,
		selected_order_type: [Object, String],
		selected_table: [Object, String],
		order_status: String,
		readonly: Boolean,
	},
	data() {
		return {
			internal_selected_order_type: this.selected_order_type,
			internal_selected_table: this.selected_table,
			showValidation: false,
		};
	},
	computed: {
		isDarkTheme() {
			return this.$theme?.current === "dark";
		},
		showTableSelection() {
			return (
				this.internal_selected_order_type &&
				this.internal_selected_order_type.requires_table &&
				this.available_tables &&
				this.available_tables.length > 0
			);
		},
		showValidationMessage() {
			return this.showValidation && this.validationMessage;
		},
		validationMessage() {
			if (!this.internal_selected_order_type) {
				return __("⚠️ Order Type is mandatory - Please select before adding items");
			}
			if (this.showTableSelection && !this.internal_selected_table) {
				return __("⚠️ Table selection required for {0} orders", [this.internal_selected_order_type.order_type_name]);
			}
			return "";
		},
	},
	watch: {
		selected_order_type(val) {
			this.internal_selected_order_type = val;
		},
		selected_table(val) {
			this.internal_selected_table = val;
		},
		available_tables: {
			handler(newTables) {
				// Add display text for tables
				if (newTables) {
					newTables.forEach(table => {
						table.table_display = table.table_name 
							? `${table.table_number} - ${table.table_name}`
							: table.table_number;
					});
				}
			},
			immediate: true,
		},
	},
	methods: {
		onOrderTypeUpdate(val) {
			this.$emit("update:selected_order_type", val);
			// Clear table selection if new order type doesn't require table
			if (!val || !val.requires_table) {
				this.internal_selected_table = null;
				this.$emit("update:selected_table", null);
			}
		},
		onTableUpdate(val) {
			this.$emit("update:selected_table", val);
		},
		getStatusColor(status) {
			const statusColors = {
				'Draft': 'orange',
				'Submitted': 'blue',
				'Preparing': 'amber',
				'Ready': 'green',
				'Served': 'success',
				'Billed': 'purple',
				'Cancelled': 'error',
			};
			return statusColors[status] || 'grey';
		},
		getStatusIcon(status) {
			const statusIcons = {
				'Draft': 'mdi-file-document-outline',
				'Submitted': 'mdi-check-circle-outline',
				'Preparing': 'mdi-chef-hat',
				'Ready': 'mdi-bell-ring',
				'Served': 'mdi-silverware-fork-knife',
				'Billed': 'mdi-receipt',
				'Cancelled': 'mdi-cancel',
			};
			return statusIcons[status] || 'mdi-information-outline';
		},
		validateSelection() {
			this.showValidation = true;
			return this.internal_selected_order_type &&
				   (!this.showTableSelection || this.internal_selected_table);
		},
	},
};
</script>

<style scoped>
:deep([data-theme="dark"]) .dark-field,
:deep(.v-theme--dark) .dark-field,
::v-deep([data-theme="dark"]) .dark-field,
::v-deep(.v-theme--dark) .dark-field {
	background-color: #1e1e1e !important;
}

:deep([data-theme="dark"]) .dark-field :deep(.v-field__input),
:deep(.v-theme--dark) .dark-field :deep(.v-field__input),
:deep([data-theme="dark"]) .dark-field :deep(input),
:deep(.v-theme--dark) .dark-field :deep(input),
:deep([data-theme="dark"]) .dark-field :deep(.v-label),
:deep(.v-theme--dark) .dark-field :deep(.v-label),
::v-deep([data-theme="dark"]) .dark-field .v-field__input,
::v-deep(.v-theme--dark) .dark-field .v-field__input,
::v-deep([data-theme="dark"]) .dark-field input,
::v-deep(.v-theme--dark) .dark-field input,
::v-deep([data-theme="dark"]) .dark-field .v-label,
::v-deep(.v-theme--dark) .dark-field .v-label {
	color: #fff !important;
}

:deep([data-theme="dark"]) .dark-field :deep(.v-field__overlay),
:deep(.v-theme--dark) .dark-field :deep(.v-field__overlay),
::v-deep([data-theme="dark"]) .dark-field .v-field__overlay,
::v-deep(.v-theme--dark) .dark-field .v-field__overlay {
	background-color: #1e1e1e !important;
}

.sleek-field {
	border-radius: 8px;
}

.error-field {
	border: 2px solid rgb(var(--v-theme-error)) !important;
}

.error-field :deep(.v-field__outline) {
	border-color: rgb(var(--v-theme-error)) !important;
}
</style>