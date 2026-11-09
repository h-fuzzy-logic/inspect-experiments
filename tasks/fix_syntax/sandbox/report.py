scores = {"alice": 91, "bob": 78, "carol": 85}


def average(values):
    return sum(values) / len(values)


for name, score in sorted(scores.items()):
    print(f"{name}: {score}")

avg = average(list(scores.values()))
print(f"average: {avg:.1f}")

if avg > 80
    print("Class average is above 80")
else:
    print("Class average is 80 or below")
