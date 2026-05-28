'use client';
import { useState, useCallback } from 'react';
import styles from './FileUploader.module.css';

interface UploadStats {
  total_chunks: number;
  unique_documents: number;
  documents: { filename: string; chunks: number }[];
}

interface FileUploaderProps {
  onUploadSuccess: (stats: UploadStats) => void;
}

export default function FileUploader({ onUploadSuccess }: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState('');

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const formData = new FormData();
    Array.from(files).forEach(f => formData.append('files', f));
    formData.append('chunk_size', '500');
    formData.append('chunk_overlap', '50');

    setIsUploading(true);
    setStatus('Uploading & indexing...');

    try {
      const res = await fetch('/api/upload', { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed');
      }
      const data = await res.json();
      setStatus('✅ Indexed successfully!');
      setTimeout(() => setStatus(''), 3000);
      onUploadSuccess(data.db_stats);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setStatus(`❌ ${message}`);
      setTimeout(() => setStatus(''), 4000);
    } finally {
      setIsUploading(false);
    }
  }, [onUploadSuccess]);

  return (
    <div className={styles.wrapper}>
      <label
        className={`${styles.dropzone} ${isDragging ? styles.dragging : ''} ${isUploading ? styles.uploading : ''}`}
        onDragEnter={e => { e.preventDefault(); setIsDragging(true); }}
        onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={e => {
          e.preventDefault();
          setIsDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
      >
        <input
          type="file"
          multiple
          accept=".pdf,.txt"
          style={{ display: 'none' }}
          onChange={e => handleFiles(e.target.files)}
          disabled={isUploading}
        />
        <div className={styles.icon}>
          {isUploading ? (
            <div className={styles.spinner} />
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          )}
        </div>
        <p className={styles.label}>{isUploading ? 'Processing...' : 'Drop PDF or TXT here'}</p>
        <p className={styles.sub}>or click to browse</p>
      </label>
      {status && <p className={styles.statusMsg}>{status}</p>}
    </div>
  );
}
