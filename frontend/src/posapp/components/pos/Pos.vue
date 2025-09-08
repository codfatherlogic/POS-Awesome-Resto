<template>
	<div class="pos-main-container dynamic-container" :class="rtlClasses" :style="[responsiveStyles, rtlStyles]">
		<ClosingDialog></ClosingDialog>
		<Drafts></Drafts>
		<SalesOrders></SalesOrders>
		<RestaurantOrders></RestaurantOrders>
		<Returns></Returns>
		<NewAddress></NewAddress>
		<MpesaPayments></MpesaPayments>
		<Variants></Variants>
		<OpeningDialog v-if="dialog" :dialog="dialog"></OpeningDialog>
		
		<!-- POS Layout with Category Sidebar -->
		<div v-show="!dialog" class="pos-layout">
			<!-- Category Sidebar -->
			<CategorySidebar 
				v-show="!payment && !showOffers && !coupons"
				:item-groups="itemGroups"
				:selected-group="selectedItemGroup"
				:loading="loadingCategories"
				@group-selected="onGroupSelected"
				@sidebar-toggled="onSidebarToggled"
				@search-changed="onCategorySearch"
				@filter-changed="onFilterChanged"
			/>
			
			<!-- Main Content Area -->
			<div class="pos-main-content" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
				<v-row dense class="ma-0 dynamic-main-row">
					<v-col v-show="!payment && !showOffers && !coupons" xl="8" lg="8" md="7" sm="6" cols="12"
						class="pos dynamic-col">
						<ItemsSelector ref="itemsSelector"></ItemsSelector>
					</v-col>
					<v-col v-show="showOffers" xl="8" lg="8" md="7" sm="6" cols="12" class="pos dynamic-col">
						<PosOffers></PosOffers>
					</v-col>
					<v-col v-show="coupons" xl="8" lg="8" md="7" sm="6" cols="12" class="pos dynamic-col">
						<PosCoupons></PosCoupons>
					</v-col>
					<v-col v-show="payment" xl="8" lg="8" md="7" sm="6" cols="12" class="pos dynamic-col">
						<Payments></Payments>
					</v-col>

					<v-col xl="4" lg="4" md="5" sm="6" cols="12" class="pos dynamic-col">
						<Invoice></Invoice>
					</v-col>
				</v-row>
			</div>
		</div>
	</div>
</template>

<script>
import ItemsSelector from "./ItemsSelector.vue";
import Invoice from "./Invoice.vue";
import OpeningDialog from "./OpeningDialog.vue";
import Payments from "./Payments.vue";
import PosOffers from "./PosOffers.vue";
import PosCoupons from "./PosCoupons.vue";
import Drafts from "./Drafts.vue";
import SalesOrders from "./SalesOrders.vue";
import RestaurantOrders from "./RestaurantOrders.vue";
import ClosingDialog from "./ClosingDialog.vue";
import NewAddress from "./NewAddress.vue";
import Variants from "./Variants.vue";
import Returns from "./Returns.vue";
import MpesaPayments from "./Mpesa-Payments.vue";
import CategorySidebar from "./CategorySidebar.vue";
import {
	getOpeningStorage,
	setOpeningStorage,
	clearOpeningStorage,
	initPromise,
	checkDbHealth,
	setTaxTemplate,
} from "../../../offline/index.js";
import { getCurrentInstance } from "vue";
import { usePosShift } from "../../composables/usePosShift.js";
import { useOffers } from "../../composables/useOffers.js";
// Import the cache cleanup function
import { clearExpiredCustomerBalances } from "../../../offline/index.js";
import { useResponsive } from "../../composables/useResponsive.js";
import { useRtl } from "../../composables/useRtl.js";

