import streamlit as st
import os
import time
import pandas as pd
import numpy as np

# Core Pipeline Imports
from ingestion import DocumentIngester
from retriever import HybridRetriever
from llm_manager import LLMManager
from evaluator import RAGEvaluator

# 1. Page Configuration & Custom CSS Aesthetic System
st.set_page_config(
    page_title="RAG Document Q&A Portfolio Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Design CSS injection
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
h1, h2, h3, .gradient-title {
    font-family: 'Outfit', sans-serif;
}

.gradient-title {
    background: linear-gradient(135deg, #7F77DD 0%, #378ADD 50%, #1D9E75 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 2.5rem;
    margin-bottom: 0.2rem;
}

/* Glassmorphism Metrics */
.metric-box {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 18px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
}
.metric-val {
    font-size: 28px;
    font-weight: 700;
    margin: 0;
}
.metric-lbl {
    font-size: 12px;
    color: #888888;
    margin: 5px 0 0 0;
}

/* Pipeline Status Badges */
.status-pill {
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    display: inline-block;
}
.sp-active { background-color: rgba(29, 158, 117, 0.15); color: #1D9E75; border: 1px solid #1D9E75; }
.sp-offline { background-color: rgba(239, 159, 39, 0.15); color: #EF9F27; border: 1px solid #EF9F27; }

/* Custom Accordion / Card Style */
.custom-card {
    background: #111217;
    border-left: 4px solid #7F77DD;
    padding: 12px 18px;
    border-radius: 4px 12px 12px 4px;
    margin-bottom: 12px;
}
.custom-card-title {
    font-weight: 600;
    color: #FFFFFF;
    margin-bottom: 4px;
}
.custom-card-sub {
    font-size: 12.5px;
    color: #AAAAAA;
}

/* Citation Badges */
.citation-badge {
    background-color: #EEEDFE;
    color: #3C3489;
    font-size: 11.5px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 6px;
    display: inline-block;
    margin-right: 6px;
    margin-top: 6px;
    border: 0.5px solid #7F77DD;
}

/* Source Details Table */
.chunk-table {
    width: 100%;
    border-collapse: collapse;
}
.chunk-table th {
    background-color: rgba(127, 119, 221, 0.1);
    color: #7F77DD;
    font-weight: 600;
    text-align: left;
    padding: 8px;
    font-size: 12px;
}
.chunk-table td {
    padding: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    font-size: 12.5px;
}

/* Micro animations */
.glow-indicator {
    box-shadow: 0 0 10px rgba(29, 158, 117, 0.5);
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0% { transform: scale(0.95); opacity: 0.5; }
    50% { transform: scale(1); opacity: 1; }
    100% { transform: scale(0.95); opacity: 0.5; }
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 2. Session State Management & Pipeline Hooking
if "ingester" not in st.session_state:
    st.session_state.ingester = DocumentIngester()
if "retriever" not in st.session_state:
    st.session_state.retriever = HybridRetriever()
if "llm" not in st.session_state:
    st.session_state.llm = LLMManager()
if "evaluator" not in st.session_state:
    st.session_state.evaluator = RAGEvaluator(llm_manager=st.session_state.llm)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_query_metrics" not in st.session_state:
    st.session_state.last_query_metrics = None

# Get local handles
ingester = st.session_state.ingester
retriever = st.session_state.retriever
llm = st.session_state.llm
evaluator = st.session_state.evaluator

# 3. SIDEBAR: Configuration & Stack Diagnostics
with st.sidebar:
    st.markdown('<p style="font-size: 20px; font-weight: 700; color: #FFFFFF; margin: 0 0 5px 0;">⚙️ RAG Engine Panel</p>', unsafe_allow_html=True)
    st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
    
    # 3.1 LLM Credentials Configuration
    with st.expander("🔑 LLM Credentials", expanded=True):
        st.markdown("<p style='font-size: 12px; color: #888888;'>Dynamic credentials override .env values</p>", unsafe_allow_html=True)
        
        gemini_input = st.text_input(
            "GEMINI_API_KEY", 
            value=os.getenv("GEMINI_API_KEY", ""), 
            type="password",
            placeholder="AIzaSy..."
        )
        openai_input = st.text_input(
            "OPENAI_API_KEY", 
            value=os.getenv("OPENAI_API_KEY", ""), 
            type="password",
            placeholder="sk-proj-..."
        )
        
        if st.button("Apply Keys", use_container_width=True):
            llm.set_keys(gemini_key=gemini_input, openai_key=openai_input)
            st.success("Credentials updated successfully!")
            time.sleep(0.5)
            st.rerun()

    # 3.2 Stack Status Indicator Badges
    with st.expander("🛠️ Active Tech Stack", expanded=True):
        st.markdown(
            f"**LLM Generator**: "
            f"{'<span class=\"status-pill sp-active\">Gemini</span>' if llm.provider == 'gemini' else ('<span class=\"status-pill sp-active\">OpenAI</span>' if llm.provider == 'openai' else '<span class=\"status-pill sp-offline\">Mock (Demo Mode)</span>')}",
            unsafe_allow_html=True
        )
        st.markdown(
            "**Dense Vector Search**: <span class='status-pill sp-active'>ChromaDB (Local)</span>", 
            unsafe_allow_html=True
        )
        st.markdown(
            "**Dense Embeddings**: <span class='status-pill sp-active'>all-MiniLM-L6-v2</span>", 
            unsafe_allow_html=True
        )
        st.markdown(
            "**Sparse Search**: <span class='status-pill sp-active'>BM25Okapi</span>", 
            unsafe_allow_html=True
        )
        st.markdown(
            "**Reranker**: <span class='status-pill sp-active'>cross-encoder/ms-marco-v2</span>", 
            unsafe_allow_html=True
        )
        st.markdown(
            "**Evaluation**: <span class='status-pill sp-active'>LLM-as-a-Judge</span>", 
            unsafe_allow_html=True
        )
        
    # 3.3 Database Status & Stats
    stats = ingester.get_stats()
    with st.expander("📊 Corpus Metadata", expanded=True):
        st.metric("Total Indexed Chunks", stats["total_chunks"])
        st.metric("Unique Uploaded Files", stats["unique_documents"])
        
        if st.button("Wipe Database", type="secondary", use_container_width=True):
            ingester.clear_database()
            # Force retriever refresh
            st.session_state.retriever = HybridRetriever()
            st.success("Database cleared successfully!")
            time.sleep(0.5)
            st.rerun()

# 4. MAIN PANEL LAYOUT
st.markdown('<p class="gradient-title">RAG Document Q&A Portfolio Dashboard</p>', unsafe_allow_html=True)
st.markdown("<p style='font-size: 15px; color: #888888; margin-top:0px;'>Advanced Hybrid Retrieval (Dense Vector + Sparse Keyword) with Cross-Encoder Reranking and Real-time Evaluation</p>", unsafe_allow_html=True)

# Main Tab Bar
tab_chat, tab_docs = st.tabs(["💬 Contextual Chat Assistant", "📁 Ingestion & Document Manager"])

# -----------------
# TAB 1: CONTEXTUAL CHAT ASSISTANT
# -----------------
with tab_chat:
    col_chat, col_analytics = st.columns([1.1, 0.9])
    
    with col_chat:
        st.markdown('<p style="font-size: 18px; font-weight: 600; color: #7F77DD; margin-bottom: 10px;">💬 Dynamic Conversation</p>', unsafe_allow_html=True)
        
        # Displays welcome panel if chat is empty
        if not st.session_state.chat_history:
            st.markdown(
                '<div class="custom-card">'
                '<p class="custom-card-title">🚀 Welcome to your Advanced RAG System!</p>'
                '<p class="custom-card-sub">To get started, switch to the <b>Ingestion Manager</b> tab to upload documents (PDF/TXT) or start chatting if documents are already indexed.<br><br>'
                'Ask domain-specific questions to see semantic hybrid retrieval and Cross-Encoder reranking in action. Every answer will be fully grounded with precise page-level citations.</p>'
                '</div>',
                unsafe_allow_html=True
            )
            
        # Render Chat History
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "citations" in message and message["citations"]:
                    st.markdown("---")
                    st.markdown("**Grounded Citations:**")
                    for cit in message["citations"]:
                        st.markdown(f'<span class="citation-badge">{cit}</span>', unsafe_allow_html=True)

        # Chat Input Form
        if query := st.chat_input("Ask a question about your documents..."):
            # Append User Question
            st.session_state.chat_history.append({"role": "user", "content": query})
            with st.chat_message("user"):
                st.markdown(query)
                
            # Perform RAG Pipeline In-flight
            with st.chat_message("assistant"):
                with st.spinner("Executing retrieval, reranking, and generation..."):
                    start_time = time.time()
                    
                    # 1. Retrieve context
                    retrieved_chunks = retriever.retrieve(query=query, top_k=5)
                    
                    if not retrieved_chunks:
                        ans_text = "No context chunks could be retrieved. Please verify that you have uploaded files under the **Ingestion & Document Manager** tab."
                        st.markdown(ans_text)
                        st.session_state.chat_history.append({"role": "assistant", "content": ans_text})
                    else:
                        # 2. Generate answer
                        results = llm.generate_answer(query=query, retrieved_chunks=retrieved_chunks)
                        answer = results["answer"]
                        citations = results["citations"]
                        
                        # 3. Perform Evaluations (Faithfulness, Context Relevance, Answer Relevance)
                        eval_results = evaluator.run_all_evaluations(
                            query=query, 
                            retrieved_chunks=retrieved_chunks, 
                            answer=answer
                        )
                        
                        latency = time.time() - start_time
                        
                        # Render answer
                        st.markdown(answer)
                        
                        # Render citations
                        if citations:
                            st.markdown("---")
                            st.markdown("**Grounded Citations:**")
                            for cit in citations:
                                st.markdown(f'<span class="citation-badge">{cit}</span>', unsafe_allow_html=True)
                                
                        # Save metadata to session state for diagnostic display
                        st.session_state.last_query_metrics = {
                            "query": query,
                            "latency": latency,
                            "chunks": retrieved_chunks,
                            "evaluations": eval_results
                        }
                        
                        # Append Assistant Answer
                        st.session_state.chat_history.append({
                            "role": "assistant", 
                            "content": answer,
                            "citations": citations
                        })
                        
                        time.sleep(0.1)
                        st.rerun()

    # RAG PIPELINE DIAGNOSTICS & ANALYTICS SIDE PANEL
    with col_analytics:
        st.markdown('<p style="font-size: 18px; font-weight: 600; color: #1D9E75; margin-bottom: 10px;">📊 Real-time Pipeline Diagnostics</p>', unsafe_allow_html=True)
        
        if not st.session_state.last_query_metrics:
            st.info("Ask a question to see real-time search weights, reranking scores, and LLM-as-a-judge grounding metrics!")
        else:
            q_metrics = st.session_state.last_query_metrics
            evals = q_metrics["evaluations"]
            
            # Metrics Gauges (Groundedness, Context, Answer Relevance)
            st.markdown("##### 🩺 LLM-as-a-Judge Evaluation Scores")
            
            col_f, col_c, col_a = st.columns(3)
            
            # 1. Faithfulness Score UI
            f_score = evals["faithfulness"].get("score", 0.0)
            f_color = "#1D9E75" if f_score >= 0.8 else ("#EF9F27" if f_score >= 0.5 else "#D85A30")
            with col_f:
                st.markdown(
                    f'<div class="metric-box">'
                    f'<p class="metric-val" style="color: {f_color}">{f_score:.2f}</p>'
                    f'<p class="metric-lbl">Faithfulness<br>(Groundedness)</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
            # 2. Context Relevance Score UI
            c_score = evals["context_relevance"].get("score", 0.0)
            c_color = "#1D9E75" if c_score >= 0.8 else ("#EF9F27" if c_score >= 0.5 else "#D85A30")
            with col_c:
                st.markdown(
                    f'<div class="metric-box">'
                    f'<p class="metric-val" style="color: {c_color}">{c_score:.2f}</p>'
                    f'<p class="metric-lbl">Context<br>Relevance</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
            # 3. Answer Relevance Score UI
            a_score = evals["answer_relevance"].get("score", 0.0)
            a_color = "#1D9E75" if a_score >= 0.8 else ("#EF9F27" if a_score >= 0.5 else "#D85A30")
            with col_a:
                st.markdown(
                    f'<div class="metric-box">'
                    f'<p class="metric-val" style="color: {a_color}">{a_score:.2f}</p>'
                    f'<p class="metric-lbl">Answer<br>Relevance</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            
            st.caption(f"**Query Latency**: {q_metrics['latency']:.2f}s | **Average Judge Score**: {evals['average_score']:.2f}")
            
            # Show explanation details
            with st.expander("🔍 Read Evaluation Critiques"):
                st.markdown(f"**Faithfulness Explanation**:\n> *{evals['faithfulness'].get('explanation', 'N/A')}*")
                st.markdown(f"**Context Relevance Explanation**:\n> *{evals['context_relevance'].get('explanation', 'N/A')}*")
                st.markdown(f"**Answer Relevance Explanation**:\n> *{evals['answer_relevance'].get('explanation', 'N/A')}*")
                
            # Hybrid Search Reranking Table Deep Dive
            st.markdown("##### 🔬 Search & Reranking Stack Deep Dive")
            
            # Build Table of matches
            table_rows = []
            for i, chunk in enumerate(q_metrics["chunks"]):
                meta = chunk["metadata"]
                src = meta.get("source", "doc")
                page = meta.get("page", 1)
                
                dense_score = chunk.get("dense_score", 0.0)
                sparse_score = chunk.get("sparse_score", 0.0)
                rrf_score = chunk.get("rrf_score", 0.0)
                rerank_score = chunk.get("rerank_score", 0.0)
                
                table_rows.append({
                    "Rank": i + 1,
                    "Source": f"{src} (p.{page})",
                    "Dense Sim": f"{dense_score:.4f}",
                    "BM25 Keyword": f"{sparse_score:.4f}",
                    "RRF Rank": f"{chunk.get('rrf_rank', 'N/A')}",
                    "Cross-Encoder": f"{rerank_score:.4f}"
                })
                
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
            
            # Display retrieved text blocks with cross-encoder highlight borders
            st.markdown("##### 📄 Retrieved Document Chunks (In Reranked Order)")
            for i, chunk in enumerate(q_metrics["chunks"]):
                meta = chunk["metadata"]
                src = meta.get("source", "doc")
                page = meta.get("page", 1)
                rerank_score = chunk.get("rerank_score", 0.0)
                
                border_color = "#1D9E75" if i == 0 else "#7F77DD"
                
                st.markdown(
                    f'<div style="background: #1e1e24; border-left: 3px solid {border_color}; border-radius: 4px; padding: 10px 14px; margin-bottom: 10px;">'
                    f'<p style="font-size: 11.5px; color: #888888; margin: 0 0 4px 0;">'
                    f'<b>Rank {i+1}</b> | 📂 {src} (Page {page}) | 🎯 CE Rerank Score: <b>{rerank_score:.4f}</b>'
                    f'</p>'
                    f'<p style="font-size: 12.5px; color: #E0E0E0; line-height: 1.5; margin: 0;">'
                    f'{chunk["text"]}'
                    f'</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )

# -----------------
# TAB 2: DOCUMENT INGESTION MANAGER
# -----------------
with tab_docs:
    st.markdown('<p style="font-size: 18px; font-weight: 600; color: #7F77DD; margin-bottom: 10px;">📁 Document Corpus Manager</p>', unsafe_allow_html=True)
    
    col_upload, col_corpus = st.columns([1, 1])
    
    with col_upload:
        st.markdown("##### 📥 Ingest New Documents")
        uploaded_files = st.file_uploader(
            "Upload legal, financial, or academic PDF/TXT files", 
            type=["pdf", "txt"], 
            accept_multiple_files=True
        )
        
        st.markdown("##### ⚙️ Indexing Hyperparameters")
        c_size = st.slider("Chunk Character Size", min_value=100, max_value=2000, value=500, step=50)
        c_overlap = st.slider("Chunk Overlap Size", min_value=0, max_value=500, value=50, step=10)
        
        if st.button("Trigger Indexing Pipeline ⚡", use_container_width=True, type="primary"):
            if not uploaded_files:
                st.warning("Please drag and drop at least one PDF or TXT document.")
            else:
                progress_bar = st.progress(0.0)
                status_text = st.empty()
                
                total_chunks = 0
                temp_dir = "./temp_uploads"
                os.makedirs(temp_dir, exist_ok=True)
                
                for idx, u_file in enumerate(uploaded_files):
                    status_text.text(f"Processing {u_file.name}...")
                    
                    # Save to local temporary path
                    temp_path = os.path.join(temp_dir, u_file.name)
                    with open(temp_path, "wb") as f:
                        f.write(u_file.getvalue())
                        
                    file_ext = os.path.splitext(u_file.name)[1].lower()
                    
                    # 1. Parse File
                    if file_ext == ".pdf":
                        raw_docs = ingester.load_pdf(temp_path)
                    else:
                        raw_docs = ingester.load_txt(temp_path)
                        
                    if not raw_docs:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        continue
                        
                    # 2. Chunking
                    chunks = ingester.split_text(raw_docs, chunk_size=c_size, chunk_overlap=c_overlap)
                    
                    # 3. Local embedding & insertion
                    chunks_added = ingester.add_documents(chunks)
                    total_chunks += chunks_added
                    
                    # Clean up temp
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
                    # Update progress
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                    
                status_text.text("Ingestion process completed!")
                st.success(f"Successfully processed {len(uploaded_files)} file(s). Embedded and indexed **{total_chunks}** text chunks in ChromaDB!")
                time.sleep(1.0)
                
                # Re-initialize hybrid retriever to bind to populated DB
                st.session_state.retriever = HybridRetriever()
                st.rerun()
                
    with col_corpus:
        st.markdown("##### 🗄️ Ingested Corpus Explorer")
        
        db_stats = ingester.get_stats()
        if not db_stats["documents"]:
            st.info("The vector database collection is currently empty. Upload documents to index them.")
        else:
            st.markdown(f"**Database contains {db_stats['unique_documents']} document(s):**")
            
            # Display documents as a nice interactive table
            doc_df = pd.DataFrame(db_stats["documents"])
            st.dataframe(
                doc_df.rename(columns={"filename": "Document Filename", "chunks": "Chroma DB Chunks"}),
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("---")
            # Step by Step pipeline guide review callout
            st.markdown(
                '<div style="background: rgba(127, 119, 221, 0.05); border: 1px solid rgba(127, 119, 221, 0.2); border-radius: 8px; padding: 12px; font-size:12.5px; color:#c0bceb;">'
                '💡 <b>Pro-Tip for Portfolios</b>: Hybrid Retrieval merging dense (vector) and sparse (keyword) search scores '
                'with RRF, followed by Cross-Encoder reranking, is what differentiates production AI systems from basic tutorial demos!'
                '</div>',
                unsafe_allow_html=True
            )
