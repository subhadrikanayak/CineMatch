"""Fit the models offline and save them to ml/artifacts/.
Run from D:\\CineMatch:  python -m ml.train"""
import json
import logging
from datetime import datetime
from pathlib import Path

from ml.collaborative import CollaborativeModel
from ml.content_based import ContentModel
from ml.data import load_movies_df, load_ratings_df

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

df = load_movies_df()
if df.empty:
    raise SystemExit("No movies found. Run the TMDB ingestion first.")

content = ContentModel.fit(df)
content.save()
print(f"Content model: {content.matrix.shape[0]} movies x {content.matrix.shape[1]} TF-IDF features")

ratings = load_ratings_df()
collab = CollaborativeModel.fit(ratings, df["id"].tolist())
collab.save()
print(f"Collaborative model ready: {collab.ready} ({len(ratings)} real user ratings in DB)")

manifest = {"trained_at": datetime.utcnow().isoformat(), "movies": len(df),
            "ratings": len(ratings), "collab_ready": collab.ready}
(Path(__file__).parent / "artifacts" / "manifest.json").write_text(json.dumps(manifest, indent=2))
print("Saved to ml/artifacts/")