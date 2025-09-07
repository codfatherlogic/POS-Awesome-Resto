# Customer Dialog - Default "Hide Non Essential Fields" Enhancement

## Change Summary
Updated the "Create Customer" dialog to enable "Hide Non Essential Fields" by default for a cleaner, more streamlined user experience.

## What Changed

### Before
- Customer dialog opened with all fields visible (including optional fields like Address, City, Country, Customer Group, Territory)
- Users had to manually toggle "Hide Non Essential Fields" if they wanted a simpler view
- Non-essential fields cluttered the interface for quick customer creation

### After  
- Customer dialog opens with "Hide Non Essential Fields" enabled by default
- Only essential fields are shown: Customer Name, Tax ID, Mobile No, Email ID, Gender, Referral Code, Birthday
- Users can still toggle to show all fields if needed
- Preference is saved in localStorage for subsequent uses

## Technical Implementation

### File Modified
`/frontend/src/posapp/components/pos/UpdateCustomer.vue`

### Changes Made

1. **Default Value Update**
```javascript
// Before
hideNonEssential: false,

// After  
hideNonEssential: true, // Default to hiding non-essential fields
```

2. **Enhanced Initialization Logic**
```javascript
// Before
if (saved !== null) {
    this.hideNonEssential = JSON.parse(saved);
}

// After
if (saved !== null) {
    this.hideNonEssential = JSON.parse(saved);
} else {
    // First time use - set default to true and save it
    this.hideNonEssential = true;
    localStorage.setItem("posawesome_hide_non_essential_fields", JSON.stringify(true));
}
```

## Field Visibility

### Essential Fields (Always Visible)
- ✅ Customer Name (required)
- ✅ Tax ID  
- ✅ Mobile No
- ✅ Email ID
- ✅ Gender
- ✅ Referral Code
- ✅ Birthday

### Non-Essential Fields (Hidden by Default)
- ❌ Address Line 1
- ❌ City
- ❌ Country
- ❌ Customer Group (required but hidden by default)
- ❌ Territory (required but hidden by default)

## User Experience Benefits

1. **Faster Customer Creation**: Less visual clutter allows for quicker data entry
2. **Better Mobile Experience**: Fewer fields fit better on smaller screens  
3. **Streamlined Workflow**: Focus on most commonly used fields
4. **Flexible**: Users can still access all fields by toggling the switch
5. **Persistent Preference**: Setting is remembered across sessions

## Backwards Compatibility

- ✅ Existing users who have saved preference (localStorage) will maintain their choice
- ✅ New users or cleared localStorage will get the improved default (hide non-essential)
- ✅ Toggle functionality remains exactly the same
- ✅ All fields are still accessible when needed

## Usage Impact

### For Quick Customer Creation (Most Common)
1. Click "Create Customer" 
2. Fill Customer Name (required)
3. Optionally add Tax ID, Mobile, Email
4. Submit ✅

### For Detailed Customer Creation
1. Click "Create Customer"
2. Toggle "Hide Non Essential Fields" OFF
3. Fill all required and optional fields  
4. Submit ✅

This change makes the customer creation process more efficient while maintaining full functionality for users who need all fields.
