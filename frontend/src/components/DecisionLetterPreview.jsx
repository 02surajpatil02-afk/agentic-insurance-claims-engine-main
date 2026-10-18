import React from 'react';
import { FileCheck, Printer, Copy, CheckCircle, XCircle } from 'lucide-react';

export default function DecisionLetterPreview({ state }) {
  if (!state || !state.letter_draft) return null;

  const isApproved = state.decision === 'approved';

  return (
    <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
      
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <FileCheck size={18} color="var(--primary)" />
          <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#fff' }}>
            Generated Formal Decision Letter
          </h3>
          <span className={`badge ${isApproved ? 'badge-emerald' : 'badge-rose'}`}>
            {isApproved ? <CheckCircle size={12} /> : <XCircle size={12} />}
            {isApproved ? 'APPROVED NOTICE' : 'DENIAL NOTICE'}
          </span>
          <span className="badge badge-indigo">
            Path: {state.decision_path ? state.decision_path.toUpperCase() : 'AUTO'}
          </span>
        </div>

        <button
          className="btn btn-secondary"
          onClick={() => navigator.clipboard.writeText(state.letter_draft)}
          style={{ fontSize: '0.78rem', padding: '6px 12px' }}
        >
          <Copy size={14} /> Copy Letter Text
        </button>
      </div>

      <div style={{
        background: '#090d16',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '16px 20px',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.82rem',
        color: '#e2e8f0',
        lineHeight: 1.6,
        whiteSpace: 'pre-wrap',
        maxHeight: '380px',
        overflowY: 'auto'
      }}>
        {state.letter_draft}
      </div>

    </div>
  );
}
