'use client';
import { useState, useEffect } from 'react';
import styles from './LockScreen.module.css';

const CORRECT_PASSWORD = 'raglab2026';
const STORAGE_KEY = 'raglab_unlocked';

interface LockScreenProps {
  children: React.ReactNode;
}

export default function LockScreen({ children }: LockScreenProps) {
  const [unlocked, setUnlocked] = useState(false);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [shake, setShake] = useState(false);

  useEffect(() => {
    // Check if user already unlocked in this session
    if (sessionStorage.getItem(STORAGE_KEY) === 'true') {
      setUnlocked(true);
    }
  }, []);

  function handleUnlock() {
    if (password === CORRECT_PASSWORD) {
      sessionStorage.setItem(STORAGE_KEY, 'true');
      setUnlocked(true);
    } else {
      setError('Incorrect access key. Try again.');
      setShake(true);
      setTimeout(() => setShake(false), 500);
      setPassword('');
    }
  }

  if (unlocked) return <>{children}</>;

  return (
    <div className={styles.overlay}>
      {/* Background orbs */}
      <div className={styles.orb1} />
      <div className={styles.orb2} />
      <div className={styles.orb3} />

      <div className={`${styles.card} ${shake ? styles.shake : ''}`}>
        <div className={styles.icon}>🔒</div>
        <h1 className={styles.title}>
          <span className={styles.gradient}>RAG LAB</span>
        </h1>
        <p className={styles.sub}>Enter your access key to continue</p>

        <input
          className={styles.input}
          type="password"
          placeholder="Access key..."
          value={password}
          onChange={e => { setPassword(e.target.value); setError(''); }}
          onKeyDown={e => e.key === 'Enter' && handleUnlock()}
          autoFocus
        />
        {error && <p className={styles.error}>{error}</p>}

        <button className={styles.btn} onClick={handleUnlock}>
          Unlock Playground →
        </button>

        <p className={styles.hint}>
          Built with FastAPI · Pinecone · Gemini · Next.js
        </p>
      </div>
    </div>
  );
}
