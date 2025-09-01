<template>
  <div class="category-sidebar" :class="{ collapsed: isCollapsed }">
    <!-- Sidebar Header -->
    <div class="sidebar-header">
      <div class="header-content">
        <i class="fas fa-layer-group header-icon" v-if="!isCollapsed"></i>
        <h3 v-if="!isCollapsed">{{ __('Categories') }}</h3>
      </div>
      <v-btn
        icon
        size="small"
        variant="outlined"
        class="collapse-btn"
        @click="toggleSidebar"
        :title="isCollapsed ? __('Expand Categories') : __('Collapse Categories')"
      >
        <v-icon>{{ isCollapsed ? 'mdi-chevron-right' : 'mdi-chevron-left' }}</v-icon>
      </v-btn>
    </div>
    
    <!-- Search Section - Only visible when expanded -->
    <div v-if="!isCollapsed" class="search-section">
      <v-text-field
        v-model="searchTerm"
        :placeholder="__('Search categories...')"
        density="compact"
        variant="outlined"
        clearable
        hide-details
        prepend-inner-icon="mdi-magnify"
        @input="onSearchInput"
        @click:clear="clearSearch"
        class="category-search"
      >
      </v-text-field>
    </div>

    <!-- Quick Filters - Only visible when expanded -->
    <div v-if="!isCollapsed && !searchTerm" class="quick-filters">
      <v-btn-toggle
        v-model="selectedFilter"
        color="primary"
        density="compact"
        variant="outlined"
        divided
        mandatory
      >
        <v-btn
          value="all"
          size="small"
          @click="setFilter('all')"
        >
          <v-icon left size="small">mdi-view-grid</v-icon>
          {{ __('All') }}
        </v-btn>
        <v-btn
          value="popular"
          size="small"
          @click="setFilter('popular')"
        >
          <v-icon left size="small">mdi-star</v-icon>
          {{ __('Popular') }}
        </v-btn>
        <v-btn
          value="recent"
          size="small"
          @click="setFilter('recent')"
        >
          <v-icon left size="small">mdi-clock-outline</v-icon>
          {{ __('Recent') }}
        </v-btn>
      </v-btn-toggle>
    </div>

    <!-- Category List -->
    <div class="category-list" ref="categoryList">
      <div 
        v-for="group in filteredGroups" 
        :key="group.name"
        class="category-item"
        :class="{ 
          active: selectedGroup === group.name,
          'has-items': group.item_count > 0,
          'no-stock': group.item_count === 0
        }"
        @click="selectGroup(group)"
        :title="isCollapsed ? group.name : `${group.name} (${group.item_count} items)`"
      >
        <div class="category-icon" :style="{ color: getCategoryColor(group.name) }">
          <v-icon size="large">{{ getGroupIcon(group.name) }}</v-icon>
        </div>
        
        <div v-if="!isCollapsed" class="category-details">
          <span class="category-name">{{ group.name }}</span>
          <div class="category-meta">
            <v-chip 
              size="x-small" 
              :color="group.item_count > 0 ? 'primary' : 'grey'"
              variant="flat"
            >
              {{ group.item_count }} {{ __('items') }}
            </v-chip>
            <span v-if="group.stock_value" class="stock-value">
              ₹{{ formatCurrency(group.stock_value) }}
            </span>
          </div>
        </div>
        
        <div v-if="!isCollapsed && group.item_count > 0" class="category-arrow">
          <v-icon size="small">mdi-chevron-right</v-icon>
        </div>

        <!-- Item count badge for collapsed view -->
        <div v-if="isCollapsed && group.item_count > 0" class="item-badge">
          {{ group.item_count }}
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="filteredGroups.length === 0" class="empty-state">
        <div class="empty-icon">
          <v-icon size="48" color="grey">mdi-folder-search-outline</v-icon>
        </div>
        <p v-if="!isCollapsed" class="empty-text">
          {{ searchTerm ? __('No categories found') : __('No categories available') }}
        </p>
      </div>
    </div>

    <!-- Footer Stats - Only visible when expanded -->
    <div v-if="!isCollapsed" class="sidebar-footer">
      <v-divider></v-divider>
      <div class="stats">
        <div class="stat-item">
          <span class="stat-label">{{ __('Total Categories') }}:</span>
          <v-chip size="x-small" color="primary">{{ totalCategories }}</v-chip>
        </div>
        <div class="stat-item">
          <span class="stat-label">{{ __('Total Items') }}:</span>
          <v-chip size="x-small" color="success">{{ totalItems }}</v-chip>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { debounce } from 'lodash';

