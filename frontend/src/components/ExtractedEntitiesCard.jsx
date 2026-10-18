import React from 'react';
import { Cpu, AlertTriangle, CheckCircle2, User, FileCheck, DollarSign, Calendar, Building, Activity } from 'lucide-react';

export default function ExtractedEntitiesCard({ state }) {
  if (!state) return null;
  const { extracted_entities: entities, extraction_confidence: conf, extraction_warnings: warnings } = state;

  const confPercent = Math.round((conf || 1) * 100);
  let confColor = 'var(--emerald)';
  if (confPercent < 60) confColor = 'var(--rose)';
  else if (confPercent < 85) confColor = 'var(--amber)';

  return (
    <div className="glass-panel" style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      
      {/* Header with Confidence Gauge */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <h3 style={{ fontSize: '0.9rem', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Cpu size={16} color="var(--cyan)" />
          Extracted Entity Breakdown
        </h3>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(0,0,0,0.3)', padding: '4px 10px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Confidence:</span>
          <span style={{ fontSize: '0.85rem', fontWeight: '700', color: confColor }}>{confPercent}%</span>
        </div>
      </div>

      {/* Warnings Banner if any */}
      {warnings && warnings.length > 0 && (
        <div style={{ background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px', padding: '10px 12px', marginBottom: '14px' }}>
          <div style={{ fontSize: '0.78rem', fontWeight: '700', color: 'var(--amber)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
            <AlertTriangle size={14} /> Extraction Ambiguity Warnings ({warnings.length}):
          </div>
          {warnings.map((w, idx) => (
            <div key={idx} style={{ fontSize: '0.73rem', color: '#fef3c7', marginLeft: '20px', listStyleType: 'disc' }}>
              • {w}
            </div>
          ))}
        </div>
      )}

      {/* Grid of Key Fields */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginBottom: '16px' }}>
        
        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <User size={12} /> Claimant Name
          </div>
          <div style={{ fontSize: '0.9rem', fontWeight: '700', color: entities.claimant_name ? '#fff' : 'var(--rose)' }}>
            {entities.claimant_name || 'Missing / Unextracted'}
          </div>
        </div>

        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <FileCheck size={12} /> Policy Number
          </div>
          <div style={{ fontSize: '0.9rem', fontWeight: '700', color: entities.policy_number ? '#fff' : 'var(--rose)' }}>
            {entities.policy_number || 'Missing / Invalid'}
          </div>
        </div>

        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <DollarSign size={12} /> Total Claim Amount
          </div>
          <div style={{ fontSize: '0.95rem', fontWeight: '800', color: entities.claim_amount > 10000 ? 'var(--amber)' : 'var(--emerald)' }}>
            ${entities.claim_amount ? entities.claim_amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) : '0.00'}
          </div>
        </div>

        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Calendar size={12} /> Service Date
          </div>
          <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#fff' }}>
            {entities.date_of_service || 'N/A'}
          </div>
        </div>

        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', gridColumn: 'span 2' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Building size={12} /> Healthcare Provider
          </div>
          <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#fff' }}>
            {entities.provider_name || 'N/A'}
          </div>
        </div>

      </div>

      {/* Itemized Breakdown Table if present */}
      {entities.line_items && entities.line_items.length > 0 && (
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
            Itemized Line Item Charges ({entities.line_items.length})
          </div>
          <div style={{ background: '#090d16', border: '1px solid var(--border-color)', borderRadius: '6px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
              <thead>
                <tr style={{ background: 'rgba(255,255,255,0.04)', color: 'var(--text-muted)', textAlign: 'left' }}>
                  <th style={{ padding: '6px 10px' }}>Description</th>
                  <th style={{ padding: '6px 10px', textAlign: 'right' }}>Amount</th>
                </tr>
              </thead>
              <tbody>
                {entities.line_items.map((item, i) => (
                  <tr key={i} style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '6px 10px', color: '#cbd5e1' }}>{item.description}</td>
                    <td style={{ padding: '6px 10px', textAlign: 'right', fontWeight: '600', color: '#fff' }}>
                      ${item.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
