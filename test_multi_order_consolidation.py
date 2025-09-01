#!/usr/bin/env python3
"""
Test script to validate multi-order consolidation fixes
"""

import json
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8002"
SESSION = requests.Session()

def login():
    """Login to get session"""
    print("🔐 Logging in...")
    response = SESSION.post(f"{BASE_URL}/login", data={
        "cmd": "login",
        "usr": "administrator",
        "pwd": "admin"
    })
    if response.status_code != 200:
        print(f"❌ Login failed with status {response.status_code}")
        return False
    print("✅ Login successful")
    return True

def test_load_multiple_orders():
    """Test load_multiple_draft_orders_for_editing API"""
    print("\n🧪 Testing load_multiple_draft_orders_for_editing...")
    
    # Mock order names - replace with actual order names from your system
    test_data = {
        "sales_order_names": ["SO-2024-00001", "SO-2024-00002"]  # Replace with actual order names
    }
    
    response = SESSION.post(f"{BASE_URL}/api/method/posawesome.posawesome.api.restaurant_orders.load_multiple_draft_orders_for_editing", 
                          json=test_data,
                          headers={"Content-Type": "application/json"})
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if 'message' in data:
                consolidated_data = data['message']
                print(f"✅ API successful")
                print(f"📊 Data keys: {list(consolidated_data.keys())}")
                
                # Check for critical fields
                if 'source_orders' in consolidated_data:
                    print(f"✅ source_orders field present: {consolidated_data['source_orders']}")
                else:
                    print("❌ source_orders field missing")
                
                if 'multi_order_names' in consolidated_data:
                    print(f"✅ multi_order_names field present: {consolidated_data['multi_order_names']}")
                else:
                    print("❌ multi_order_names field missing")
                
                if 'is_multi_order_consolidation' in consolidated_data:
                    print(f"✅ is_multi_order_consolidation field present: {consolidated_data['is_multi_order_consolidation']}")
                else:
                    print("❌ is_multi_order_consolidation field missing")
                
                return consolidated_data
            else:
                print(f"❌ No message in response: {data}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"Raw response: {response.text[:500]}")
    else:
        print(f"❌ API failed with status {response.status_code}")
        print(f"Response: {response.text[:500]}")
    
    return None

def test_submit_invoice_with_consolidation(consolidated_data):
    """Test submit_invoice with multi-order consolidation data"""
    if not consolidated_data:
        print("⚠️  No consolidated data to test submit_invoice")
        return
    
    print("\n🧪 Testing submit_invoice with consolidation...")
    
    # Simulate the invoice data that would be sent from frontend
    invoice_data = {
        **consolidated_data,
        "payments": [
            {
                "mode_of_payment": "Cash",
                "amount": consolidated_data.get("grand_total", 100)
            }
        ]
    }
    
    # Log what we're sending
    print(f"📤 Sending invoice data with keys: {list(invoice_data.keys())}")
    if 'source_orders' in invoice_data:
        print(f"✅ source_orders in payload: {invoice_data['source_orders']}")
    if 'multi_order_names' in invoice_data:
        print(f"✅ multi_order_names in payload: {invoice_data['multi_order_names']}")
    if 'is_multi_order_consolidation' in invoice_data:
        print(f"✅ is_multi_order_consolidation in payload: {invoice_data['is_multi_order_consolidation']}")
    
    response = SESSION.post(f"{BASE_URL}/api/method/posawesome.posawesome.api.invoices.submit_invoice",
                          json=invoice_data,
                          headers={"Content-Type": "application/json"})
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"✅ submit_invoice successful")
            return data
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"Raw response: {response.text[:500]}")
    else:
        print(f"❌ submit_invoice failed with status {response.status_code}")
        print(f"Response: {response.text[:500]}")
    
    return None

def test_debug_finalize_payment():
    """Test the finalize_multi_order_payment function directly with debug data"""
    print("\n🧪 Testing finalize_multi_order_payment debug...")
    
    # Create minimal test data to trigger the function
    test_data = {
        "name": "test-invoice-001",
        "doctype": "Sales Invoice", 
        "customer": "Test Customer",
        "grand_total": 100,
        "is_multi_order_consolidation": True,
        "source_orders": ["SO-2024-00001", "SO-2024-00002"],
        "multi_order_names": ["SO-2024-00001", "SO-2024-00002"],
        "payments": [{"mode_of_payment": "Cash", "amount": 100}]
    }
    
    response = SESSION.post(f"{BASE_URL}/api/method/posawesome.posawesome.api.restaurant_orders.debug_finalize_payment", 
                          json=test_data,
                          headers={"Content-Type": "application/json"})
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:1000]}")

def main():
    """Main test function"""
    print("🚀 Starting Multi-Order Consolidation Test")
    print("=" * 50)
    
    if not login():
        return
    
    # Test 1: Load multiple orders
    consolidated_data = test_load_multiple_orders()
    
    # Test 2: Submit invoice with consolidation (if we got data)
    if consolidated_data:
        test_submit_invoice_with_consolidation(consolidated_data)
    
    # Test 3: Debug finalize payment function
    test_debug_finalize_payment()
    
    print("\n🏁 Test completed")
    print("Check the server logs for detailed debugging output from frappe.logger()")

if __name__ == "__main__":
    main()
