import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMManager:
    def __init__(self):
        """
        Initializes the LLM manager, detecting available API keys.
        Supports Gemini (Google GenAI) and OpenAI.
        """
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
        self.provider = "mock"
        
        # Select provider based on key availability (prefer Gemini, then OpenAI)
        if self.gemini_key and self.gemini_key.strip():
            self.provider = "gemini"
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
            print("LLM Manager initialized with Google Gemini API.")
        elif self.openai_key and self.openai_key.strip():
            self.provider = "openai"
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=self.openai_key)
            print("LLM Manager initialized with OpenAI API.")
        else:
            print("WARNING: No LLM API keys found. Operating in OFFLINE MOCK MODE. Please add API keys to your .env file to enable real answers.")

    def set_keys(self, gemini_key: Optional[str] = None, openai_key: Optional[str] = None):
        """
        Dynamically update keys (used for web interface input).
        """
        if gemini_key and gemini_key.strip():
            self.gemini_key = gemini_key
            self.provider = "gemini"
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        elif openai_key and openai_key.strip():
            self.openai_key = openai_key
            self.provider = "openai"
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=self.openai_key)
        else:
            # Re-check environment if empty strings were passed
            self.__init__()

    def generate_answer(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Formats the context, constructs the citation-oriented prompt, and calls the selected LLM.
        """
        if not retrieved_chunks:
            return {
                "answer": "No documents have been indexed or no matching context could be retrieved. Please upload documents first.",
                "citations": [],
                "provider": self.provider
            }
            
        # Format the context blocks with index markers and metadata
        context_str_list = []
        for idx, chunk in enumerate(retrieved_chunks):
            meta = chunk["metadata"]
            src = meta.get("source", "unknown")
            page = meta.get("page", 1)
            c_idx = meta.get("chunk_index", 0)
            
            context_str_list.append(
                f"[Doc {idx+1} | Source: {src} | Page: {page} | Chunk ID: {c_idx}]\n"
                f"Content: {chunk['text']}\n"
                f"---"
            )
            
        context_str = "\n\n".join(context_str_list)
        
        # Build prompt enforcing citation rules
        system_instructions = (
            "You are an expert, professional, and precise AI assistant answering questions about user-uploaded documents.\n\n"
            "INSTRUCTIONS:\n"
            "1. Answer the user's question based strictly and ONLY on the provided document context. Do not make up facts, hallucinate, or bring in external knowledge.\n"
            "2. If the answer cannot be found in the provided context, state EXACTLY: 'I do not have enough information in the provided documents to answer this question.' Do not attempt to answer anyway.\n"
            "3. For every claim, fact, or statement you make that is derived from the context, you MUST append an inline citation referencing the document and page in the exact format: [Source: filename, page X]. Example: 'The fiscal year 2025 revenue grew by 15% [Source: financial_report.pdf, page 4].'\n"
            "4. Keep your answer professional, concise, structured, and easy to read. Use Markdown lists or tables where appropriate."
        )
        
        prompt = (
            f"{system_instructions}\n\n"
            f"--- START RETRIEVED CONTEXT ---\n"
            f"{context_str}\n"
            f"--- END RETRIEVED CONTEXT ---\n\n"
            f"User Question: {query}\n\n"
            f"Provide your answer below, ensuring strict adherence to the rules above:"
        )
        
        answer_text = ""
        
        # Invoke selected LLM provider
        if self.provider == "gemini":
            try:
                response = self.gemini_model.generate_content(prompt)
                answer_text = response.text
            except Exception as e:
                answer_text = f"Error generating answer with Gemini API: {str(e)}"
        elif self.provider == "openai":
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a professional document Q&A assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0
                )
                answer_text = response.choices[0].message.content
            except Exception as e:
                answer_text = f"Error generating answer with OpenAI API: {str(e)}"
        else:
            # Mock / Offline Mode
            # Demonstrate that the RAG pipeline is fully functional and show what chunk ranks was matched!
            top_sources = list(set([c["metadata"].get("source", "unknown") for c in retrieved_chunks[:3]]))
            pages = list(set([str(c["metadata"].get("page", 1)) for c in retrieved_chunks[:3]]))
            
            answer_text = (
                f"### [DEMO MODE - NO API KEY SET]\n"
                f"Your query *\"{query}\"* successfully executed through the entire offline **Hybrid Retrieval & Cross-Encoder Reranking pipeline**! "
                f"We retrieved the top **{len(retrieved_chunks)}** chunks locally.\n\n"
                f"**Retrieval Insights (Local Models):**\n"
                f"- Top document matched: `{top_sources[0] if top_sources else 'N/A'}` (page {pages[0] if pages else '1'})\n"
                f"- Best chunk cross-encoder score: `{retrieved_chunks[0].get('rerank_score', 0.0):.4f}`\n"
                f"- Best chunk BM25 keyword score: `{retrieved_chunks[0].get('sparse_score', 0.0):.4f}`\n\n"
                f"**Simulated Answer Based on Retrieved Context:**\n"
                f"Here is a mock answer showing the citation format: We found matching details in the file `{top_sources[0] if top_sources else 'doc'}` on page `{pages[0] if pages else '1'}`. "
                f"The text segment discusses the queried topics and provides context regarding your request [Source: {top_sources[0] if top_sources else 'document'}, page {pages[0] if pages else '1'}].\n\n"
                f"> **Setup instructions**: Please insert a valid `GEMINI_API_KEY` or `OPENAI_API_KEY` into the sidebar configuration or the `.env` file in the workspace to generate real-time answers!"
            )
            
        # Parse citations from text
        citations = []
        # Find all occurrences of [Source: filename, page X]
        import re
        citation_matches = re.findall(r"\[Source:\s*([^,\]]+),\s*page\s*(\d+)\]", answer_text)
        for doc_name, page_num in citation_matches:
            cit_str = f"{doc_name} (Page {page_num})"
            if cit_str not in citations:
                citations.append(cit_str)
                
        return {
            "answer": answer_text,
            "citations": citations,
            "provider": self.provider
        }

if __name__ == "__main__":
    print("Initializing LLMManager test...")
    manager = LLMManager()
    print("Testing generate_answer in offline mode...")
    test_chunks = [{
        "text": "Antigravity is a powerful agentic AI coding assistant designed by Google DeepMind.",
        "metadata": {"source": "antigravity_intro.pdf", "page": 1, "chunk_index": 0}
    }]
    res = manager.generate_answer("Who is Antigravity?", test_chunks)
    print("Result Answer:")
    print(res["answer"])
    print("Result Citations:", res["citations"])
