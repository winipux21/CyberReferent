# recommendation_engine.py

# import faiss
# import numpy as np
# from sentence_transformers import SentenceTransformer

class ReferenceRecommender:
    def __init__(self, vak_df):
        # Сохраняем DataFrame в поле, если вдруг нужно
        self.vak_df = vak_df
        # Комментируем всё, что касается модели, эмбеддингов и faiss
        # self.model = SentenceTransformer('distiluse-base-multilingual-cased-v2')
        # self.embeddings = self.model.encode(vak_df['journal'].tolist())
        # self.index = faiss.IndexFlatL2(self.embeddings.shape[1])
        # self.index.add(self.embeddings)
        pass

    def recommend_similar(self, ref, k=3):
        """
        Возвращает всегда одну и ту же рекомендацию, например:
        [("Вопросы права, экономики и", "2949-5172"), ...]
        """
        # Игнорируем ref и k, всегда отдаём ту же пару
        # Если k=3, отдадим 3 одинаковых записи (или меньше, как нужно)
        recommendations = []
        for _ in range(k):
            recommendations.append(("Вопросы права, экономики и", "2949-5172"))
        return recommendations
