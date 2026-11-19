"""python -m ml.build_embeddings   (needs: python -m pip install sentence-transformers)"""
import json

import numpy as np
from sentence_transformers import SentenceTransformer

from ml.data import load_movies_df
from ml.semantic import EMB_FILE, IDS_FILE, MODEL_NAME, SemanticIndex

df = load_movies_df()
texts = SemanticIndex(df).texts
model = SentenceTransformer(MODEL_NAME)
emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=True, batch_size=32)
EMB_FILE.parent.mkdir(parents=True, exist_ok=True)
np.save(EMB_FILE, emb)
IDS_FILE.write_text(json.dumps(df["id"].tolist()))
print(f"Saved embeddings for {len(texts)} movies. Restart the API to use them.")