prices = {
    "coffee": 3.50,
    "tea": 2.75
    "cake": 4.25,
}

order = ["coffee", "cake", "cake"]
total = sum(prices[item] for item in order)
print(f"items: {len(order)}")
print(f"total: ${total:.2f}")
