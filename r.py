def assign_bucket(value, bins):
    """
    Assigns a value to a bucket given a list of sorted bin edges.
    Example bins: [0, 30, 60, 100]
    """
    for i in range(len(bins) - 1):
        lower = bins[i]
        upper = bins[i + 1]

        # Check if value falls within the current bucket
        if lower <= value <= upper:
            return f"{lower}–{upper}"

    return f"{bins[-1]}+"


# Define your bucket edges
bin_edges = [0, 30, 60, 100]

# Test cases
print(assign_bucket(25, bin_edges))  # Output: 0–30
print(assign_bucket(45, bin_edges))  # Output: 30–60
print(assign_bucket(90, bin_edges))  # Output: 60–100
print(assign_bucket(120, bin_edges))  # Output: 100+
