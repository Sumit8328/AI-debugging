def slice_batch(items, batch_size):
    """
    Slices an iterable of items into chunks of size batch_size.
    BUG: Loops up to len(items) + 1 which causes out of bounds / empty overflow on exact multiples,
    and fails to guard against non-positive batch_size.
    """
    batches = []
    # BUG: + 1 causes index boundary spillover
    for i in range(0, len(items) + 1, batch_size):
        batches.append(items[i:i + batch_size])
    return batches
