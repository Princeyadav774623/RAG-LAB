'use client';
import { useState, useEffect, useRef } from 'react';
import styles from './page.module.css';
import LockScreen from '../components/LockScreen';
import ChatConsole from '../components/ChatConsole';
import FileUploader from '../components/FileUploader';
import EvalGauges from '../components/EvalGauges';

interface DocStats {
  total_chunks: number;
  unique_documents: number;
  documents: { filename: string; chunks: number }[];
}
interface QueryResult {
  answer: string; citations: string[];
  retrieved_chunks: Array<{ id: string; text: string; metadata: { source: string; page: number }; dense_score: number; sparse_score: number; rrf_rank: number; rrf_score: number; rerank_score: number; }>;
  evaluations: { faithfulness: { score: number; explanation: string }; context_relevance: { score: number; explanation: string }; answer_relevance: { score: number; explanation: string }; average_score: number; };
  provider: string;
}

const faqs = [
  { q: 'How do I use RAG LAB to query documents?', a: 'Upload a PDF or TXT file using the drag-and-drop area in the Playground. Once indexed, type any question in the chat console and RAG LAB will retrieve the most relevant sections and generate a cited answer.' },
  { q: 'What file types are supported?', a: 'RAG LAB currently supports PDF and TXT files. Support for DOCX, CSV, and web URLs is planned in the next release.' },
  { q: 'What AI model is used for embeddings?', a: 'RAG LAB uses Google Gemini (gemini-embedding-2) to generate 768-dimensional dense vector embeddings, stored in Pinecone for semantic retrieval.' },
  { q: 'How does hybrid retrieval work?', a: 'RAG LAB combines dense semantic vector search (Pinecone) with sparse keyword search (Supabase full-text) using Reciprocal Rank Fusion (RRF) to combine both rankings into the best possible result.' },
  { q: 'Does it have conversation memory?', a: 'Yes! RAG LAB injects the last 5 turns of your conversation into every prompt, so the AI correctly understands follow-up questions like "explain more about that".' },
  { q: 'What are the LLM-as-a-Judge scores?', a: 'After every answer, RAG LAB automatically evaluates Faithfulness (no hallucinations), Context Relevance (quality of retrieved chunks), and Answer Relevance (how well the answer addresses the query). Each is scored 0.0–1.0.' },
];

