import numpy as np


def minmax(x) -> np.ndarray:
    """Scale to 0..1 within the candidate pool. A constant array gives a neutral 0.5."""
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-12:
        return np.full_like(x, 0.5)
    return (x - lo) / (hi - lo)