import React from 'react';
import { Clock, ShieldCheck } from 'lucide-react';

export default function AuditLogViewer({ auditTrail }) {
  if (!auditTrail) return null;

  return (
    <div className="glass-panel" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Clock size={16} color="var(--cyan)" />
          Agent Audit Trail & State Log ({auditTrail.length} Entries)
        </h3>
        <span className="badge badge-cyan">Auditable Event Stream</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {auditTrail.map((entry, idx) => (
          <div key={idx} style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid var(--border-color)',
            borderRadius: '6px',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            fontSize: '0.8rem'
          }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.73rem', color: 'var(--text-muted)', minWidth: '130px' }}>
              {entry.timestamp ? entry.timestamp.substring(11, 19) : ''}
            </span>

            <span className="badge badge-indigo" style={{ minWidth: '140px', justifyContent: 'center' }}>
              {entry.stage}
            </span>

            <span style={{ color: '#cbd5e1', flex: 1 }}>
              {entry.summary}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
