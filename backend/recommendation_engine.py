import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class ReferenceRecommender:
    def __init__(self, vak_df):
        self.vak_df = vak_df
        self.model = SentenceTransformer('distiluse-base-multilingual-cased-v2')
        self.embeddings = self.model.encode(vak_df['journal'].tolist())
        self.index = faiss.IndexFlatL2(self.embeddings.shape[1])
        self.index.add(self.embeddings)

    def recommend_similar(self, ref, k=3):
        ref_emb = self.model.encode([ref])
        _, idx = self.index.search(np.array(ref_emb), k)
        return self.vak_df.iloc[idx[0]][['journal', 'ISSN']].values.tolist()


