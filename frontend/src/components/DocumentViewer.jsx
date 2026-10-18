import React from 'react';
import { FileText, Copy } from 'lucide-react';

export default function DocumentViewer({ rawText }) {
  const lines = rawText ? rawText.split('\n') : [];

  return (
    <div className="glass-panel" style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <h3 style={{ fontSize: '0.9rem', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileText size={16} color="var(--primary)" />
          Raw Claim Document Viewer
        </h3>
        <span className="badge badge-indigo">{lines.length} Lines</span>
      </div>

      <div style={{
        flex: 1,
        background: '#090d16',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '14px',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.82rem',
        color: '#cbd5e1',
        overflowY: 'auto',
        whiteSpace: 'pre-wrap',
        maxHeight: '420px'
      }}>
        {lines.map((line, idx) => (
          <div key={idx} style={{ display: 'flex', gap: '16px' }}>
            <span style={{ color: '#475569', userSelect: 'none', minWidth: '24px', textAlign: 'right' }}>{idx + 1}</span>
            <span style={{ flex: 1 }}>{line}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
