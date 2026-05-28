import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'RAG LAB — Precision Document Intelligence',
  description: 'Production-grade RAG system with hybrid retrieval, Gemini embeddings, and real-time LLM-as-a-Judge evaluation.',
  keywords: ['RAG', 'AI', 'document intelligence', 'vector search', 'Gemini', 'Pinecone'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark">
      <body>{children}</body>
    </html>
  );
}
