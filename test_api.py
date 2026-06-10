import os
from dotenv import load_dotenv
from bot.client import BinanceFuturesClient

# Load environment variables
load_dotenv()

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

print("=== API Configuration Test ===")
print(f"API Key: {api_key[:20]}...{api_key[-10:] if api_key else 'NOT SET'}")
print(f"API Secret: {api_secret[:20]}...{api_secret[-10:] if api_secret else 'NOT SET'}")
print()

if not api_key or not api_secret:
    print("ERROR: API credentials not found in .env file")
    exit(1)

# Test the client
client = BinanceFuturesClient(api_key, api_secret)

# Test 1: Can we read price? (no auth needed)
print("Test 1: Reading BTC price (public endpoint)...")
try:
    price_data = client.get_price("BTCUSDT")
    print(f"✅ SUCCESS - Price: {price_data.get('price')}")
except Exception as e:
    print(f"❌ FAILED - {e}")

print()

# Test 2: Can we read account info? (requires auth + read permission)
print("Test 2: Reading account info (requires auth + read permission)...")
try:
    account_data = client.get_account()
    print(f"✅ SUCCESS - Account assets: {len(account_data.get('assets', []))} assets")
except Exception as e:
    print(f"❌ FAILED - {e}")

print()

# Test 3: Can we place a test order? (requires auth + trading permission)
print("Test 3: Attempting to place order (requires auth + trading permission)...")
try:
    order_data = client.place_order(
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        quantity="0.001"
    )
    print(f"✅ SUCCESS - Order ID: {order_data.get('orderId')}")
except Exception as e:
    print(f"❌ FAILED - {e}")
    print()
    print("This means your API key does NOT have trading permissions enabled.")
    print("You need to:")
    print("1. Go to https://testnet.binancefuture.com")
    print("2. Delete the current API key")
    print("3. Create a NEW API key with 'Enable Spot & Margin & Stock Trading' checked")
    print("4. Update your .env file with the NEW credentials")