export default function HomePage() {
  const [stats, setStats] = useState<DocStats>({ total_chunks: 0, unique_documents: 0, documents: [] });
  const [lastResult, setLastResult] = useState<QueryResult | null>(null);
  const [activeTab, setActiveTab] = useState<'chat' | 'analytics'>('chat');
  const [isOnline, setIsOnline] = useState(true);
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const [navScrolled, setNavScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setNavScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  async function fetchStats() {
    try {
      const res = await fetch('/status');
      if (res.ok) { const data = await res.json(); setStats(data.stats); }
    } catch { /* backend not running locally */ }
  }

  async function checkHealth() {
    try {
      const res = await fetch('/health');
      setIsOnline(res.ok);
    } catch { setIsOnline(true); } // default online for Render
  }

  async function clearDatabase() {
    if (!confirm('Wipe all indexed documents? This cannot be undone.')) return;
    await fetch('/clear', { method: 'POST' });
    fetchStats();
  }

  useEffect(() => {
    checkHealth();
    fetchStats();
    const iv = setInterval(fetchStats, 15000);
    return () => clearInterval(iv);
  }, []);

  return (
    <LockScreen>
      <div className={styles.page}>

        {/* ── FLOATING PILL NAVBAR ── */}
        <div className={styles.headerWrapper}>
          <header className={`${styles.navContainer} ${navScrolled ? styles.navScrolled : ''}`}>
            <div className={styles.navBgBlur} />
            <div className={styles.navBgShadow} />
            <div className={styles.navInner}>
              <a href="/" className={styles.logo}>
                <span className={styles.logoMark}>⚗</span>
                <span className={styles.logoText}>RAG<span className={styles.logoAccent}>LAB</span></span>
              </a>
              <nav className={styles.navLinks}>
                <a href="#hero">Home</a>
                <a href="#how-it-works">How it Works</a>
                <a href="#features">Features</a>
                <a href="http://localhost:8000/docs" target="_blank">API</a>
                <a href="#faq">FAQ</a>
              </nav>
              <div className={styles.navActions}>
                <div className={styles.statusBadge}>
                  <span className={`${styles.statusDot} ${isOnline ? styles.online : styles.offline}`} />
                  {isOnline ? 'Live' : 'Offline'}
                </div>
                <a href="#playground" className={styles.navCta}>
                  Try it free
                </a>
              </div>
            </div>
          </header>
        </div>

        {/* ── HERO ── */}
        <section id="hero" className={styles.hero}>
          <div className={styles.heroBgWrap}>
            <div className={styles.heroBgPattern} />
            <div className={styles.heroBgGradient} />
          </div>
          <div className={styles.heroFade} />

          <div className={styles.heroContent}>
            <div className={styles.heroBadge}>
              <div className={styles.badgeAvatars}>
                {['🧑🏽‍💻','👩🏻‍🔬','🧑🏾‍💼','👨🏼‍💻'].map((e,i) => (
                  <span key={i} className={styles.avatar}>{e}</span>
                ))}
              </div>
              <span>Loved by researchers & developers</span>
            </div>

            <h1 className={styles.heroTitle}>
              Query Documents<br />with AI Precision.<br />In Seconds.
            </h1>

            <p className={styles.heroSubtitle}>
              Upload any PDF or document. Ask questions in plain language.<br />
              RAG LAB finds the answer with full citations — automatically.<br /><br />
              Even across hundreds of pages, multiple files, or follow-up questions.
            </p>

            <a href="#playground" className={styles.heroCta}>
              Try the Playground for free
            </a>
          </div>
        </section>

        {/* ── DEMO SECTION ── */}
        <section className={styles.demoSection}>
          <div className={styles.demoHeader}>
            <h2 className={styles.demoTitle}>Get answers as if an expert read your document.</h2>
            <p className={styles.demoSub}>No more Ctrl+F. No more skimming. Just ask — and get a cited, grounded answer.</p>
          </div>
          <div className={styles.demoCard}>
            <div className={styles.demoChat}>
              <div className={styles.demoBubbleUser}>What are the main risk factors for type 2 diabetes?</div>
              <div className={styles.demoBubbleAI}>
                <p>The main risk factors include <strong>obesity, physical inactivity, and family history</strong> [Source: diabetes_booklet.pdf, page 2]. Additionally, age over 45 and a history of gestational diabetes significantly increase risk [Source: diabetes_booklet.pdf, page 3].</p>
                <div className={styles.demoCitations}>
                  <span>📎 diabetes_booklet.pdf (Page 2)</span>
                  <span>📎 diabetes_booklet.pdf (Page 3)</span>
                </div>
              </div>
            </div>
            <div className={styles.demoMetrics}>
              <div className={styles.demoMetricItem}><span className={styles.demoMetricVal}>0.94</span><span className={styles.demoMetricLabel}>Faithfulness</span></div>
              <div className={styles.demoMetricItem}><span className={styles.demoMetricVal}>0.88</span><span className={styles.demoMetricLabel}>Context Relevance</span></div>
              <div className={styles.demoMetricItem}><span className={styles.demoMetricVal}>0.92</span><span className={styles.demoMetricLabel}>Answer Relevance</span></div>
            </div>
          </div>
          <div className={styles.demoCta}>
            <a href="#playground" className={styles.btnDark}>
              <svg viewBox="0 0 20 20" fill="none" width="18" height="18"><path d="M3.75 7.5v5M6.25 5.625v8.75M8.75 8.75v2.5M11.25 6.25v7.5M13.75 8.125v3.75M16.25 6.875v6.25" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round"/></svg>
              Query your documents for free
            </a>
            <p className={styles.demoHint}>No sign-up required. Works with any PDF or TXT file.</p>
          </div>
        </section>

        {/* ── HOW IT WORKS ── */}
        <section id="how-it-works" className={styles.stepsSection}>
          <div className={styles.container}>
            <div className={styles.stepsHeader}>
              <h2 className={styles.stepsTitle}>How to query documents with AI?</h2>
              <p className={styles.stepsSub}>No AI expertise needed. No complex setup.<br /><strong>Simple for anyone, from first-time users to engineers.</strong></p>
              <a href="#playground" className={styles.btnDarkSm}>
                <svg viewBox="0 0 20 20" fill="none" width="16" height="16"><path d="M4 7v6M7 5v10M10 8v4M13 6v8M16 8v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
                Try Now
              </a>
            </div>

            <div className={styles.stepsGrid}>
              {[
                { n: '1', icon: '📄', title: 'Upload your PDF or TXT file', desc: 'Drag and drop any document into the Playground. RAG LAB parses, chunks, and indexes it in seconds.' },
                { n: '2', icon: '🧠', title: 'Let AI find the answers', desc: 'Hybrid vector + keyword search retrieves the most relevant passages. Gemini embeddings ensure precision.' },
                { n: '3', icon: '✅', title: 'Get cited, grounded answers', desc: 'Every response includes exact page-level citations and real-time quality scores so you can trust every word.' },
              ].map(step => (
                <div key={step.n} className={styles.stepCard}>
                  <div className={styles.stepVisual}>
                    <div className={styles.stepGlow} />
                    <span className={styles.stepEmoji}>{step.icon}</span>
                  </div>
                  <div className={styles.stepFoot}>
                    <span className={styles.stepNum}>{step.n}</span>
                    <h3 className={styles.stepTitle}>{step.title}</h3>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── FEATURES ── */}
        <section id="features" className={styles.featuresSection}>
          <div className={styles.container}>
            {[
              {
                title: 'Hybrid Retrieval Engine',
                serif: 'Precision at scale.',
                desc: 'RAG LAB combines dense semantic vector search (Pinecone) with BM25 sparse keyword search (Supabase). The results are merged using Reciprocal Rank Fusion — giving you the best of both worlds. No single retrieval strategy gets everything right; hybrid does.',
                badge: 'Dense + Sparse + RRF',
                reverse: false,
              },
              {
                title: 'Conversation Memory',
                serif: 'Context that sticks.',
                desc: 'Most RAG systems forget context after each question. Not RAG LAB. The last 5 turns of your conversation are injected into every prompt, so the AI correctly resolves follow-up questions like "tell me more about that" or "what about its treatment?".',
                badge: '5-Turn Memory',
                reverse: true,
              },
              {
                title: 'LLM-as-a-Judge Evaluation',
                serif: 'Trust, verified.',
                desc: 'After every answer, a separate Gemini call evaluates the response for Faithfulness (no hallucinations), Context Relevance (quality of retrieved text), and Answer Relevance (addressing the actual question). Every number is displayed in real-time on the Analytics tab.',
                badge: 'Evaluation-First',
                reverse: false,
              },
            ].map((f, i) => (
              <div key={i} className={`${styles.featureRow} ${f.reverse ? styles.featureReverse : ''}`}>
                <div className={styles.featureVisual}>
                  <div className={styles.featureCardPlaceholder}>
                    <div className={styles.featureInner}>
                      <span className={styles.featureBadge}>{f.badge}</span>
                      <div className={styles.featureBar}><div className={styles.featureBarFill} /></div>
                      <div className={styles.featureBar}><div className={styles.featureBarFill} style={{width:'60%'}} /></div>
                      <div className={styles.featureBar}><div className={styles.featureBarFill} style={{width:'80%'}} /></div>
                    </div>
                  </div>
                </div>
                <div className={styles.featureText}>
                  <h2 className={styles.featureTitle}>{f.title}</h2>
                  <p className={styles.featureDesc}>{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── PLAYGROUND ── */}
        <section id="playground" className={styles.playgroundSection}>
          <div className={styles.container}>
            <div className={styles.playgroundHeader}>
              <h2 className={styles.playgroundTitle}>
                Query your documents.<br />
                <em className={styles.serif}>Audit every citation.</em>
              </h2>
              <p className={styles.playgroundSub}>Upload a file and start asking questions. Every answer includes citations and live quality scores.</p>
            </div>

            <div className={styles.playgroundLayout}>
              {/* Sidebar */}
              <aside className={styles.sidebar}>
                <div className={styles.sideBlock}>
                  <h4 className={styles.sideTitle}>📂 Upload Document</h4>
                  <FileUploader onUploadSuccess={(s) => setStats(s)} />
                </div>
                <div className={styles.sideBlock}>
                  <h4 className={styles.sideTitle}>📊 Corpus</h4>
                  <div className={styles.statsRow}>
                    <div className={styles.statBox}>
                      <span className={styles.statNum}>{stats.total_chunks}</span>
                      <span className={styles.statLbl}>Chunks</span>
                    </div>
                    <div className={styles.statBox}>
                      <span className={styles.statNum}>{stats.unique_documents}</span>
                      <span className={styles.statLbl}>Files</span>
                    </div>
                  </div>
                  <div className={styles.fileList}>
                    {stats.documents.length === 0
                      ? <p className={styles.noFiles}>No files indexed yet</p>
                      : stats.documents.map(d => (
                          <div key={d.filename} className={styles.fileItem}>📄 {d.filename} ({d.chunks})</div>
                        ))}
                  </div>
                  <button className={styles.clearBtn} onClick={clearDatabase}>🗑 Wipe Collection</button>
                </div>
              </aside>

              {/* Main Panel */}
              <div className={styles.mainPanel}>
                <div className={styles.tabs}>
                  <button className={`${styles.tab} ${activeTab === 'chat' ? styles.activeTab : ''}`} onClick={() => setActiveTab('chat')}>💬 Chat Console</button>
                  <button className={`${styles.tab} ${activeTab === 'analytics' ? styles.activeTab : ''}`} onClick={() => setActiveTab('analytics')}>📊 Analytics</button>
                </div>
                <div className={styles.tabBody}>
                  <div style={{ display: activeTab === 'chat' ? 'block' : 'none', height: '100%' }}>
                    <ChatConsole hasDocuments={stats.total_chunks > 0} onQueryResult={setLastResult} />
                  </div>
                  <div style={{ display: activeTab === 'analytics' ? 'block' : 'none', height: '100%' }}>
                    <div className={styles.analyticsPanel}>
                      <h4>🛡️ LLM-as-a-Judge Scores</h4>
                      <EvalGauges evals={lastResult?.evaluations ?? null} />
                      {lastResult && lastResult.retrieved_chunks.length > 0 && (
                        <>
                          <h4 style={{ marginTop: 24 }}>🔬 Retrieval Fusion Table</h4>
                          <div className={styles.tableWrap}>
                            <table className={styles.table}>
                              <thead><tr><th>Rank</th><th>Source</th><th>Dense</th><th>Sparse</th><th>RRF Score</th></tr></thead>
                              <tbody>
                                {lastResult.retrieved_chunks.map((c, i) => (
                                  <tr key={c.id}>
                                    <td><strong>#{i+1}</strong></td>
                                    <td>{c.metadata.source} (p.{c.metadata.page})</td>
                                    <td>{c.dense_score.toFixed(3)}</td>
                                    <td>{c.sparse_score.toFixed(3)}</td>
                                    <td>{c.rrf_score.toFixed(4)}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── FAQ ── */}
        <section id="faq" className={styles.faqSection}>
          <div className={styles.container}>
            <div className={styles.faqTop}>
              <h2 className={styles.faqTitle}>
                <span>Frequently Asked</span>
                <em className={styles.serif}>Questions</em>
              </h2>
              <a href="http://localhost:8000/docs" target="_blank" className={styles.btnDarkSm}>
                <svg viewBox="0 0 20 20" fill="none" width="16" height="16"><circle cx="10" cy="10" r="6.25" stroke="currentColor" strokeWidth="1.3"/><path d="M8.35 8.27C8.43 7.23 9.21 6.5 10.24 6.5C11.33 6.5 12.1 7.2 12.1 8.15C12.1 8.87 11.73 9.31 11.06 9.72C10.43 10.1 10.2 10.42 10.2 11.06V11.32" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.3"/><path d="M10.2 13.35H10.21" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8"/></svg>
                View API Docs
              </a>
            </div>
            <div className={styles.faqList}>
              {faqs.map((faq, i) => (
                <div key={i} className={`${styles.faqItem} ${openFaq === i ? styles.faqOpen : ''}`}>
                  <button className={styles.faqQ} onClick={() => setOpenFaq(openFaq === i ? null : i)}>
                    <span>{faq.q}</span>
                    <span className={`${styles.faqIcon} ${openFaq === i ? styles.faqIconOpen : ''}`}>
                      <span className={styles.faqIconH} />
                      <span className={styles.faqIconV} />
                    </span>
                  </button>
                  {openFaq === i && <div className={styles.faqA}>{faq.a}</div>}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── FOOTER ── */}
        <div className={styles.footerWrapper}>
          <footer className={styles.footer}>
            <div className={styles.footerBg} />
            <div className={styles.footerWave}>
              <img src="/figma-footer-waveform.svg" alt="waveform" />
            </div>
            <div className={styles.footerContent}>
              <div className={styles.footerTop}>
                <div className={styles.footerBrand}>
                  <div className={styles.footerLogo}>
                    <span className={styles.logoMark}>⚗</span>
                    <span className={styles.logoText}>RAG<span className={styles.logoAccent}>LAB</span></span>
                  </div>
                  <p className={styles.footerTagline}>Precision Document Intelligence — Powered by Google Gemini and Pinecone Vector Search.</p>
                </div>
                <div className={styles.footerLinks}>
                  <div className={styles.footerCol}>
                    <h4>Product</h4>
                    <a href="#playground">Playground Console</a>
                    <a href="#features">Core Features</a>
                    <a href="#how-it-works">How it Works</a>
                    <a href="#faq">FAQ</a>
                  </div>
                  <div className={styles.footerCol}>
                    <h4>Use Cases</h4>
                    <a href="#">Academic Research</a>
                    <a href="#">Legal Document Analysis</a>
                    <a href="#">Medical Literature</a>
                    <a href="#">Financial Audits</a>
                  </div>
                  <div className={styles.footerCol}>
                    <h4>Resources</h4>
                    <a href="http://localhost:8000/docs" target="_blank">API Documentation</a>
                    <a href="https://github.com/Princeyadav774623/RAG-LAB" target="_blank">GitHub Repository</a>
                    <a href="#">Developer Guides</a>
                    <a href="#">System Architecture</a>
                  </div>
                  <div className={styles.footerCol}>
                    <h4>Legal & Company</h4>
                    <a href="#">Privacy Policy</a>
                    <a href="#">Terms of Service</a>
                    <a href="#">Open Source License</a>
                  </div>
                </div>
              </div>
              <div className={styles.footerBottom}>
                <p className={styles.footerCopy}>© 2026 RAG LAB. Open Source & Active.</p>
                <div className={styles.footerTechTags}>
                  {['FastAPI','Pinecone','Supabase','Gemini','Next.js','Python'].map(t => (
                    <span key={t} className={styles.techTag}>{t}</span>
                  ))}
                </div>
              </div>
            </div>
          </footer>
        </div>

      </div>
    </LockScreen>
  );
}
