import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ClaimSelector from './components/ClaimSelector';
import AgentPipelineVisualizer from './components/AgentPipelineVisualizer';
import DocumentViewer from './components/DocumentViewer';
import ExtractedEntitiesCard from './components/ExtractedEntitiesCard';
import BusinessRulesMatrix from './components/BusinessRulesMatrix';
import HITLReviewModal from './components/HITLReviewModal';
import DecisionLetterPreview from './components/DecisionLetterPreview';
import AuditLogViewer from './components/AuditLogViewer';
import ClaimsQueueDrawer from './components/ClaimsQueueDrawer';

export default function App() {
  const [samples, setSamples] = useState([]);
  const [claims, setClaims] = useState([]);
  const [activeState, setActiveState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [queueOpen, setQueueOpen] = useState(false);
  const [queueMode, setQueueMode] = useState('all'); // 'all' | 'hitl'

  useEffect(() => {
    fetchSamples();
    fetchClaims();
  }, []);

  const fetchSamples = async () => {
    try {
      const res = await fetch('/api/samples');
      if (res.ok) {
        const data = await res.json();
        setSamples(data);
      }
    } catch (e) {
      console.error("Failed to load samples", e);
    }
  };

  const fetchClaims = async () => {
    try {
      const res = await fetch('/api/claims');
      if (res.ok) {
        const data = await res.json();
        setClaims(data);
      }
    } catch (e) {
      console.error("Failed to load claims", e);
    }
  };

  const [activeBackendEvent, setActiveBackendEvent] = useState(null);

  const handleRunClaim = async (rawText) => {
    setLoading(true);
    setActiveBackendEvent(null);
    try {
      const res = await fetch('/api/workflow/process-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: rawText })
      });

      if (!res.ok) {
        throw new Error("Backend agent streaming failed.");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.replace('data: ', '').trim();
            if (jsonStr) {
              try {
                const payload = JSON.parse(jsonStr);
                if (payload.state) {
                  setActiveState(payload.state);
                }
                setActiveBackendEvent({
                  step_index: payload.step_index,
                  step_id: payload.step_id,
                  message: payload.message,
                  is_completed: payload.event === 'completed'
                });
              } catch (e) {
                console.error("Error parsing stream chunk", e);
              }
            }
          }
        }
      }

      fetchClaims();
    } catch (e) {
      console.error("Error executing workflow stream", e);
      // Fallback to standard process endpoint if stream unsupported
      try {
        const res = await fetch('/api/workflow/process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ raw_text: rawText })
        });
        if (res.ok) {
          const newState = await res.json();
          setActiveState(newState);
          fetchClaims();
        }
      } catch (err) {
        alert("Execution error: " + err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResumeHITL = async (claimId, action, notes, signature) => {
    setLoading(true);
    try {
      const res = await fetch('/api/workflow/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claim_id: claimId,
          action: action,
          notes: notes,
          caseworker_signature: signature
        })
      });
      if (res.ok) {
        const updatedState = await res.json();
        setActiveState(updatedState);
        fetchClaims();
      } else {
        const err = await res.json();
        alert("Failed to resume claim: " + (err.detail || 'Unknown error'));
      }
    } catch (e) {
      console.error("Error resuming workflow", e);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSample = () => {
    setActiveState(null);
    setActiveBackendEvent(null);
  };

  const openClaimsQueue = (mode) => {
    setQueueMode(mode);
    setQueueOpen(true);
  };

  const handleSelectQueuedClaim = async (claim) => {
    setQueueOpen(false);
    setLoading(true);
    setActiveBackendEvent(null);
    try {
      const res = await fetch(`/api/claims/${claim.claim_id}`);
      if (res.ok) {
        const fresh = await res.json();
        setActiveState(fresh);
      } else {
        setActiveState(claim);
      }
      // Treat historical claims as already completed so downstream panels unlock immediately.
      setActiveBackendEvent({
        step_index: 5,
        step_id: 'completion',
        message: 'Loaded persisted claim from queue',
        is_completed: true
      });
    } catch (e) {
      console.error('Failed to load claim from queue', e);
      setActiveState(claim);
      setActiveBackendEvent({
        step_index: 5,
        step_id: 'completion',
        message: 'Loaded persisted claim from queue',
        is_completed: true
      });
    } finally {
      setLoading(false);
    }
  };

  const showDownstreamResults = activeState && (activeBackendEvent ? activeBackendEvent.is_completed : !loading);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-dark)', pb: '40px' }}>
      <Header
        claims={claims}
        onOpenClaims={() => openClaimsQueue('all')}
        onOpenHitlQueue={() => openClaimsQueue('hitl')}
      />

      <ClaimsQueueDrawer
        open={queueOpen}
        mode={queueMode}
        claims={claims}
        onClose={() => setQueueOpen(false)}
        onSelectClaim={handleSelectQueuedClaim}
      />

      <main style={{ maxWidth: '1440px', margin: '0 auto', padding: '0 24px 40px 24px' }}>
        
        {/* Claim Selector / Document Ingestion */}
        <ClaimSelector samples={samples} onRunClaim={handleRunClaim} onSelectSample={handleSelectSample} loading={loading} />

        {/* Clean Ready State Banner before Run Agents is clicked */}
        {!activeState && !loading && (
          <div className="glass-panel" style={{ padding: '48px 32px', textAlign: 'center', marginBottom: '24px' }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '16px',
              background: 'rgba(99, 102, 241, 0.15)',
              border: '1px solid var(--border-accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px auto'
            }}>
              <span style={{ fontSize: '1.8rem' }}>🚀</span>
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#fff', marginBottom: '8px' }}>
              Ready to Run Autonomous Claims Agents
            </h3>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', maxWidth: '560px', margin: '0 auto 20px auto' }}>
              Select a preloaded scenario card above (or paste custom claim text) and click <strong style={{ color: 'var(--cyan)' }}>"Run Agents"</strong> to observe live multi-step agent execution, extraction, and rule evaluation.
            </p>
          </div>
        )}

        {/* Active Pipeline Visualizer */}
        {activeState && <AgentPipelineVisualizer state={activeState} backendEvent={activeBackendEvent} />}

        {/* Live Streaming Execution Indicator while DAG is running */}
        {activeState && !showDownstreamResults && (
          <div className="glass-panel" style={{ padding: '24px', textAlign: 'center', marginBottom: '24px', border: '1px solid var(--primary)' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', color: 'var(--cyan)', fontWeight: '600', fontSize: '0.9rem' }}>
              <span className="pulse-active" style={{ fontSize: '1.2rem' }}>📡</span>
              Backend Agents Executing Real-Time Workflow... Detailed Entities & Rules Matrix will unlock upon completion.
            </div>
          </div>
        )}

        {/* Downstream Sections - Only Render AFTER DAG Visualizer Execution Completes */}
        {showDownstreamResults && (
          <div className="fade-in-section">
            
            {/* HITL Exception Review Drawer (if Halted) */}
            {activeState.status === 'pending_human_review' && (
              <HITLReviewModal state={activeState} onResume={handleResumeHITL} />
            )}

            {/* Dual Split Pane (Document vs Extracted Entities) */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
              <DocumentViewer rawText={activeState.raw_text} />
              <ExtractedEntitiesCard state={activeState} />
            </div>

            {/* Business Rules Matrix */}
            {activeState.validation_results && (
              <BusinessRulesMatrix validationResults={activeState.validation_results} />
            )}

            {/* Formal Decision Letter Preview */}
            {activeState.letter_draft && (
              <DecisionLetterPreview state={activeState} />
            )}

            {/* Audit Trail Timeline Log */}
            {activeState.audit_trail && (
              <AuditLogViewer auditTrail={activeState.audit_trail} />
            )}
          </div>
        )}

      </main>
    </div>
  );
}
