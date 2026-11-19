import numpy as np


def mmr(relevance: np.ndarray, sim: np.ndarray, k: int, lam: float = 0.7) -> list[int]:
    """Maximal Marginal Relevance. Returns indices into `relevance`, in selection order.
    lam=1 -> pure relevance, lam=0 -> maximum diversity."""
    n = len(relevance)
    k = min(k, n)
    selected: list[int] = []
    remaining = list(range(n))
    while remaining and len(selected) < k:
        if not selected:
            best = max(remaining, key=lambda i: relevance[i])
        else:
            best = max(remaining,
                       key=lambda i: lam * relevance[i] - (1 - lam) * sim[i, selected].max())
        selected.append(best)
        remaining.remove(best)
    return selected