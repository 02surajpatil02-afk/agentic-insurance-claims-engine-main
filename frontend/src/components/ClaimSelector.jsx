import React, { useState } from 'react';
import { Play, FileText, Upload, Sparkles } from 'lucide-react';

export default function ClaimSelector({ samples, onRunClaim, onSelectSample, loading }) {
  const [selectedSample, setSelectedSample] = useState(null);
  const [customText, setCustomText] = useState('');
  const [activeTab, setActiveTab] = useState('preset'); // 'preset' | 'custom'

  const handleSelectSample = (sample) => {
    setSelectedSample(sample);
    setCustomText(sample.content);
    if (onSelectSample) {
      onSelectSample(sample);
    }
  };

  const handleExecute = () => {
    const textToRun = activeTab === 'preset' ? selectedSample?.content : customText;
    if (textToRun) {
      onRunClaim(textToRun);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '20px 24px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} color="var(--cyan)" />
            Select or Ingest Claim Document
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Choose a preloaded scenario or paste custom unstructured claim text to execute agent pipeline
          </p>
        </div>

        <div style={{ display: 'flex', background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <button
            onClick={() => setActiveTab('preset')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'preset' ? 'var(--primary)' : 'transparent',
              color: activeTab === 'preset' ? '#fff' : 'var(--text-muted)',
              fontSize: '0.8rem',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Preloaded Scenarios
          </button>
          <button
            onClick={() => setActiveTab('custom')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'custom' ? 'var(--primary)' : 'transparent',
              color: activeTab === 'custom' ? '#fff' : 'var(--text-muted)',
              fontSize: '0.8rem',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Custom Text Input
          </button>
        </div>
      </div>

      {activeTab === 'preset' ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '16px' }}>
          {samples.map((sample, idx) => {
            const isSelected = selectedSample?.filename === sample.filename;
            let tagColor = 'badge-emerald';
            let tagText = 'Auto-Approve';

            if (sample.filename.includes('over_threshold')) {
              tagColor = 'badge-amber';
              tagText = 'HITL Trigger (> $10k)';
            } else if (sample.filename.includes('conflicting_data')) {
              tagColor = 'badge-amber';
              tagText = 'HITL (Data Mismatch)';
            } else if (sample.filename.includes('clean_reject')) {
              tagColor = 'badge-rose';
              tagText = 'Hard Rejection';
            }

            return (
              <div
                key={sample.filename}
                onClick={() => handleSelectSample(sample)}
                style={{
                  background: isSelected ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                  border: isSelected ? '1px solid var(--primary)' : '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '14px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <span className={`badge ${tagColor}`} style={{ marginBottom: '8px' }}>{tagText}</span>
                <h4 style={{ fontSize: '0.9rem', fontWeight: '700', color: '#fff', marginBottom: '4px' }}>
                  {sample.title}
                </h4>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {sample.content.substring(0, 90)}...
                </p>
              </div>
            );
          })}
        </div>
      ) : (
        <div style={{ marginBottom: '16px' }}>
          <textarea
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            placeholder="Paste raw unstructured claim text here (e.g. Claimant Name, Policy POL-XXXXXXX, Claim Amount $X,XXX.XX)..."
            rows={5}
            style={{
              width: '100%',
              background: 'rgba(0,0,0,0.3)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '12px',
              color: '#fff',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.85rem',
              outline: 'none',
              resize: 'vertical'
            }}
          />
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          {activeTab === 'preset' && selectedSample ? (
            <span>Selected: <strong style={{ color: '#fff' }}>{selectedSample.title}</strong> ({selectedSample.content.length} characters)</span>
          ) : (
            <span>Ready to process claim through multi-step agent flow</span>
          )}
        </div>

        <button
          className="btn btn-primary"
          disabled={loading || (activeTab === 'preset' && !selectedSample) || (activeTab === 'custom' && !customText.trim())}
          onClick={handleExecute}
          style={{ opacity: loading ? 0.6 : 1, padding: '10px 24px', fontSize: '0.95rem' }}
        >
          <Play size={16} />
          {loading ? 'Agents Executing Live...' : 'Run Agents'}
        </button>
      </div>
    </div>
  );
}