export default {
  name: 'CategorySidebar',
  props: {
    itemGroups: {
      type: Array,
      default: () => []
    },
    selectedGroup: {
      type: String,
      default: null
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['group-selected', 'sidebar-toggled', 'search-changed', 'filter-changed'],
  
  data() {
    return {
      isCollapsed: false,
      searchTerm: '',
      selectedFilter: 'all',
      recentGroups: [], // Store recently selected groups
      searchTimeout: null
    }
  },

  computed: {
    filteredGroups() {
      let groups = [...this.itemGroups];
      
      // Apply search filter
      if (this.searchTerm) {
        const searchLower = this.searchTerm.toLowerCase();
        groups = groups.filter(group => 
          group.name.toLowerCase().includes(searchLower)
        );
      }
      
      // Apply quick filters
      switch (this.selectedFilter) {
        case 'popular':
          // Sort by item count (most items first)
          groups = groups.sort((a, b) => (b.item_count || 0) - (a.item_count || 0));
          break;
        case 'recent':
          // Show recently selected categories first
          groups = groups.sort((a, b) => {
            const aIndex = this.recentGroups.indexOf(a.name);
            const bIndex = this.recentGroups.indexOf(b.name);
            if (aIndex === -1 && bIndex === -1) return 0;
            if (aIndex === -1) return 1;
            if (bIndex === -1) return -1;
            return aIndex - bIndex;
          });
          break;
        default:
          // Sort alphabetically
          groups = groups.sort((a, b) => a.name.localeCompare(b.name));
      }
      
      return groups;
    },
    
    totalCategories() {
      return this.itemGroups.length;
    },
    
    totalItems() {
      return this.itemGroups.reduce((sum, group) => sum + (group.item_count || 0), 0);
    }
  },

  methods: {
    toggleSidebar() {
      this.isCollapsed = !this.isCollapsed;
      this.$emit('sidebar-toggled', this.isCollapsed);
      
      // Store preference in localStorage
      localStorage.setItem('pos_category_sidebar_collapsed', this.isCollapsed);
    },
    
    selectGroup(group) {
      this.$emit('group-selected', group.name);
      
      // Add to recent groups
      this.addToRecent(group.name);
    },
    
    addToRecent(groupName) {
      // Remove if already exists
      this.recentGroups = this.recentGroups.filter(name => name !== groupName);
      // Add to beginning
      this.recentGroups.unshift(groupName);
      // Keep only last 10
      this.recentGroups = this.recentGroups.slice(0, 10);
      
      // Store in localStorage
      localStorage.setItem('pos_recent_categories', JSON.stringify(this.recentGroups));
    },
    
    onSearchInput: debounce(function() {
      this.$emit('search-changed', this.searchTerm);
    }, 300),
    
    clearSearch() {
      this.searchTerm = '';
      this.$emit('search-changed', '');
    },
    
    setFilter(filter) {
      this.selectedFilter = filter;
      this.$emit('filter-changed', filter);
    },
    
    getGroupIcon(groupName) {
      const iconMap = {
        'Consumable': 'mdi-shopping',
        'Products': 'mdi-package-variant',
        'Raw Material': 'mdi-factory',
        'Services': 'mdi-handshake',
        'Sub Assemblies': 'mdi-cogs',
        'Food': 'mdi-food',
        'Beverages': 'mdi-coffee',
        'Electronics': 'mdi-laptop',
        'Clothing': 'mdi-tshirt-crew',
        'Books': 'mdi-book-open-page-variant',
        'Health': 'mdi-heart-pulse',
        'Beauty': 'mdi-face-woman-shimmer',
        'Sports': 'mdi-soccer',
        'Automotive': 'mdi-car',
        'Home': 'mdi-home',
        'All': 'mdi-view-grid',
        'ALL': 'mdi-view-grid',
        'Default': 'mdi-folder'
      };
      
      return iconMap[groupName] || iconMap['Default'];
    },
    
    getCategoryColor(groupName) {
      const colorMap = {
        'Consumable': '#4CAF50',
        'Products': '#2196F3',
        'Raw Material': '#9C27B0',
        'Services': '#FF9800',
        'Sub Assemblies': '#00BCD4',
        'Food': '#F44336',
        'Beverages': '#795548',
        'Electronics': '#3F51B5',
        'Clothing': '#E91E63',
        'Books': '#009688',
        'Health': '#FF5722',
        'Beauty': '#E91E63',
        'Sports': '#8BC34A',
        'Automotive': '#607D8B',
        'Home': '#00BCD4',
        'All': '#673AB7',
        'ALL': '#673AB7',
        'Default': '#9E9E9E'
      };
      
      return colorMap[groupName] || colorMap['Default'];
    },
    
    formatCurrency(amount) {
      return new Intl.NumberFormat('en-IN', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(amount);
    },
    
    // Load saved preferences
    loadPreferences() {
      // Load collapsed state
      const collapsed = localStorage.getItem('pos_category_sidebar_collapsed');
      if (collapsed !== null) {
        this.isCollapsed = collapsed === 'true';
      }
      
      // Load recent categories
      const recent = localStorage.getItem('pos_recent_categories');
      if (recent) {
        try {
          this.recentGroups = JSON.parse(recent);
        } catch (e) {
          this.recentGroups = [];
        }
      }
    }
  },
  
  mounted() {
    this.loadPreferences();
  },
  
  beforeUnmount() {
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }
  }
}
</script>

<style scoped>
.category-sidebar {
  width: 320px;
  background: var(--v-theme-surface);
  border-right: 1px solid var(--v-border-color);
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  box-shadow: 0 2px 8px rgba(var(--v-theme-on-surface), 0.12);
}

.category-sidebar.collapsed {
  width: 70px;
}

/* Header Styles */
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--v-border-color);
  background: var(--v-theme-surface-variant);
  min-height: 70px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  font-size: 24px;
  color: rgb(var(--v-theme-primary));
}