export default {
	setup() {
		const instance = getCurrentInstance();
		const responsive = useResponsive();
		const rtl = useRtl();
		const shift = usePosShift(() => {
			if (instance && instance.proxy) {
				instance.proxy.dialog = true;
			}
		});
		const offers = useOffers();
		return { ...responsive, ...rtl, ...shift, ...offers };
	},
	data: function () {
		return {
			dialog: false,
			payment: false,
			showOffers: false,
			coupons: false,
			itemsLoaded: false,
			customersLoaded: false,
			
			// Category Sidebar Data
			itemGroups: [],
			selectedItemGroup: 'ALL',
			sidebarCollapsed: false,
			loadingCategories: false,
			categorySearchTerm: '',
			activeFilter: 'all'
		};
	},

	components: {
		ItemsSelector,
		Invoice,
		OpeningDialog,
		Payments,
		Drafts,
		ClosingDialog,
		Returns,
		PosOffers,
		PosCoupons,
		SalesOrders,
		RestaurantOrders,
		NewAddress,
		Variants,
		MpesaPayments,
		CategorySidebar,
	},

	methods: {
		create_opening_voucher() {
			this.dialog = true;
		},
		get_pos_setting() {
			frappe.db.get_doc("POS Settings", undefined).then((doc) => {
				this.eventBus.emit("set_pos_settings", doc);
			});
		},
		checkLoadingComplete() {
			if (this.itemsLoaded && this.customersLoaded) {
				console.info("Loading completed");
			}
		},
		
		// Category Sidebar Methods
		onGroupSelected(groupName) {
			this.selectedItemGroup = groupName;
			// Update the ItemsSelector component with the selected group
			if (this.$refs.itemsSelector) {
				this.$refs.itemsSelector.item_group = groupName;
			}
			// Emit event for ItemsSelector to handle
			this.eventBus.emit('item_group_changed', groupName);
		},
		
		onSidebarToggled(isCollapsed) {
			this.sidebarCollapsed = isCollapsed;
			// Adjust main content layout
			this.$nextTick(() => {
				this.adjustLayout();
			});
		},
		
		onCategorySearch(searchTerm) {
			this.categorySearchTerm = searchTerm;
			// Filter categories based on search
			this.filterCategories();
		},
		
		onFilterChanged(filter) {
			this.activeFilter = filter;
			// Apply filter to categories
			this.applyFilter(filter);
		},
		
		filterCategories() {
			// This method can be used to filter categories based on search
			// Implementation will depend on your data structure
		},
		
		applyFilter(filter) {
			// Apply different filters (all, popular, recent)
			// Implementation will depend on your requirements
		},
		
		adjustLayout() {
			// Adjust item grid layout when sidebar is toggled
			// This can be used to trigger layout recalculation
			this.eventBus.emit('layout_adjusted', this.sidebarCollapsed);
		},
		
		loadItemGroups() {
			// Load item groups for the sidebar
			// This should get the item groups from ItemsSelector or API
			if (this.$refs.itemsSelector && this.$refs.itemsSelector.items_group) {
				const groups = this.$refs.itemsSelector.items_group.map(group => ({
					name: group,
					item_count: 0, // This should be calculated based on filtered items
					stock_value: 0 // Optional: calculate stock value
				}));
				this.itemGroups = groups;
			}
		},
	},

	mounted: function () {
		this.$nextTick(function () {
			this.check_opening_entry();
			this.get_pos_setting();
			this.eventBus.on("close_opening_dialog", () => {
				this.dialog = false;
			});
			this.eventBus.on("register_pos_data", (data) => {
				this.pos_profile = data.pos_profile;
				this.get_offers(this.pos_profile.name, this.pos_profile);
				this.pos_opening_shift = data.pos_opening_shift;
				this.eventBus.emit("register_pos_profile", data);
				console.info("LoadPosProfile");
			});
			// When profile is registered directly from composables,
			// ensure offers are fetched as well
			this.eventBus.on("register_pos_profile", (data) => {
				if (data && data.pos_profile) {
					this.get_offers(data.pos_profile.name, data.pos_profile);
				}
			});
			this.eventBus.on("show_payment", (data) => {
				this.payment = data === "true";
				this.showOffers = false;
				this.coupons = false;
			});
			this.eventBus.on("show_offers", (data) => {
				this.showOffers = data === "true";
				this.payment = false;
				this.coupons = false;
			});
			this.eventBus.on("show_coupons", (data) => {
				this.coupons = data === "true";
				this.showOffers = false;
				this.payment = false;
			});
			this.eventBus.on("open_closing_dialog", () => {
				this.get_closing_data();
			});
			this.eventBus.on("submit_closing_pos", (data) => {
				this.submit_closing_pos(data);
			});

			this.eventBus.on("items_loaded", () => {
				this.itemsLoaded = true;
				this.checkLoadingComplete();
			});
			this.eventBus.on("customers_loaded", () => {
				this.customersLoaded = true;
				this.checkLoadingComplete();
			});
			
			// Listen for item groups data from ItemsSelector
			this.eventBus.on("item_groups_data", (groupsData) => {
				this.itemGroups = groupsData;
			});
		});
	},
	beforeUnmount() {
		this.eventBus.off("close_opening_dialog");
		this.eventBus.off("register_pos_data");
		this.eventBus.off("register_pos_profile");
		this.eventBus.off("LoadPosProfile");
		this.eventBus.off("show_offers");
		this.eventBus.off("show_coupons");
		this.eventBus.off("open_closing_dialog");
		this.eventBus.off("submit_closing_pos");
		this.eventBus.off("items_loaded");
		this.eventBus.off("customers_loaded");
		this.eventBus.off("item_groups_data");
	},
	// In the created() or mounted() lifecycle hook
	created() {
		// Clean up expired customer balance cache on POS load
		clearExpiredCustomerBalances();
	},
};
</script>

