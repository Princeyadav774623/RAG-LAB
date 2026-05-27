import os
import shutil
import time

# Core module imports
from ingestion import DocumentIngester
from retriever import HybridRetriever
from llm_manager import LLMManager
from evaluator import RAGEvaluator

def main():
    print("[*] Starting RAG End-to-End Pipeline Integration Verification...")
    
    # 1. Initialize DB Clean
    db_path = "./temp_test_chroma_db"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
        
    print("[*] Initializing components...")
    ingester = DocumentIngester(db_path=db_path)
    retriever = HybridRetriever(db_path=db_path)
    llm = LLMManager()
    evaluator = RAGEvaluator(llm_manager=llm)
    
    # 2. Create sample document
    sample_file_path = "./sample_antigravity_doc.txt"
    sample_text = (
        "Antigravity is an advanced agentic AI coding assistant designed by the Google DeepMind team.\n"
        "It was created to pair program with software developers and solve complex software engineering challenges.\n"
        "In 2026, Antigravity achieved the highest score on coding benchmarks due to its planning-mode architecture.\n"
        "It uses recursive character-level token division to break down prompts."
    )
    
    with open(sample_file_path, "w", encoding="utf-8") as f:
        f.write(sample_text)
        
    print(f"[+] Created sample testing file: {sample_file_path}")
    
    try:
        # 3. Ingestion & Indexing
        print("[*] Loading and parsing document...")
        docs = ingester.load_txt(sample_file_path)
        assert len(docs) == 1, "Failed to load document!"
        
        print("[*] Chunking document...")
        chunks = ingester.split_text(docs, chunk_size=100, chunk_overlap=10)
        print(f"[+] Created {len(chunks)} chunks.")
        assert len(chunks) > 0, "No chunks created!"
        
        print("[*] Indexing chunks into local ChromaDB with embeddings...")
        indexed = ingester.add_documents(chunks)
        print(f"[+] Successfully indexed {indexed} chunks.")
        assert indexed == len(chunks), "Chunk indexing count mismatch!"
        
        # Force reload retriever collection
        retriever.collection = retriever.client.get_or_create_collection(name=retriever.collection_name)
        
        # 4. Retrieval Verification
        query = "Who designed Antigravity?"
        print(f"[*] Querying Hybrid Search Retriever: '{query}'")
        retrieved = retriever.retrieve(query, top_k=2)
        
        print(f"[+] Retrieved {len(retrieved)} relevant chunks:")
        for idx, item in enumerate(retrieved):
            print(f"  Rank {idx+1}: {item['metadata'].get('source')} | Page {item['metadata'].get('page')} | CE Score: {item.get('rerank_score'):.4f} | RRF Score: {item.get('rrf_score'):.4f}")
            print(f"    Snippet: \"{item['text'][:80]}...\"")
            
        assert len(retrieved) > 0, "No chunks retrieved!"
        
        # 5. Generation Verification
        print("[*] Requesting LLM answer generation with inline citations...")
        generation = llm.generate_answer(query=query, retrieved_chunks=retrieved)
        print("[+] LLM Response:")
        print(f"--- ANSWER ---\n{generation['answer']}\n--------------")
        print(f"[+] Parsed Citations: {generation['citations']}")
        
        # 6. Evaluation Verification
        print("[*] Running LLM-as-a-judge automated pipeline evaluation...")
        eval_results = evaluator.run_all_evaluations(
            query=query,
            retrieved_chunks=retrieved,
            answer=generation['answer']
        )
        
        print("[+] Evaluation Suite Scores:")
        print(f"  - Faithfulness (Groundedness): {eval_results['faithfulness'].get('score'):.2f}")
        print(f"  - Context Relevance: {eval_results['context_relevance'].get('score'):.2f}")
        print(f"  - Answer Relevance: {eval_results['answer_relevance'].get('score'):.2f}")
        print(f"  - Combined RAG score: {eval_results['average_score']:.2f}")
        
        print("\n[+] SUCCESS: All stages of the production RAG pipeline integrated and verified successfully!")
        
    except Exception as e:
        print(f"\n[!] VERIFICATION FAILURE: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("[*] Cleaning up verification artifacts...")
        if os.path.exists(sample_file_path):
            os.remove(sample_file_path)
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
        print("[+] Cleanup complete.")

if __name__ == "__main__":
    main()