.sidebar-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
}

.collapse-btn {
  transition: all 0.3s ease;
}

.collapse-btn:hover {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  transform: scale(1.05);
}

/* Search Section */
.search-section {
  padding: 16px;
  border-bottom: 1px solid var(--v-border-color);
  background: var(--v-theme-surface);
}

.category-search {
  transition: all 0.3s ease;
}

/* Quick Filters */
.quick-filters {
  padding: 12px 16px;
  border-bottom: 1px solid var(--v-border-color);
  display: flex;
  justify-content: center;
  background: var(--v-theme-surface);
}

/* Category List */
.category-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(var(--v-theme-on-surface), 0.2) transparent;
}

.category-list::-webkit-scrollbar {
  width: 6px;
}

.category-list::-webkit-scrollbar-track {
  background: transparent;
}

.category-list::-webkit-scrollbar-thumb {
  background: rgba(var(--v-theme-on-surface), 0.2);
  border-radius: 3px;
}

.category-list::-webkit-scrollbar-thumb:hover {
  background: rgba(var(--v-theme-on-surface), 0.3);
}

.category-item {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border-left: 4px solid transparent;
  position: relative;
  margin: 2px 8px;
  border-radius: 8px;
}

.category-item:hover {
  background: rgba(var(--v-theme-primary), 0.08);
  border-left-color: rgb(var(--v-theme-primary));
  transform: translateX(2px);
}

.category-item.active {
  background: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
  border-left-color: rgb(var(--v-theme-primary));
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.15);
}

.category-item.no-stock {
  opacity: 0.6;
  cursor: not-allowed;
}

.category-item.no-stock:hover {
  transform: none;
  background: rgba(var(--v-theme-error), 0.08);
  border-left-color: rgb(var(--v-theme-error));
}

.category-icon {
  width: 45px;
  text-align: center;
  transition: all 0.3s ease;
}

.category-item.active .category-icon {
  transform: scale(1.1);
}

.category-details {
  flex: 1;
  margin-left: 12px;
  min-width: 0; /* Allow text truncation */
}

.category-name {
  display: block;
  font-weight: 600;
  font-size: 14px;
  line-height: 1.3;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.category-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.stock-value {
  font-size: 11px;
  background: rgba(var(--v-theme-surface-variant), 0.8);
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
}

.category-arrow {
  opacity: 0.6;
  font-size: 12px;
  transition: all 0.3s ease;
}

.category-item:hover .category-arrow {
  opacity: 1;
  transform: translateX(2px);
}

.item-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  font-size: 10px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 12px;
  min-width: 20px;
  text-align: center;
  box-shadow: 0 2px 4px rgba(var(--v-theme-primary), 0.3);
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.empty-icon {
  margin-bottom: 16px;
}

.empty-text {
  margin: 0;
  font-size: 14px;
}

/* Footer Stats */
.sidebar-footer {
  padding: 16px;
  background: var(--v-theme-surface-variant);
}

.stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.stat-label {
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-weight: 500;
}

/* Responsive Adjustments */
@media (max-width: 1200px) {
  .category-sidebar {
    width: 280px;
  }
  
  .category-sidebar.collapsed {
    width: 60px;
  }
}

/* Animation for smooth transitions */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.category-item {
  animation: slideIn 0.3s ease-out;
}

/* Dark theme adjustments */
.v-theme--dark .category-sidebar {
  background: rgb(var(--v-theme-surface));
  border-right-color: rgba(var(--v-theme-on-surface), 0.12);
}

.v-theme--dark .sidebar-header {
  background: rgb(var(--v-theme-surface-bright));
}

.v-theme--dark .search-section,
.v-theme--dark .quick-filters {
  background: rgb(var(--v-theme-surface));
}

.v-theme--dark .sidebar-footer {
  background: rgb(var(--v-theme-surface-bright));
}
</style>
