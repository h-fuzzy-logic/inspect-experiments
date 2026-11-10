def letter(score):
    if score >= 90:
        return "A"
    else if score >= 80:
        return "B"
    else:
        return "C"


for score in [95, 85, 70]:
    print(f"{score}: {letter(score)}")
