import React, { useEffect, useMemo } from 'react';
import { X, FileText, AlertTriangle, CheckCircle, XCircle, Clock } from 'lucide-react';

function statusMeta(status) {
  if (status === 'pending_human_review') {
    return { label: 'HITL Review', badge: 'badge-amber', Icon: AlertTriangle, color: 'var(--amber)' };
  }
  if (status === 'resolved_approved') {
    return { label: 'Approved', badge: 'badge-emerald', Icon: CheckCircle, color: 'var(--emerald)' };
  }
  if (status === 'resolved_rejected') {
    return { label: 'Rejected', badge: 'badge-rose', Icon: XCircle, color: 'var(--rose)' };
  }
  return { label: (status || 'Unknown').replace(/_/g, ' '), badge: 'badge-indigo', Icon: Clock, color: 'var(--cyan)' };
}

function formatAmount(amount) {
  if (amount == null || Number.isNaN(Number(amount))) return '—';
  return `$${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function ClaimsQueueDrawer({ open, mode = 'all', claims = [], onClose, onSelectClaim }) {
  const filtered = useMemo(() => {
    const list = mode === 'hitl'
      ? claims.filter((c) => c.status === 'pending_human_review')
      : [...claims];

    return list.sort((a, b) => {
      const aTime = a.updated_at || a.created_at || '';
      const bTime = b.updated_at || b.created_at || '';
      return bTime.localeCompare(aTime);
    });
  }, [claims, mode]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const title = mode === 'hitl' ? 'HITL Exception Queue' : 'Claims Processed';
  const subtitle = mode === 'hitl'
    ? 'Claims halted for caseworker sign-off'
    : 'All persisted workflow claims';

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(3, 7, 18, 0.72)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        justifyContent: 'flex-end'
      }}
    >
      <aside
        className="glass-panel"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(440px, 100vw)',
          height: '100%',
          borderRadius: 0,
          borderTop: 0,
          borderBottom: 0,
          borderRight: 0,
          display: 'flex',
          flexDirection: 'column',
          background: 'rgba(11, 15, 25, 0.96)'
        }}
      >
        <div style={{
          padding: '20px 22px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '12px'
        }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              {mode === 'hitl' ? <AlertTriangle size={18} color="var(--amber)" /> : <FileText size={18} color="var(--primary)" />}
              {title}
            </h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              {subtitle} · {filtered.length} shown
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close claims queue"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              width: '34px',
              height: '34px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: 'var(--text-muted)'
            }}
          >
            <X size={16} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '14px' }}>
          {filtered.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '48px 20px',
              color: 'var(--text-muted)',
              fontSize: '0.85rem',
              border: '1px dashed var(--border-color)',
              borderRadius: '10px'
            }}>
              {mode === 'hitl' ? 'No claims currently awaiting sign-off.' : 'No processed claims found yet.'}
            </div>
          ) : (
            filtered.map((claim) => {
              const meta = statusMeta(claim.status);
              const entities = claim.extracted_entities || {};
              return (
                <button
                  key={claim.claim_id}
                  onClick={() => onSelectClaim(claim)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '10px',
                    padding: '14px',
                    marginBottom: '10px',
                    cursor: 'pointer',
                    color: 'inherit'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border-accent)';
                    e.currentTarget.style.background = 'rgba(99, 102, 241, 0.08)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border-color)';
                    e.currentTarget.style.background = 'rgba(255,255,255,0.02)';
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', marginBottom: '8px' }}>
                    <strong style={{ fontSize: '0.88rem', color: '#fff', fontFamily: 'var(--font-mono)' }}>
                      {claim.claim_id}
                    </strong>
                    <span className={`badge ${meta.badge}`} style={{ flexShrink: 0 }}>
                      <meta.Icon size={11} />
                      {meta.label}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.86rem', color: '#e5e7eb', fontWeight: 600, marginBottom: '4px' }}>
                    {entities.claimant_name || 'Unknown claimant'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                    <span>{entities.policy_number || 'No policy'}</span>
                    <span style={{ color: meta.color, fontWeight: 700 }}>{formatAmount(entities.claim_amount)}</span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </aside>
    </div>
  );
}
