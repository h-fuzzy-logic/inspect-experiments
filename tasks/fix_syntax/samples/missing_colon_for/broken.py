stock = {"apples": 12, "pears": 0, "plums": 7}

total = 0
for item, count in stock.items()
    total += count
    if count == 0:
        print(f"{item}: out of stock")

print(f"total items: {total}")
if total < 10:
    print("Reorder soon")
else:
    print("Stock is fine")
