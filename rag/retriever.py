from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rag.knowledge_base import KNOWLEDGE_BASE_ENTRIES

class RAGRetriever:
    def __init__(self, entries=KNOWLEDGE_BASE_ENTRIES):
        self.entries = entries
        self.corpus = [f"{e['crop']} {e['disease']} {e['title']} {e['text']}" for e in self.entries]
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

    def retrieve(self, query, top_k=5):
        """
        Retrieves top_k relevant documents for a given query string using TF-IDF cosine similarity.
        Returns list of matching document dicts with relevance scores.
        """
        if not query or len(query.strip()) == 0:
            return []

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        ranked_indices = scores.argsort()[::-1][:top_k]

        results = []
        for idx in ranked_indices:
            score = float(scores[idx])
            # Only include documents with non-zero relevance score or top 3 matches
            if score > 0.01 or len(results) < 3:
                doc = dict(self.entries[idx])
                doc["relevance_score"] = round(score, 4)
                results.append(doc)
        return results

_RETRIEVER_INSTANCE = None

def get_rag_retriever():
    global _RETRIEVER_INSTANCE
    if _RETRIEVER_INSTANCE is None:
        _RETRIEVER_INSTANCE = RAGRetriever()
    return _RETRIEVER_INSTANCE

def retrieve_rag(query, top_k=5):
    """
    Public entrypoint function required by specification:
    retrieve_rag(query, top_k=5)
    Returns: document, source, relevance score items.
    """
    retriever = get_rag_retriever()
    return retriever.retrieve(query, top_k=top_k)
