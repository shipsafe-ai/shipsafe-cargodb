"use client";
import { useState, useEffect } from "react";
import { fetchDecisions } from "@/lib/api";

interface Decision {
  decision_id: string;
  decision_type: string;
  decision_text: string;
  recommended_action?: string;
  confidence?: number;
  timestamp?: string;
  score?: number;
  outcome?: string;
}

function RiskBadge({ confidence }: { confidence?: number }) {
  if (confidence === undefined) return null;
  const level = confidence >= 0.8 ? "low" : confidence >= 0.6 ? "medium" : "high";
  const colors = {
    low: "bg-risk-low/10 text-risk-low border-risk-low/30",
    medium: "bg-risk-medium/10 text-risk-medium border-risk-medium/30",
    high: "bg-risk-high/10 text-risk-high border-risk-high/30",
  };
  return (
    <span className={`text-xs font-mono px-2 py-0.5 border rounded ${colors[level]}`}>
      {(confidence * 100).toFixed(0)}%
    </span>
  );
}

export default function MemoryBrowser() {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Decision | null>(null);

  useEffect(() => {
    fetchDecisions(20)
      .then((d) => setDecisions(d.decisions ?? []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex gap-4 h-[calc(100vh-160px)]">
      {/* List */}
      <div className="w-96 flex-shrink-0 bg-bg-surface border border-border rounded overflow-y-auto">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <span className="text-xs font-mono text-muted uppercase tracking-widest">Decisions</span>
          <span className="text-xs font-mono text-cargo-accent">{decisions.length}</span>
        </div>
        {loading && (
          <div className="p-4 text-sm text-muted font-mono">Loading...</div>
        )}
        {error && (
          <div className="p-4 text-sm text-risk-high font-mono">{error}</div>
        )}
        {decisions.map((d) => (
          <button
            key={d.decision_id}
            onClick={() => setSelected(d)}
            className={`w-full text-left px-4 py-3 border-b border-border hover:bg-bg-elevated transition-colors ${
              selected?.decision_id === d.decision_id ? "bg-cargo-accent-muted border-l-2 border-l-cargo-accent" : ""
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs font-mono text-cargo-accent truncate">{d.decision_id}</span>
              <RiskBadge confidence={d.confidence ?? d.score} />
            </div>
            <p className="text-xs text-text-secondary mt-1 line-clamp-2 font-sans">{d.decision_text}</p>
            <span className="text-xs text-muted font-mono mt-1 block">{d.decision_type}</span>
          </button>
        ))}
        {!loading && decisions.length === 0 && !error && (
          <div className="p-4 text-sm text-muted font-mono">No decisions stored yet.</div>
        )}
      </div>

      {/* Detail */}
      <div className="flex-1 bg-bg-surface border border-border rounded overflow-y-auto">
        {selected ? (
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <span className="font-mono text-sm text-cargo-accent">{selected.decision_id}</span>
              <RiskBadge confidence={selected.confidence ?? selected.score} />
            </div>
            <Field label="Type" value={selected.decision_type} />
            <Field label="Decision" value={selected.decision_text} />
            {selected.recommended_action && (
              <Field label="Action" value={selected.recommended_action} />
            )}
            {selected.outcome && <Field label="Outcome" value={selected.outcome} />}
            {selected.timestamp && <Field label="Timestamp" value={selected.timestamp} mono />}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-muted font-mono text-sm">
            Select a decision
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="mb-4">
      <span className="text-xs font-mono text-muted uppercase tracking-widest block mb-1">{label}</span>
      <p className={`text-sm text-text-primary ${mono ? "font-mono" : "font-sans"}`}>{value}</p>
    </div>
  );
}
