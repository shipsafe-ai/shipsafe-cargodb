"use client";
import { useState, useEffect } from "react";
import { fetchPending, approveDecision } from "@/lib/api";

interface PendingDecision {
  decision_id: string;
  candidate_decision: {
    decision_text: string;
    recommended_action: string;
    confidence: number;
    decision_type: string;
    rationale?: string;
    decision_thinking?: string;
    key_precedent?: string | null;
  };
  similar_decisions: Array<{ decision_id: string; score: number }>;
  verdict: {
    risk_level: string;
    concerns: string[];
    approved: boolean;
    reasoning?: string;
    thinking?: string;
  };
}

const RISK_COLOR: Record<string, string> = {
  LOW: "text-risk-low border-risk-low/30 bg-risk-low/10",
  MEDIUM: "text-risk-medium border-risk-medium/30 bg-risk-medium/10",
  HIGH: "text-risk-high border-risk-high/30 bg-risk-high/10",
  CRITICAL: "text-risk-critical border-risk-critical/30 bg-risk-critical/10",
};

export default function PendingApprovals() {
  const [pending, setPending] = useState<PendingDecision[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);
  const [approver, setApprover] = useState("operator");

  const load = () => {
    setLoading(true);
    fetchPending()
      .then((d) => setPending(d.pending ?? []))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const act = async (decisionId: string, approved: boolean) => {
    setActing(decisionId);
    try {
      await approveDecision(decisionId, approved, approver);
      load();
    } finally {
      setActing(null);
    }
  };

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-mono text-muted uppercase tracking-widest">
          Pending Approvals
        </h2>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-muted">Approver:</span>
          <input
            value={approver}
            onChange={(e) => setApprover(e.target.value)}
            className="bg-bg-elevated border border-border rounded px-2 py-1 text-xs font-mono text-text-primary w-32 focus:outline-none focus:border-cargo-accent"
          />
          <button
            onClick={load}
            className="text-xs font-mono text-muted hover:text-text-secondary px-2 py-1 border border-border rounded"
          >
            Refresh
          </button>
        </div>
      </div>

      {loading && <div className="text-sm text-muted font-mono">Loading...</div>}

      {!loading && pending.length === 0 && (
        <div className="bg-bg-surface border border-border rounded p-6 text-center text-muted font-mono text-sm">
          No decisions pending approval
        </div>
      )}

      <div className="space-y-3">
        {pending.map((p) => {
          const riskClass = RISK_COLOR[p.verdict?.risk_level] ?? RISK_COLOR.MEDIUM;
          return (
            <div key={p.decision_id} className="bg-bg-surface border border-border rounded p-4">
              <div className="flex items-start justify-between gap-4 mb-3">
                <span className="font-mono text-xs text-cargo-accent">{p.decision_id}</span>
                <span className={`text-xs font-mono px-2 py-0.5 border rounded ${riskClass}`}>
                  {p.verdict?.risk_level ?? "UNKNOWN"}
                </span>
              </div>

              <p className="text-sm text-text-primary font-sans mb-2">
                {p.candidate_decision?.decision_text}
              </p>

              <div className="flex gap-4 mb-3 text-xs font-mono text-muted">
                <span>Action: <span className="text-text-secondary">{p.candidate_decision?.recommended_action}</span></span>
                <span>Confidence: <span className="text-text-secondary">{((p.candidate_decision?.confidence ?? 0) * 100).toFixed(0)}%</span></span>
                <span>Similar: <span className="text-text-secondary">{p.similar_decisions?.length ?? 0}</span></span>
              </div>

              {/* Gemini DecisionReasoner — the brain's rationale + chain-of-thought */}
              {p.candidate_decision?.rationale && (
                <div className="mb-3 border-l-2 border-cargo-accent/40 pl-3">
                  <span className="text-xs font-mono text-cargo-accent uppercase tracking-widest">
                    Gemini reasoning{p.candidate_decision?.key_precedent ? ` · precedent ${p.candidate_decision.key_precedent}` : ""}
                  </span>
                  <p className="mt-1 text-xs text-text-secondary font-sans leading-relaxed">
                    {p.candidate_decision.rationale}
                  </p>
                  {p.candidate_decision?.decision_thinking && (
                    <details className="mt-1.5">
                      <summary className="text-[11px] font-mono text-muted cursor-pointer select-none hover:text-cargo-accent">
                        Gemini thinking
                      </summary>
                      <pre className="mt-1 text-[11px] text-muted bg-bg-base border border-border rounded p-2 whitespace-pre-wrap max-h-48 overflow-auto">
{p.candidate_decision.decision_thinking}
                      </pre>
                    </details>
                  )}
                </div>
              )}

              {/* Gemini Critic — adversarial reasoning */}
              {p.verdict?.reasoning && (
                <div className="mb-3">
                  <span className="text-xs font-mono text-muted uppercase tracking-widest">Critic (Gemini)</span>
                  <p className="mt-1 text-xs text-text-secondary font-sans leading-relaxed">
                    {p.verdict.reasoning}
                  </p>
                  {p.verdict?.thinking && (
                    <details className="mt-1.5">
                      <summary className="text-[11px] font-mono text-muted cursor-pointer select-none hover:text-cargo-accent">
                        Critic thinking
                      </summary>
                      <pre className="mt-1 text-[11px] text-muted bg-bg-base border border-border rounded p-2 whitespace-pre-wrap max-h-48 overflow-auto">
{p.verdict.thinking}
                      </pre>
                    </details>
                  )}
                </div>
              )}

              {p.verdict?.concerns?.length > 0 && (
                <div className="mb-3">
                  <span className="text-xs font-mono text-muted uppercase tracking-widest">Concerns</span>
                  <ul className="mt-1 space-y-0.5">
                    {p.verdict.concerns.map((c, i) => (
                      <li key={i} className="text-xs font-mono text-risk-medium">• {c}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex gap-2 pt-2 border-t border-border">
                <button
                  onClick={() => act(p.decision_id, true)}
                  disabled={acting === p.decision_id}
                  className="px-3 py-1.5 bg-cargo-accent text-bg-base text-xs font-mono rounded hover:bg-cargo-accent-dim disabled:opacity-40 transition-colors"
                >
                  Approve
                </button>
                <button
                  onClick={() => act(p.decision_id, false)}
                  disabled={acting === p.decision_id}
                  className="px-3 py-1.5 bg-bg-elevated border border-border text-xs font-mono text-risk-high rounded hover:border-risk-high disabled:opacity-40 transition-colors"
                >
                  Reject
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
