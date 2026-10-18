import React from 'react';
import { ShieldCheck, Activity, AlertTriangle, FileText } from 'lucide-react';

export default function Header({ claims, onOpenClaims, onOpenHitlQueue }) {
  const totalProcessed = claims.length;
  const pendingHitl = claims.filter(c => c.status === 'pending_human_review').length;

  const metricTileStyle = (activeAccent) => ({
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 16px',
    background: activeAccent ? 'rgba(245, 158, 11, 0.1)' : 'rgba(255,255,255,0.03)',
    borderRadius: '8px',
    border: activeAccent ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid var(--border-color)',
    cursor: 'pointer',
    transition: 'border-color 0.15s ease, background 0.15s ease'
  });

  return (
    <header className="glass-panel" style={{ borderRadius: 0, borderTop: 0, borderLeft: 0, borderRight: 0, padding: '16px 32px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        
        {/* Brand & Agent Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 16px rgba(99, 102, 241, 0.4)'
          }}>
            <ShieldCheck size={26} color="#fff" />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ fontSize: '1.25rem', fontWeight: '800', background: 'linear-gradient(90deg, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                ClaimsPulse AI
              </h1>
              <span className="badge badge-indigo">Autonomous Enterprise Workflow Agent</span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Healthcare & Insurance Claim Automation System with HITL Sign-off Engine
            </p>
          </div>
        </div>

        {/* Live Metrics */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 16px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <Activity size={18} color="var(--cyan)" />
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Agent Status</div>
              <div style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--emerald)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }} className="pulse-active"></span>
                ACTIVE & LISTENING
              </div>
            </div>
          </div>

          <div
            role="button"
            tabIndex={0}
            title="View all processed claims"
            onClick={onOpenClaims}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onOpenClaims(); }}
            style={metricTileStyle(false)}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--border-accent)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border-color)'; }}
          >
            <FileText size={18} color="var(--primary)" />
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Claims Processed</div>
              <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#fff' }}>{totalProcessed} Claims</div>
            </div>
          </div>

          <div
            role="button"
            tabIndex={0}
            title="View HITL exception queue"
            onClick={onOpenHitlQueue}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onOpenHitlQueue(); }}
            style={metricTileStyle(pendingHitl > 0)}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = pendingHitl > 0 ? 'rgba(245, 158, 11, 0.7)' : 'var(--border-accent)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = pendingHitl > 0 ? 'rgba(245, 158, 11, 0.4)' : 'var(--border-color)';
            }}
          >
            <AlertTriangle size={18} color={pendingHitl > 0 ? 'var(--amber)' : 'var(--text-muted)'} />
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>HITL Exception Queue</div>
              <div style={{ fontSize: '0.85rem', fontWeight: '700', color: pendingHitl > 0 ? 'var(--amber)' : '#fff' }}>
                {pendingHitl} Requiring Sign-off
              </div>
            </div>
          </div>

        </div>

      </div>
    </header>
  );
}
