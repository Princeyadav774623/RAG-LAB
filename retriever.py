import os
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from pinecone import Pinecone
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class HybridRetriever:
    def __init__(
        self, 
        index_name: str = "rag-documents",
        embedding_model_name: str = "BAAI/bge-base-en-v1.5",
        reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):
        self.index_name = index_name
        
        # Initialize Pinecone
        pinecone_key = os.environ.get("PINECONE_API_KEY")
        if pinecone_key:
            self.pc = Pinecone(api_key=pinecone_key)
            self.index = self.pc.Index(self.index_name)
        else:
            self.pc = None
            self.index = None
            
        # Initialize Supabase
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if supabase_url and supabase_key:
            self.supabase: Client = create_client(supabase_url, supabase_key)
        else:
            self.supabase = None
            
        # Load local dense embedding model (matches ingestion)
        self.embedding_model = SentenceTransformer(embedding_model_name)
        
        # Load local Cross-Encoder reranker model
        self.reranker_model = CrossEncoder(reranker_model_name)

    def retrieve(
        self, 
        query: str, 
        top_k: int = 5, 
        rrf_constant: int = 60,
        enable_rerank: bool = True
    ) -> List[Dict[str, Any]]:
        if not self.index or not self.supabase:
            return []
            
        # 1. Dense Semantic Search (Pinecone)
        query_embedding = self.embedding_model.encode(query).tolist()
        
        dense_results = self.index.query(
            vector=query_embedding,
            top_k=20,
            include_metadata=True
        )
        
        dense_ranking = []
        for match in dense_results.get("matches", []):
            dense_ranking.append({
                "id": match["id"],
                "metadata": match.get("metadata", {}),
                "dense_score": match["score"]
            })
            
        # 2. Sparse Keyword Search (Supabase Full-text)
        # We use Supabase's textSearch on the 'content' column (using english dictionary)
        sparse_ranking = []
        try:
            # text_search maps to Postgres plainto_tsquery or to_tsquery
            # WebSearch provides better handling of generic queries in Supabase
            response = self.supabase.table("documents").select("*").text_search("content", query, config="english").limit(20).execute()
            for rank, row in enumerate(response.data):
                sparse_ranking.append({
                    "id": row["id"],
                    "text": row["content"],
                    "metadata": {
                        "source": row["source"],
                        "page": row["page"],
                        "chunk_index": row["chunk_index"]
                    },
                    "sparse_score": 1.0 / (rank + 1) # simple fallback rank score for sparse
                })
        except Exception as e:
            print(f"Error during Supabase sparse search: {e}")
            
        # Helper to fetch missing texts from Supabase for dense-only results
        def fetch_texts_for_ids(ids: List[str]) -> Dict[str, str]:
            if not ids: return {}
            try:
                res = self.supabase.table("documents").select("id, content").in_("id", ids).execute()
                return {row["id"]: row["content"] for row in res.data}
            except:
                return {}
                
        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores = {}
        candidates = {}
        
        for rank, item in enumerate(dense_ranking):
            doc_id = item["id"]
            candidates[doc_id] = item
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (rrf_constant + (rank + 1)))
            
        for rank, item in enumerate(sparse_ranking):
            doc_id = item["id"]
            if doc_id not in candidates:
                candidates[doc_id] = item
                candidates[doc_id]["dense_score"] = 0.0
            candidates[doc_id]["sparse_score"] = item["sparse_score"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (rrf_constant + (rank + 1)))
            
        for doc_id, cand in candidates.items():
            if "sparse_score" not in cand:
                cand["sparse_score"] = 0.0
                
        # Sort candidates by combined RRF score
        sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        rerank_candidates_count = min(15, len(sorted_rrf))
        merged_candidates = [candidates[doc_id] for doc_id, _ in sorted_rrf[:rerank_candidates_count]]
        
        # We need to ensure we have the 'text' field for reranking
        missing_text_ids = [c["id"] for c in merged_candidates if "text" not in c]
        fetched_texts = fetch_texts_for_ids(missing_text_ids)
        
        for cand in merged_candidates:
            if "text" not in cand:
                cand["text"] = fetched_texts.get(cand["id"], "")
                
        # Remove any that failed to fetch text
        merged_candidates = [c for c in merged_candidates if c["text"]]
        
        for idx, cand in enumerate(merged_candidates):
            cand["rrf_rank"] = idx + 1
            cand["rrf_score"] = float(rrf_scores[cand["id"]])
            
        if not merged_candidates:
            return []
            
        # 4. Cross-Encoder Reranking
        if enable_rerank:
            pairs = [[query, cand["text"]] for cand in merged_candidates]
            rerank_scores = self.reranker_model.predict(pairs)
            
            for idx, score in enumerate(rerank_scores):
                merged_candidates[idx]["rerank_score"] = float(score)
                
            final_ranking = sorted(merged_candidates, key=lambda x: x["rerank_score"], reverse=True)
        else:
            for cand in merged_candidates:
                cand["rerank_score"] = cand["rrf_score"]
            final_ranking = merged_candidates
            
        return final_ranking[:top_k]

if __name__ == "__main__":
    print("Initializing HybridRetriever test...")
    retriever = HybridRetriever()
    print("Retriever model loaders complete.")
