import pandas as pd


def weighted_rating(df: pd.DataFrame, quantile: float = 0.7) -> pd.Series:
    """WR = v/(v+m)*R + m/(v+m)*C, computed separately per rating source
    (IMDb and TMDB vote counts are on different scales).
    Movies with no rating get 0 and so rank lowest on popularity."""
    out = pd.Series(0.0, index=df.index)
    for _, g in df.groupby("rating_source"):
        rated = g[g["votes"] > 0]
        if rated.empty:
            continue
        C = rated["rating"].mean()
        m = rated["votes"].quantile(quantile)
        v = g["votes"].fillna(0)
        R = g["rating"].fillna(C)
        out.loc[g.index] = (v / (v + m)) * R + (m / (v + m)) * C
    return out