import React, { useState, useEffect, useRef } from 'react';
import { FileText, Cpu, CheckSquare, GitBranch, AlertOctagon, FileCheck, ArrowRight, RefreshCw, Zap } from 'lucide-react';

export default function AgentPipelineVisualizer({ state, backendEvent }) {
  if (!state) return null;

  const [replayStepIdx, setReplayStepIdx] = useState(5);
  const [isReplaying, setIsReplaying] = useState(false);
  const prevClaimIdRef = useRef(null);

  // Replay animation function
  const startReplay = () => {
    setIsReplaying(true);
    setReplayStepIdx(0);
    
    let step = 0;
    const interval = setInterval(() => {
      step += 1;
      if (step <= 5) {
        setReplayStepIdx(step);
      } else {
        clearInterval(interval);
        setIsReplaying(false);
      }
    }, 700);
  };

  // Determine current active step and status from live backend stream OR replay
  const isLiveBackendActive = backendEvent && !backendEvent.is_completed;
  const activeStepIdx = isLiveBackendActive 
    ? backendEvent.step_index 
    : (isReplaying ? replayStepIdx : 5);

  const steps = [
    { 
      id: 'ingest', 
      name: 'Document Ingestion', 
      icon: FileText, 
      desc: 'PDF / Text Ingest',
      activeText: (backendEvent?.step_id === 'ingest' && backendEvent.message) || 'Ingesting & Parsing...'
    },
    { 
      id: 'extract', 
      name: 'Entity Extraction', 
      icon: Cpu, 
      desc: `Confidence: ${Math.round((state.extraction_confidence || 1) * 100)}%`,
      activeText: (backendEvent?.step_id === 'extract' && backendEvent.message) || 'Extracting Schema Fields...'
    },
    { 
      id: 'validate', 
      name: 'Rules Engine', 
      icon: CheckSquare, 
      desc: `${state.validation_results?.length || 7} Rules Checked`,
      activeText: (backendEvent?.step_id === 'validate' && backendEvent.message) || 'Evaluating Rules Matrix...'
    },
    { 
      id: 'route', 
      name: 'Decision Router', 
      icon: GitBranch, 
      desc: state.decision_path ? `Path: ${state.decision_path.toUpperCase()}` : 'Evaluating Routing',
      activeText: (backendEvent?.step_id === 'route' && backendEvent.message) || 'Determining Escalation...'
    },
    { 
      id: 'hitl_or_draft', 
      name: state.status === 'pending_human_review' ? 'HITL Exception Halt' : 'Letter Synthesis', 
      icon: state.status === 'pending_human_review' ? AlertOctagon : FileCheck, 
      desc: state.status === 'pending_human_review' ? 'Awaiting Caseworker' : 'Approval/Rejection Draft',
      activeText: state.status === 'pending_human_review' ? 'HALTING WORKFLOW...' : 'Drafting Formal Letter...'
    },
    { 
      id: 'completed', 
      name: 'Resolution & Audit', 
      icon: FileCheck, 
      desc: state.status.replace('_', ' ').toUpperCase(),
      activeText: 'State Persisted & Audited'
    }
  ];

  return (
    <div className="glass-panel" style={{ padding: '20px 24px', marginBottom: '24px', position: 'relative' }}>
      
      {/* Header & Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#fff', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <GitBranch size={18} color="var(--primary)" />
            Live Backend Agent Execution Visualizer
          </h3>
          
          {isLiveBackendActive ? (
            <span className="badge badge-cyan" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Zap size={14} color="var(--cyan)" className="pulse-active" />
              BACKEND EXECUTING LIVE STEP {activeStepIdx + 1} OF 6
            </span>
          ) : isReplaying ? (
            <span className="badge badge-indigo">REPLAYING ANIMATION STEP {activeStepIdx + 1}</span>
          ) : (
            <span className="badge badge-emerald">BACKEND STREAM COMPLETE</span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={startReplay}
            disabled={isLiveBackendActive || isReplaying}
            className="btn btn-secondary"
            style={{ fontSize: '0.78rem', padding: '6px 12px', opacity: (isLiveBackendActive || isReplaying) ? 0.6 : 1 }}
          >
            <RefreshCw size={14} className={isReplaying ? 'pulse-active' : ''} />
            {isReplaying ? 'Replaying...' : 'Replay DAG Animation 🎬'}
          </button>
          
          <span className="badge badge-cyan">Claim ID: {state.claim_id}</span>
        </div>
      </div>

      {/* Animated DAG Node Track */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}>
        {steps.map((step, idx) => {
          const Icon = step.icon;
          
          const isNodeActive = (isLiveBackendActive || isReplaying) ? activeStepIdx === idx : false;
          const isNodeCompleted = (isLiveBackendActive || isReplaying) ? activeStepIdx > idx : true;
          
          let nodeBg = 'rgba(255, 255, 255, 0.04)';
          let nodeBorder = 'var(--border-color)';
          let iconColor = 'var(--text-muted)';
          let badgeText = 'PASS';
          let nodeCustomClass = '';

          if (isNodeActive) {
            nodeCustomClass = 'dag-node-active';
            nodeBg = 'rgba(99, 102, 241, 0.25)';
            nodeBorder = 'var(--cyan)';
            iconColor = 'var(--cyan)';
          } else if (isNodeCompleted) {
            if (step.id === 'hitl_or_draft' && state.status === 'pending_human_review') {
              nodeCustomClass = 'dag-node-hitl';
              nodeBg = 'rgba(245, 158, 11, 0.18)';
              nodeBorder = 'var(--amber)';
              iconColor = 'var(--amber)';
            } else if (step.id === 'completed' && state.status === 'resolved_rejected') {
              nodeBg = 'rgba(244, 63, 94, 0.15)';
              nodeBorder = 'rgba(244, 63, 94, 0.4)';
              iconColor = 'var(--rose)';
            } else {
              nodeBg = 'rgba(16, 185, 129, 0.12)';
              nodeBorder = 'rgba(16, 185, 129, 0.4)';
              iconColor = 'var(--emerald)';
            }
          }

          return (
            <React.Fragment key={step.id}>
              <div 
                className={nodeCustomClass}
                style={{
                  flex: 1,
                  background: nodeBg,
                  border: `1px solid ${nodeBorder}`,
                  borderRadius: '10px',
                  padding: '12px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  transition: 'all 0.4s ease',
                  position: 'relative'
                }}
              >
                {/* Laser scan overlay beam when node is actively processing */}
                {isNodeActive && <div className="scan-beam-overlay" />}

                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '8px',
                  background: isNodeActive ? 'rgba(6, 182, 212, 0.2)' : 'rgba(0,0,0,0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <Icon size={20} color={iconColor} className={isNodeActive ? 'pulse-active' : ''} />
                </div>

                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {step.name}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: isNodeActive ? 'var(--cyan)' : 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {isNodeActive ? step.activeText : step.desc}
                  </div>
                </div>
              </div>

              {/* Connecting Laser Arrow */}
              {idx < steps.length - 1 && (
                <div style={{ padding: '0 6px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <ArrowRight 
                    size={18} 
                    color={((isLiveBackendActive || isReplaying) ? activeStepIdx > idx : true) ? 'var(--emerald)' : 'var(--text-muted)'} 
                    style={{
                      opacity: ((isLiveBackendActive || isReplaying) ? activeStepIdx >= idx : true) ? 1 : 0.3,
                      transition: 'all 0.4s ease'
                    }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
