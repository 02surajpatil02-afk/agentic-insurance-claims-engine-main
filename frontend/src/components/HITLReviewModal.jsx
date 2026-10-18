import React, { useState } from 'react';
import { AlertOctagon, ShieldAlert, CheckCircle, XCircle, UserCheck, FileText } from 'lucide-react';

export default function HITLReviewModal({ state, onResume }) {
  if (!state || state.status !== 'pending_human_review' || !state.exception_summary) return null;

  const summary = state.exception_summary;
  const [notes, setNotes] = useState('Authorized following senior clinical caseworker review & verification.');
  const [signature, setSignature] = useState('Senior Caseworker J. Smith, RN');
  const [submitting, setSubmitting] = useState(false);

  const handleAction = (action) => {
    setSubmitting(true);
    onResume(state.claim_id, action, notes, signature);
  };

  const riskPercent = Math.round(summary.risk_score * 100);
  let riskColor = 'var(--amber)';
  if (summary.risk_score > 0.7) riskColor = 'var(--rose)';

  return (
    <div className="glass-panel-glow" style={{ padding: '24px', marginBottom: '24px', background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)' }}>
      
      {/* Alert Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', pb: '16px', paddingBottom: '16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'rgba(245, 158, 11, 0.2)', border: '1px solid var(--amber)', display: 'flex', alignItems: 'center', justifyContent: 'center' }} className="pulse-active">
            <AlertOctagon size={26} color="var(--amber)" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: '800', color: '#fff' }}>
                HUMAN-IN-THE-LOOP (HITL) CASEWORKER REVIEW REQUIRED
              </h2>
              <span className="badge badge-amber">Workflow Halted</span>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Claim ID: <strong style={{ color: '#fff' }}>{state.claim_id}</strong> • Extracted Amount: <strong style={{ color: 'var(--amber)' }}>${state.extracted_entities.claim_amount?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong>
            </p>
          </div>
        </div>

        {/* Risk Score Meter */}
        <div style={{ background: 'rgba(0,0,0,0.4)', padding: '8px 16px', borderRadius: '10px', border: '1px solid var(--border-color)', textAlign: 'right' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Risk Assessment Score</div>
          <div style={{ fontSize: '1.2rem', fontWeight: '800', color: riskColor }}>
            {summary.risk_score} / 1.0 <span style={{ fontSize: '0.75rem', fontWeight: '600' }}>({riskPercent}%)</span>
          </div>
        </div>
      </div>

      {/* Exception Breakdown Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '20px' }}>
        
        {/* Left: Triggered Escalation Rules */}
        <div style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '14px' }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--amber)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ShieldAlert size={16} /> Triggered Escalation Reasons ({summary.triggered_rules.length}):
          </h4>
          {summary.triggered_rules.map((rule) => (
            <div key={rule.rule_id} style={{ fontSize: '0.8rem', color: '#fef3c7', background: 'rgba(245, 158, 11, 0.1)', padding: '8px 10px', borderRadius: '6px', marginBottom: '6px' }}>
              <strong>[{rule.rule_id} - {rule.rule_name}]:</strong> {rule.message}
            </div>
          ))}

          {summary.extraction_warnings && summary.extraction_warnings.length > 0 && (
            <div style={{ marginTop: '10px', fontSize: '0.75rem', color: '#cbd5e1' }}>
              <strong>Extraction Ambiguities:</strong>
              {summary.extraction_warnings.map((w, i) => (
                <div key={i}>• {w}</div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Suggested Action */}
        <div style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '14px' }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--cyan)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <UserCheck size={16} /> Agent Suggested Next Actions:
          </h4>
          <p style={{ fontSize: '0.82rem', color: '#e2e8f0', lineHeight: 1.6, background: 'rgba(6, 182, 212, 0.08)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(6, 182, 212, 0.2)' }}>
            {summary.suggested_action}
          </p>
        </div>

      </div>

      {/* Caseworker Sign-off Form */}
      <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-accent)', borderRadius: '10px', padding: '16px' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: '700', color: '#fff', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <FileText size={16} color="var(--primary)" /> Caseworker Digital Sign-off & Decision Override
        </h4>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '12px', marginBottom: '14px' }}>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Caseworker Digital Signature</label>
            <input
              type="text"
              value={signature}
              onChange={(e) => setSignature(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-color)', borderRadius: '6px', color: '#fff', fontSize: '0.85rem' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Clinical / Audit Review Notes</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Enter review notes for audit trail..."
              style={{ width: '100%', padding: '8px 12px', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-color)', borderRadius: '6px', color: '#fff', fontSize: '0.85rem' }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '12px' }}>
          <button
            className="btn btn-rose"
            onClick={() => handleAction('reject')}
            disabled={submitting}
          >
            <XCircle size={16} />
            Reject Claim & Issue Denial
          </button>

          <button
            className="btn btn-emerald"
            onClick={() => handleAction('approve')}
            disabled={submitting}
          >
            <CheckCircle size={16} />
            Sign-off & Approve Claim (${state.extracted_entities.claim_amount?.toLocaleString()})
          </button>
        </div>

      </div>

    </div>
  );
}
