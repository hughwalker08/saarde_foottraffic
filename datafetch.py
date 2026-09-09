import requests
import os
from dotenv import load_dotenv

load_dotenv()

SHOP  = "saarde.myshopify.com"
TOKEN = os.environ["SHOPIFY_TOKEN"]

headers = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

BASE = f"https://{SHOP}/admin/api/2024-01"

def get_orders(status="any", limit=250):
    url = f"{BASE}/orders.json"
    params = {
        "status": status,   # "any", "open", "closed", "cancelled"
        "limit": limit,     # max 250 per page
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()["orders"]

orders = get_orders()
print(f"Fetched {len(orders)} orders")

from collections import defaultdict

daily_revenue = defaultdict(float)

for order in orders:
    date = order["created_at"][:10]  # "YYYY-MM-DD"
    daily_revenue[date] += float(order["total_price"])

for date, revenue in sorted(daily_revenue.items()):
    print(f"{date}: ${revenue:.2f}")