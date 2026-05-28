'use client';
import { useState, useEffect, useRef } from 'react';
import styles from './ChatConsole.module.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: string[];
  timestamp: string;
}

interface EvalScores {
  faithfulness: { score: number; explanation: string };
  context_relevance: { score: number; explanation: string };
  answer_relevance: { score: number; explanation: string };
  average_score: number;
}

interface Chunk {
  id: string;
  text: string;
  metadata: { source: string; page: number };
  dense_score: number;
  sparse_score: number;
  rrf_rank: number;
  rrf_score: number;
  rerank_score: number;
}

interface QueryResult {
  answer: string;
  citations: string[];
  retrieved_chunks: Chunk[];
  evaluations: EvalScores;
  provider: string;
}

interface ChatConsoleProps {
  hasDocuments: boolean;
  onQueryResult?: (result: QueryResult) => void;
}

export default function ChatConsole({ hasDocuments, onQueryResult }: ChatConsoleProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  async function sendMessage() {
    const query = input.trim();
    if (!query || isLoading) return;

    const userMsg: Message = { role: 'user', content: query, timestamp: now() };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput('');
    setIsLoading(true);

    // Build history for memory (last 10 messages, excluding the one we just added)
    const historyForApi = updatedMessages.slice(-10).map(m => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          top_k: 5,
          enable_rerank: true,
          chat_history: historyForApi,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Query failed');
      }

      const data: QueryResult = await res.json();
      const assistantMsg: Message = {
        role: 'assistant',
        content: data.answer,
        citations: data.citations,
        timestamp: now(),
      };
      setMessages(prev => [...prev, assistantMsg]);
      onQueryResult?.(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `**Error:** ${message}`,
        timestamp: now(),
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className={styles.console}>
      <div className={styles.messages}>
        {messages.length === 0 && (
          <div className={styles.welcome}>
            <div className={styles.welcomeIcon}>🧠</div>
            <h3>RAG LAB Intelligence Layer</h3>
            <p>
              {hasDocuments
                ? 'Documents are indexed. Ask any question below!'
                : 'Upload a PDF or TXT document from the sidebar to get started.'}
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`${styles.msg} ${styles[`msg_${msg.role}`]}`}>
            <div className={styles.bubble}>
              <div
                className={styles.text}
                dangerouslySetInnerHTML={{
                  __html: msg.content
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/\n/g, '<br/>'),
                }}
              />
              {msg.citations && msg.citations.length > 0 && (
                <div className={styles.citations}>
                  <span className={styles.citLabel}>📎 Sources:</span>
                  {msg.citations.map((c, ci) => (
                    <span key={ci} className={styles.citPill}>{c}</span>
                  ))}
                </div>
              )}
            </div>
            <div className={styles.meta}>
              {msg.role === 'user' ? 'You' : 'RAG OS'} · {msg.timestamp}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className={`${styles.msg} ${styles.msg_assistant}`}>
            <div className={styles.bubble}>
              <div className={styles.typing}>
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className={styles.inputRow}>
        <input
          className={styles.input}
          type="text"
          placeholder="Ask anything about your documents..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          disabled={isLoading}
        />
        <button
          className={styles.sendBtn}
          onClick={sendMessage}
          disabled={isLoading || !input.trim()}
        >
          ↑
        </button>
      </div>
    </div>
  );
}
