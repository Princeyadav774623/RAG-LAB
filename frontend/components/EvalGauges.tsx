'use client';
import { useEffect } from 'react';
import styles from './EvalGauges.module.css';

interface GaugeProps {
  score: number;
  label: string;
  explanation: string;
  color: string;
}

function Gauge({ score, label, explanation, color }: GaugeProps) {
  const r = 40;
  const circ = 2 * Math.PI * r;
  const offset = circ - score * circ;

  return (
    <div className={styles.gauge}>
      <div className={styles.svgWrap}>
        <svg viewBox="0 0 100 100">
          <circle className={styles.ringBg} cx="50" cy="50" r={r} />
          <circle
            className={styles.ringFill}
            cx="50" cy="50" r={r}
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ stroke: color, transition: 'stroke-dashoffset 0.8s ease' }}
          />
        </svg>
        <span className={styles.score} style={{ color }}>{score.toFixed(2)}</span>
      </div>
      <h5 className={styles.gaugeLabel}>{label}</h5>
      <p className={styles.gaugeExp}>{explanation || '—'}</p>
    </div>
  );
}

interface EvalData {
  faithfulness: { score: number; explanation: string };
  context_relevance: { score: number; explanation: string };
  answer_relevance: { score: number; explanation: string };
  average_score: number;
}

export default function EvalGauges({ evals }: { evals: EvalData | null }) {
  if (!evals) {
    return (
      <div className={styles.placeholder}>
        <p>Ask a question to see live evaluation scores</p>
      </div>
    );
  }

  const scoreColor = (s: number) => s >= 0.8 ? '#22c55e' : s >= 0.5 ? '#f59e0b' : '#ef4444';

  return (
    <div className={styles.gaugesGrid}>
      <Gauge
        score={evals.faithfulness.score}
        label="Faithfulness"
        explanation={evals.faithfulness.explanation}
        color={scoreColor(evals.faithfulness.score)}
      />
      <Gauge
        score={evals.context_relevance.score}
        label="Context Relevance"
        explanation={evals.context_relevance.explanation}
        color={scoreColor(evals.context_relevance.score)}
      />
      <Gauge
        score={evals.answer_relevance.score}
        label="Answer Relevance"
        explanation={evals.answer_relevance.explanation}
        color={scoreColor(evals.answer_relevance.score)}
      />
    </div>
  );
}