<style scoped>
.dynamic-container {
	/* add space for the navbar with better spacing */
	/*padding-top: calc(25px + var(--dynamic-lg));*/
	/* Navbar height (25px) + larger spacing */
	transition: all 0.3s ease;
}

.dynamic-main-row {
	padding: 0;
	margin: 0;
	height: 100%;
	overflow: hidden;
}

.dynamic-col {
	padding: var(--dynamic-sm);
	transition: padding 0.3s ease;
	margin-top: var(--dynamic-sm);
	/* Add top margin for better separation */
	display: flex;
	flex-direction: column;
	height: 100%;
}

/* New POS Layout Styles */
.pos-layout {
	display: flex;
	height: calc(100vh - 64px);
	overflow: hidden;
}

.pos-main-content {
	flex: 1;
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	overflow: hidden;
	display: flex;
	flex-direction: column;
}

.pos-main-content.sidebar-collapsed {
	/* Additional space when sidebar is collapsed */
	padding-left: 8px;
}

/* Responsive adjustments */
@media (max-width: 1200px) {
	.pos-layout {
		height: calc(100vh - 56px);
	}
}

@media (max-width: 768px) {
	.dynamic-container {
		padding-top: calc(56px + var(--dynamic-md));
		/* Consistent navbar height + medium spacing */
	}

	.dynamic-col {
		padding: var(--dynamic-xs);
		margin-top: var(--dynamic-xs);
	}
	
	.pos-layout {
		flex-direction: column;
		height: calc(100vh - 56px);
	}
	
	.pos-main-content,
	.pos-main-content.sidebar-collapsed {
		padding-left: 0;
	}
	
	/* Hide sidebar on mobile or make it overlay */
	.pos-layout .category-sidebar {
		position: fixed;
		top: 56px;
		left: 0;
		z-index: 1000;
		height: calc(100vh - 56px);
		transform: translateX(-100%);
		transition: transform 0.3s ease;
	}
	
	.pos-layout .category-sidebar.mobile-open {
		transform: translateX(0);
	}
}
</style>
