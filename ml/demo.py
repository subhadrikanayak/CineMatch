"""Try the engine. Signals are built in memory only; nothing is written to the database.
Run from D:\\CineMatch:  python -m ml.demo"""
import logging

from ml.hybrid import HybridRecommender, UserSignals

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
rec = HybridRecommender.load()
print(f"Loaded {len(rec.ids)} movies. Collaborative model ready: {rec.collab.ready}")


def show(title, signals, **kw):
    print(f"\n=== {title} ===")
    results = rec.recommend(signals, k=8, **kw)
    if results:
        print("weights used:", results[0].weights)
    for r in results:
        row = rec.records[rec.pos[r.movie_id]]
        print(f"{r.match_percent:>3}%  {row['title']} ({row['language']}, {row['release_year']})")
        for reason in r.reasons:
            print("       -", reason)


show("Cold start: new user who picked Malayalam + Thriller",
     UserSignals(fav_languages={"ml"}, fav_genres={"Thriller"}))

seed = rec.ids[int(rec.wr.argmax())]
seed_row = rec.records[rec.pos[seed]]
show(f"In-memory test: user who rated '{seed_row['title']}' 5/5",
     UserSignals(ratings={seed: 5.0}))

print(f"\n=== Movies similar to '{seed_row['title']}' (TF-IDF cosine) ===")
for mid, sim in rec.content.similar(seed, 5):
    print(f"{sim:.3f}  {rec.records[rec.pos[mid]]['title']}")