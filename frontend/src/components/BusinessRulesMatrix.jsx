import React from 'react';
import { CheckSquare, CheckCircle, XCircle, AlertTriangle, Shield } from 'lucide-react';

export default function BusinessRulesMatrix({ validationResults }) {
  if (!validationResults) return null;

  const passedCount = validationResults.filter(r => r.passed).length;
  const failedCount = validationResults.length - passedCount;

  return (
    <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
      
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckSquare size={18} color="var(--primary)" />
            Declarative Business Rules Engine Matrix
          </h3>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Evaluated {validationResults.length} enterprise rules: {passedCount} Passed, {failedCount} Triggered
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <span className="badge badge-emerald">{passedCount} Passed</span>
          {failedCount > 0 && <span className="badge badge-rose">{failedCount} Failed / Escalated</span>}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(1, 1fr)', gap: '10px' }}>
        {validationResults.map((r) => {
          let statusBadge = <span className="badge badge-emerald"><CheckCircle size={12} /> PASS</span>;
          let borderStyle = '1px solid var(--border-color)';
          let bgStyle = 'rgba(255,255,255,0.02)';

          if (!r.passed) {
            if (r.severity === 'reject') {
              statusBadge = <span className="badge badge-rose"><XCircle size={12} /> REJECT TRIGGER</span>;
              borderStyle = '1px solid rgba(244, 63, 94, 0.4)';
              bgStyle = 'rgba(244, 63, 94, 0.08)';
            } else if (r.severity === 'escalate') {
              statusBadge = <span className="badge badge-amber"><AlertTriangle size={12} /> HITL ESCALATION</span>;
              borderStyle = '1px solid rgba(245, 158, 11, 0.4)';
              bgStyle = 'rgba(245, 158, 11, 0.08)';
            }
          }

          return (
            <div key={r.rule_id} style={{
              background: bgStyle,
              border: borderStyle,
              borderRadius: '8px',
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px'
            }}>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: '700', color: 'var(--cyan)', background: 'rgba(6, 182, 212, 0.1)', padding: '2px 8px', borderRadius: '4px' }}>
                  {r.rule_id}
                </span>
                
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: '700', color: '#fff' }}>
                    {r.rule_name}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: r.passed ? 'var(--text-muted)' : '#fca5a5' }}>
                    {r.message}
                  </div>
                  {r.citations && r.citations.length > 0 && (
                    <div style={{ marginTop: '6px', fontSize: '0.75rem', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '4px', padding: '6px 10px', color: '#93c5fd' }}>
                      <span style={{ fontWeight: '600' }}>📖 Policy Citation ({r.citations[0].document_name}, p.{r.citations[0].page_number}):</span>
                      <div style={{ fontStyle: 'italic', marginTop: '2px', color: 'rgba(255,255,255,0.85)' }}>
                        "{r.citations[0].excerpt}"
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div>
                {statusBadge}
              </div>

            </div>
          );
        })}
      </div>

    </div>
  );
}
