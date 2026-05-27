/* ==========================================================================
   PRODUCTION-GRADE FRONTEND CONTROLLER - RAG OS 2026
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // Pipeline API Config
    const API_BASE = ""; // Relative paths since served from same FastAPI process
    
    // Credentials State
    let localGeminiKey = "";
    let localOpenaiKey = "";

    // DOM Element Handles
    const apiStatusDot = document.getElementById("api-status-dot");
    const apiStatusText = document.getElementById("api-status-text");
    const themeToggleBtn = document.getElementById("theme-toggle-btn");

    // ==========================================================================
    // 0. THEME SWITCHING SERVICE (DARK / LIGHT / SYSTEM SELECTION DROPDOWN)
    // ==========================================================================
    const themeDropdownMenu = document.getElementById("theme-dropdown-menu");
    const themeMenuItems = document.querySelectorAll(".theme-menu-item");
    let currentTheme = localStorage.getItem("theme") || "system";
    
    function applyTheme(theme) {
        if (!themeToggleBtn) return;
        
        // Determine corresponding icon name
        let iconName = "laptop";
        if (theme === "dark") {
            iconName = "moon";
            document.documentElement.setAttribute("data-theme", "dark");
        } else if (theme === "light") {
            iconName = "sun";
            document.documentElement.setAttribute("data-theme", "light");
        } else {
            document.documentElement.removeAttribute("data-theme");
        }
        
        // Recreate the icon tag dynamically to prevent Lucide mutation errors
        themeToggleBtn.innerHTML = `<i data-lucide="${iconName}" class="theme-toggle-icon"></i>`;
        
        // Update active class on dropdown items
        themeMenuItems.forEach(item => {
            if (item.dataset.themeVal === theme) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });
        
        // Persist theme choice
        localStorage.setItem("theme", theme);
        currentTheme = theme;
        
        // Re-create icons to reflect changes
        lucide.createIcons();
    }
    
    // Toggle dropdown visibility on click
    if (themeToggleBtn && themeDropdownMenu) {
        themeToggleBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            themeDropdownMenu.classList.toggle("active");
        });
        
        // Register click listeners for theme options
        themeMenuItems.forEach(item => {
            item.addEventListener("click", (e) => {
                e.stopPropagation();
                const selectedTheme = item.dataset.themeVal;
                applyTheme(selectedTheme);
                themeDropdownMenu.classList.remove("active");
            });
        });
        
        // Close dropdown when clicking anywhere else
        document.addEventListener("click", (e) => {
            if (!e.target.closest(".theme-dropdown-wrapper")) {
                themeDropdownMenu.classList.remove("active");
            }
        });
    }
    
    // Apply persisted theme on load
    applyTheme(currentTheme);
    
    const apiProviderSelect = document.getElementById("api-provider");
    const credentialsWrapper = document.getElementById("credentials-wrapper");
    const geminiKeyInput = document.getElementById("gemini-key");
    const geminiKeyWrapper = document.getElementById("gemini-key-wrapper");
    const openaiKeyInput = document.getElementById("openai-key");
    const openaiKeyWrapper = document.getElementById("openai-key-wrapper");
    
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const uploadProgressContainer = document.getElementById("upload-progress-container");
    const uploadProgressFill = document.getElementById("upload-progress-fill");
    const uploadStatusText = document.getElementById("upload-status-text");
    
    const statChunks = document.getElementById("stat-chunks");
    const statFiles = document.getElementById("stat-files");
    const filesList = document.getElementById("files-list");
    const clearDbBtn = document.getElementById("clear-db-btn");
    
    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const chatSendBtn = document.getElementById("chat-send-btn");
    
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");
    const diagnosticsTabBtn = document.getElementById("diagnostics-tab-btn");
    
    // Evaluation Gauge DOM Handles
    const gaugeFaithfulness = document.getElementById("gauge-faithfulness");
    const gaugeContext = document.getElementById("gauge-context");
    const gaugeAnswer = document.getElementById("gauge-answer");
    
    const valFaithfulness = document.getElementById("val-faithfulness");
    const valContext = document.getElementById("val-context");
    const valAnswer = document.getElementById("val-answer");
    
    const expFaithfulness = document.getElementById("exp-faithfulness");
    const expContext = document.getElementById("exp-context");
    const expAnswer = document.getElementById("exp-answer");
    
    const retrievalTableBody = document.querySelector("#retrieval-table tbody");
    const chunksLogsContainer = document.getElementById("chunks-logs");

    // ==========================================================================
    // 1. INITIALIZATION & HEALTH SERVICES
    // ==========================================================================
    
    async function checkSystemHealth() {
        try {
            const res = await fetch(`${API_BASE}/health`);
            if (res.ok) {
                const data = await res.json();
                apiStatusDot.classList.add("online");
                apiStatusText.innerText = "Online";
                
                // Set initial active provider matching the backend default
                if (data.llm_provider !== "mock") {
                    apiProviderSelect.value = data.llm_provider;
                    handleProviderToggle();
                }
                
                chatInput.disabled = false;
                chatSendBtn.disabled = false;
                chatInput.placeholder = "Ask a question about your indexed files...";
                return true;
            }
        } catch (e) {
            console.error("Health check failure:", e);
        }
        
        apiStatusDot.classList.remove("online");
        apiStatusText.innerText = "Offline";
        chatInput.disabled = true;
        chatSendBtn.disabled = true;
        chatInput.placeholder = "Server connection lost...";
        return false;
    }
    
    async function fetchCorpusStats() {
        try {
            const res = await fetch(`${API_BASE}/status`);
            if (res.ok) {
                const data = await res.json();
                const stats = data.stats;
                
                statChunks.innerText = stats.total_chunks;
                statFiles.innerText = stats.unique_documents;
                
                if (stats.documents && stats.documents.length > 0) {
                    filesList.innerHTML = "";
                    stats.documents.forEach(doc => {
                        const div = document.createElement("div");
                        div.className = "indexed-file-item";
                        div.innerHTML = `<i data-lucide="file-check"></i> <span>${doc.filename} (${doc.chunks} chunks)</span>`;
                        filesList.appendChild(div);
                    });
                    lucide.createIcons();
                    
                    // Enable chat inputs if files exist
                    chatInput.disabled = false;
                    chatSendBtn.disabled = false;
                } else {
                    filesList.innerHTML = '<div class="no-files-msg">No files indexed yet</div>';
                }
            }
        } catch (e) {
            console.error("Failed to load corpus stats:", e);
        }
    }

    // ==========================================================================
    // 2. CREDENTIALS HANDLERS
    // ==========================================================================

    function handleProviderToggle() {
        const val = apiProviderSelect.value;
        if (val === "mock") {
            credentialsWrapper.classList.add("hidden");
        } else {
            credentialsWrapper.classList.remove("hidden");
            if (val === "gemini") {
                geminiKeyWrapper.classList.remove("hidden");
                openaiKeyWrapper.classList.add("hidden");
            } else {
                geminiKeyWrapper.classList.add("hidden");
                openaiKeyWrapper.classList.remove("hidden");
            }
        }
    }
    
    apiProviderSelect.addEventListener("change", handleProviderToggle);
    geminiKeyInput.addEventListener("input", (e) => { localGeminiKey = e.target.value; });
    openaiKeyInput.addEventListener("input", (e) => { localOpenaiKey = e.target.value; });

    // ==========================================================================
    // 3. FILE INGESTION pipeline
    // ==========================================================================

    // Drag-Drop Triggers
    ["dragenter", "dragover"].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add("dragover");
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
        }, false);
    });

    dropZone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFileUpload(files);
        }
    });

    dropZone.addEventListener("click", () => {
        fileInput.click();
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files);
        }
    });

    async function handleFileUpload(filesListObj) {
        const formData = new FormData();
        for (let i = 0; i < filesListObj.length; i++) {
            formData.append("files", filesListObj[i]);
        }
        formData.append("chunk_size", 500);
        formData.append("chunk_overlap", 50);
        
        uploadProgressContainer.classList.remove("hidden");
        uploadProgressFill.style.width = "40%";
        uploadStatusText.innerText = "Parsing files...";
        
        try {
            const res = await fetch(`${API_BASE}/upload`, {
                method: "POST",
                body: formData
            });
            
            if (res.ok) {
                uploadProgressFill.style.width = "100%";
                uploadStatusText.innerText = "Indexing success!";
                setTimeout(() => {
                    uploadProgressContainer.classList.add("hidden");
                    uploadProgressFill.style.width = "0%";
                }, 1500);
                
                // Refresh database metrics
                fetchCorpusStats();
            } else {
                const err = await res.json();
                alert(`Upload failed: ${err.detail || "Error occurred"}`);
                uploadProgressContainer.classList.add("hidden");
            }
        } catch (e) {
            console.error("Upload failure:", e);
            alert("File upload failed. Connect to local backend server.");
            uploadProgressContainer.classList.add("hidden");
        }
    }
    
    // Clear Database Trigger
    clearDbBtn.addEventListener("click", async () => {
        if (confirm("Are you sure you want to completely wipe your persistent ChromaDB corpus collection? This cannot be undone.")) {
            try {
                const res = await fetch(`${API_BASE}/clear`, { method: "POST" });
                if (res.ok) {
                    alert("Database successfully wiped.");
                    fetchCorpusStats();
                    chatMessages.innerHTML = `
                        <div class="chat-welcome">
                            <div class="welcome-badge"><i data-lucide="shield-check"></i> 100% Grounded AI</div>
                            <h3>Ready to interact with your knowledge.</h3>
                            <p>Upload files in the sidebar and ask specific queries. Your responses will be dynamically checked against local vector stores, scored by our reranker, and generated with explicit citations.</p>
                        </div>
                    `;
                    lucide.createIcons();
                }
            } catch (e) {
                console.error(e);
            }
        }
    });

    // ==========================================================================
    // 4. INTERACTIVE TAB NAVIGATION
    // ==========================================================================

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            tabButtons.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(btn.dataset.tab).classList.add("active");
        });
    });

    // ==========================================================================
    // 5. CHAT broker AND EVALUATION GAUGES
    // ==========================================================================

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !chatInput.disabled && chatInput.value.trim() !== "") {
            submitChatQuery();
        }
    });

    chatSendBtn.addEventListener("click", () => {
        if (!chatInput.disabled && chatInput.value.trim() !== "") {
            submitChatQuery();
        }
    });

    async function submitChatQuery() {
        const queryText = chatInput.value.trim();
        if (!queryText) return;
        
        // Remove welcome panel if present
        const welcomePanel = document.querySelector(".chat-welcome");
        if (welcomePanel) welcomePanel.remove();
        
        // 5.1 Render User Bubble
        appendChatBubble("user", queryText);
        chatInput.value = "";
        
        // 5.2 Append Typing Indicator Bubble
        const typingBubble = appendChatBubble("assistant", '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>');
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Prep payload
        const payload = {
            query: queryText,
            top_k: 5,
            enable_rerank: true
        };
        
        // Inject keys dynamically if present
        if (apiProviderSelect.value === "gemini" && localGeminiKey) {
            payload.gemini_key = localGeminiKey;
        } else if (apiProviderSelect.value === "openai" && localOpenaiKey) {
            payload.openai_key = localOpenaiKey;
        }
        
        try {
            const res = await fetch(`${API_BASE}/query`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            
            // Remove typing bubble
            typingBubble.remove();
            
            if (res.ok) {
                const data = await res.json();
                
                // 5.3 Render Assistant bubble with citations
                appendChatBubble("assistant", data.answer, data.citations);
                
                // 5.4 Update Audit Gauges & Diagnostics Panel
                updateDiagnosticPanels(data);
                
                // Highlight Analytics Panel tab to indicate audit has updated
                diagnosticsTabBtn.classList.add("glow-indicator");
                setTimeout(() => {
                    diagnosticsTabBtn.classList.remove("glow-indicator");
                }, 3000);
                
            } else {
                const err = await res.json();
                appendChatBubble("assistant", `<b>API Error:</b> ${err.detail || "Unable to complete Q&A pipeline."}`);
            }
        } catch (e) {
            typingBubble.remove();
            appendChatBubble("assistant", `<b>Connection Loss:</b> Unable to connect to backend processes.`);
            console.error(e);
        }
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendChatBubble(role, content, citations = []) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `chat-msg msg-${role}`;
        
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        let citationHtml = "";
        if (citations && citations.length > 0) {
            citationHtml = `
                <div class="msg-citations">
                    <div class="citation-header"><i data-lucide="bookmark-check" style="width:10px;height:10px;vertical-align:-1px;display:inline-block;margin-right:2px;"></i> Verified Sources:</div>
                    ${citations.map(cit => `<span class="cit-pill">${cit}</span>`).join("")}
                </div>
            `;
        }
        
        messageDiv.innerHTML = `
            <div class="msg-bubble">${content}${citationHtml}</div>
            <div class="msg-meta">${role === "user" ? "You" : "RAG OS"} • ${timestamp}</div>
        `;
        
        chatMessages.appendChild(messageDiv);
        lucide.createIcons();
        return messageDiv;
    }

    // ==========================================================================
    // 6. RAG DIAGNOSTICS & AUDITING GAUGES
    // ==========================================================================

    function animateCircularRing(gaugeEl, score) {
        // Circumference is 2 * pi * radius (r=40) = ~251.2
        const circumference = 251.2;
        const offset = circumference - (score * circumference);
        gaugeEl.style.strokeDashoffset = offset;
    }

    function updateDiagnosticPanels(data) {
        const evals = data.evaluations;
        
        // 6.1 Animate Gauges & Scoring numbers
        const fScore = evals.faithfulness.score || 0;
        const cScore = evals.context_relevance.score || 0;
        const aScore = evals.answer_relevance.score || 0;
        
        valFaithfulness.innerText = fScore.toFixed(2);
        valContext.innerText = cScore.toFixed(2);
        valAnswer.innerText = aScore.toFixed(2);
        
        animateCircularRing(gaugeFaithfulness, fScore);
        animateCircularRing(gaugeContext, cScore);
        animateCircularRing(gaugeAnswer, aScore);
        
        // Write critiques
        expFaithfulness.innerText = evals.faithfulness.explanation || "No written critique provided.";
        expContext.innerText = evals.context_relevance.explanation || "No written critique provided.";
        expAnswer.innerText = evals.answer_relevance.explanation || "No written critique provided.";
        
        // 6.2 Populate Search Fusion Analytics Table
        retrievalTableBody.innerHTML = "";
        
        if (data.retrieved_chunks && data.retrieved_chunks.length > 0) {
            data.retrieved_chunks.forEach((chunk, index) => {
                const tr = document.createElement("tr");
                
                const rank = index + 1;
                const source = `${chunk.metadata.source} (Page ${chunk.metadata.page || 1})`;
                const denseVal = chunk.dense_score ? chunk.dense_score.toFixed(4) : "0.0000";
                const sparseVal = chunk.sparse_score ? chunk.sparse_score.toFixed(4) : "0.0000";
                const rrfVal = `${chunk.rrf_rank || "N/A"} (${chunk.rrf_score ? chunk.rrf_score.toFixed(4) : "N/A"})`;
                const ceVal = chunk.rerank_score ? chunk.rerank_score.toFixed(4) : "N/A";
                
                tr.innerHTML = `
                    <td><b>${rank}</b></td>
                    <td>${source}</td>
                    <td><span class="status-pill sp-active">${denseVal}</span></td>
                    <td><span class="status-pill sp-active">${sparseVal}</span></td>
                    <td><span class="status-pill sp-active">${rrfVal}</span></td>
                    <td><span class="status-pill sp-active" style="background-color:rgba(127,119,221,0.1);color:var(--color-purple);border-color:var(--color-purple);">${ceVal}</span></td>
                `;
                retrievalTableBody.appendChild(tr);
            });
        } else {
            retrievalTableBody.innerHTML = `<tr><td colspan="6" class="table-empty">No context blocks retrieved for query.</td></tr>`;
        }
        
        // 6.3 Populate Chunk Text Segment Logs
        chunksLogsContainer.innerHTML = "";
        
        if (data.retrieved_chunks && data.retrieved_chunks.length > 0) {
            data.retrieved_chunks.forEach((chunk, index) => {
                const logItem = document.createElement("div");
                logItem.className = "chunk-log-item";
                
                const source = `${chunk.metadata.source} (Page ${chunk.metadata.page || 1})`;
                const ceScore = chunk.rerank_score ? chunk.rerank_score.toFixed(4) : "N/A";
                
                logItem.innerHTML = `
                    <div class="chunk-log-header">
                        <span><b>Rank ${index + 1}</b> • 📂 ${source}</span>
                        <span>CE Rerank Score: <b>${ceScore}</b></span>
                    </div>
                    <div class="chunk-log-body">
                        "${chunk.text}"
                    </div>
                `;
                chunksLogsContainer.appendChild(logItem);
            });
        } else {
            chunksLogsContainer.innerHTML = '<div class="no-chunks-msg">No chunks retrieved</div>';
        }
    }

    // ==========================================================================
    // 7. DYNAMIC NAVIGATION SCROLL SPY (ALLYS STYLE ACTIVE PILL TRANSITION)
    // ==========================================================================
    const sections = document.querySelectorAll("section[id]");
    const navLinks = document.querySelectorAll(".nav-link");

    function scrollSpyHandler() {
        const scrollPosition = window.scrollY + 120; // Offset to clear the floating capsule navbar

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute("id");

            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                navLinks.forEach(link => {
                    link.classList.remove("active");
                    if (link.getAttribute("href") === `#${sectionId}`) {
                        link.classList.add("active");
                    }
                });
            }
        });
    }

    window.addEventListener("scroll", scrollSpyHandler);



    // ==========================================================================
    // 9. INITIAL STARTUP SEQUENCING
    // ==========================================================================
    
    async function runStartupSequence() {
        console.log("[*] Starting RAG OS Web UI Startup sequencing...");
        handleProviderToggle();
        const isOnline = await checkSystemHealth();
        if (isOnline) {
            await fetchCorpusStats();
        }
    }
    
    // Launch Sequence
    runStartupSequence();
});
