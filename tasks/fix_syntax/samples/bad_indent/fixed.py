def shipping_cost(weight_kg):
    if weight_kg <= 1:
        return 5
    elif weight_kg <= 5:
        return 9
    return 15


for weight in [0.5, 3, 12]:
    print(f"{weight} kg: ${shipping_cost(weight)}")
