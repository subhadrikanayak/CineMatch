import pandas as pd

from ml.popularity import weighted_rating


def find_gems(df: pd.DataFrame, popularity: dict, candidate_ids=None,
              min_votes: int = 50, vote_quantile: float = 0.7,
              pop_quantile: float = 0.6, wr_quantile: float = 0.6, limit: int = 20):
    """A hidden gem needs ALL of:
       - weighted rating in the top (1 - wr_quantile) of the catalogue
       - at least `min_votes` votes (a few votes never counts as excellent)
       - votes at or below the vote_quantile (not already a mass-market hit)
       - popularity at or below the pop_quantile of the catalogue
    Thresholds are computed from your catalogue and returned with the results."""
    d = df[["id", "title", "rating", "votes", "rating_source"]].copy()
    d["wr"] = weighted_rating(df).to_numpy()
    d["pop"] = pd.to_numeric(d["id"].map(popularity), errors="coerce")
    rated = d[(d["votes"] > 0) & d["pop"].notna()]
    if len(rated) < 20:
        return [], {}
    th = {
        "min_votes": min_votes,
        "max_votes": float(rated["votes"].quantile(vote_quantile)),
        "max_popularity": float(rated["pop"].quantile(pop_quantile)),
        "min_weighted_rating": float(rated["wr"].quantile(wr_quantile)),
    }
    d["pop_pct"] = d["pop"].rank(pct=True)
    mask = ((d["votes"] >= th["min_votes"]) & (d["votes"] <= th["max_votes"])
            & (d["pop"] <= th["max_popularity"]) & (d["wr"] >= th["min_weighted_rating"]))
    if candidate_ids is not None:
        mask &= d["id"].isin(set(candidate_ids))
    g = d[mask].copy()
    g["gem_score"] = g["wr"] * (1 - g["pop_pct"])
    g = g.sort_values("gem_score", ascending=False).head(limit)
    return g.to_dict("records"), th