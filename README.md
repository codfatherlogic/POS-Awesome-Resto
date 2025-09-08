<div align="center">
    <img src="https://frappecloud.com/fil37. **Restaurant Order Consolidation**: Advanced multi-order payment workflow allowing cashiers to select multiple restaurant orders, automatically consolidate them into a single draft order, review and modify items in the POS cart, and complete payment while properly closing source orders and maintaining audit trails

### Recent Enhancements

#### Restaurant Order Consolidation (v15.2024)
- **Multi-Order Selection**: Select multiple draft restaurant orders from the Restaurant Orders dialog
- **Automatic Consolidation**: System creates a consolidated draft Sales Order containing all items from selected orders
- **POS Cart Integration**: Consolidated order automatically loads into POS cart for review and modification
- **Item Review & Modification**: Cashiers can add, remove, or modify items before final payment
- **Smart Payment Processing**: Submit consolidated order converts to Sales Invoice, closes source orders, and updates custom reference fields
- **Table Management**: Automatic release of restaurant tables upon order consolidation
- **Audit Trail**: Maintains complete traceability with consolidated invoice references and VAT mappings

#### Enhanced POS Workflow (v15.2024)png" height="128">
    <h2>POS AWESOME</h2>
</div>

#### An open-source Point of Sale for [Erpnext](https://github.com/frappe/erpnext) using [Vue.js](https://github.com/vuejs/vue) and [Vuetify](https://github.com/vuetifyjs/vuetify) (VERSION 15 Support)

---

### Update Instructions

After switching branches or pulling latest changes:

1. cd apps/posawesome
2. git pull
3. yarn install
4. cd ../..
5. bench build --app posawesome
6. bench --site your.site migrate
    - If the build exits with code 143, verify that your system has enough RAM or swap space.
    - You can also try building the app in smaller parts to reduce memory usage.

### Main Features

1. Supports Erpnext Version 15
2. Supports Multi-Currency Transactions.
   Customers can be invoiced in different currencies.
   Exchange Rate is fetched automatically based on selected currency. When a price list has its own exchange rate set, POS Awesome uses that rate and falls back to the standard ERPNext rate otherwise.
   Invoices made with posawesome display Grand Total in both base and selected currency in erpnext.
3. Supports offline mode for creating invoices and customers, saves data locally with stock validation, and syncs automatically when reconnected. If **Allow Negative Stock** is enabled in Stock Settings, offline invoices can still be saved even when quantities are below zero. **Enable browser local storage from settings and also enable the server cache for offline mode.**
4. User-friendly and provides a good user experience and speed of use
5. The cashier can either use list view or card view during sales transactions. Card view shows the images of the items
6. Supports enqueue invoice submission after printing the receipt for faster processing
7. Supports batch & serial numbering
8. Supports batch-based pricing
9. Supports UOM-specific barcode and pricing
10. Supports sales of scale (weighted) products
11. Ability to make returns from POS
12. Supports Making returns for either cash or customer credit
13. Supports using customer credit notes for payment
14. Supports credit sales
15. Allows the user to choose a due date for credit sales
16. Supports customer loyalty points
17. Shortcut keys
18. Supports Customer Discount
19. Supports POS Offers
20. Auto-apply batches for bundle items
21. Search and add items by Serial Number
22. Create Sales Orders from POS directly
23. Supports template items with variants
24. Supports multiple languages with language selection per POS Profile (English, Arabic, Portuguese and Spanish provided)
25. Supports Mpesa mobile payment
26. POS Coupons
27. Supports Referral Code
28. Supports Customer and Customer Group price list
29. Supports Sales Person
30. Supports Delivery Charges
31. Search and add items by Batch Number
32. Accept new payments from customers against existing invoices
33. Payments Reconciliation
34. A lot more bug fixes from the version 14
35. Offline invoices that fail to submit are saved as draft documents
36. **Enhanced Sales Order to Sales Invoice workflow** with automatic document submission and comprehensive item synchronization
37. **Smart document concurrency management** to prevent timestamp conflicts during order processing
38. **Restaurant-ready dynamic item synchronization** allowing customers to modify orders after initial payment conversion

### Recent Enhancements

#### Enhanced POS Workflow (v15.2024)
- **Automatic Sales Order Submission**: System automatically submits Draft Sales Orders before creating Sales Invoices, eliminating workflow errors
- **Intelligent Document Resolution**: Backend automatically converts Sales Order names to Sales Invoice names when needed
- **Dynamic Item Synchronization**: Real-time synchronization of items between Sales Orders and Sales Invoices, perfect for restaurant scenarios where customers modify orders after initial conversion
- **Document Concurrency Management**: Advanced handling of document modification conflicts with automatic reloading and validation
- **Robust Payment Processing**: Enhanced payment workflow with document locking and comprehensive error handling

These improvements ensure seamless order-to-payment workflows in high-volume restaurant environments where orders frequently change after initial processing.

### Quick Start

Follow these steps to install and start using POS Awesome:

1. **Install the app** in your bench:
    1. `bench get-app --branch Version-15 https://github.com/defendicon/POS-Awesome-V15`
    2. `bench setup requirements`
    3. `bench build --app posawesome`
    4. `bench restart`
    5. `bench --site your.site.name install-app posawesome`
    6. `bench --site your.site.name migrate`

2. **Open the POS Awesome workspace**

    Log in to ERPNext, go to the home page, and click **POS Awesome** from the left-hand menu.

3. **Create a POS Profile**
    - Navigate to **POS Awesome → POS Profile → New**.
    - Fill in the mandatory fields:
        - **Name** – any label for this profile.
        - **Company** – the company under which transactions will be recorded.
        - **Warehouse** – the default warehouse for item stock deduction.
        - **Customer** – a default customer (create one if none exists).
        - **Applicable for Users** – add the users allowed to use this POS.
        - **Payment Methods** – add accepted modes (e.g., Cash, Card).

4. **Save the profile**

5. **Start selling**

    Return to the **POS Awesome** workspace and launch the POS. Select the newly created profile if prompted and begin creating invoices.

For more details, see the [POS Awesome Wiki](https://github.com/yrestom/POS-Awesome/wiki).

---

### Shortcuts:

- `CTRL or CMD + S` open payments
- `CTRL or CMD + X` submit payments
- `CTRL or CMD + D` remove the first item from the top
- `CTRL or CMD + A` expand the first item from the top
- `CTRL or CMD + E` focus on discount field

---

### Dependencies:

- [Frappe](https://github.com/frappe/frappe)
- [Erpnext](https://github.com/frappe/erpnext)
- [Vue.js](https://github.com/vuejs/vue)
- [Vuetify.js](https://github.com/vuetifyjs/vuetify)

---

### Contributing

1. [Issue Guidelines](https://github.com/frappe/erpnext/wiki/Issue-Guidelines)
2. [Pull Request Requirements](https://github.com/frappe/erpnext/wiki/Contribution-Guidelines)

---

### License

GNU/General Public License (see [license.txt](https://github.com/yrestom/POS-Awesome/blob/master/license.txt))

The POS Awesome code is licensed as GNU General Public License (v3)
