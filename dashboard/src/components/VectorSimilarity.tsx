"use client";
import { useState } from "react";
import { fetchSimilar } from "@/lib/api";

interface SimilarResult {
  decision_id: string;
  decision_text: string;
  decision_type: string;
  score: number;
  outcome?: string;
  timestamp?: string;
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "#10B981" : pct >= 60 ? "#F59E0B" : "#EF4444";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-bg-elevated rounded">
        <div
          className="h-1 rounded"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs font-mono w-10 text-right" style={{ color }}>
        {pct}%
      </span>
    </div>
  );
}

export default function VectorSimilarity() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [results, setResults] = useState<SimilarResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSimilar(query, type || undefined, 10);
      setResults(data.decisions ?? []);
      setSearched(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h2 className="text-sm font-mono text-muted uppercase tracking-widest mb-4">
          Vector Similarity Search
        </h2>
        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="Hormuz closure, reroute options..."
            className="flex-1 bg-bg-elevated border border-border rounded px-3 py-2 text-sm font-sans text-text-primary placeholder-muted focus:outline-none focus:border-cargo-accent"
          />
          <input
            value={type}
            onChange={(e) => setType(e.target.value)}
            placeholder="Type filter (optional)"
            className="w-44 bg-bg-elevated border border-border rounded px-3 py-2 text-sm font-mono text-text-primary placeholder-muted focus:outline-none focus:border-cargo-accent"
          />
          <button
            onClick={search}
            disabled={loading || !query.trim()}
            className="px-4 py-2 bg-cargo-accent text-bg-base font-mono text-sm rounded hover:bg-cargo-accent-dim disabled:opacity-40 transition-colors"
          >
            {loading ? "..." : "Search"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-risk-high/10 border border-risk-high/30 rounded p-3 text-sm text-risk-high font-mono mb-4">
          {error}
        </div>
      )}

      {searched && results.length === 0 && !loading && (
        <div className="text-muted font-mono text-sm">No similar decisions found.</div>
      )}

      <div className="space-y-2">
        {results.map((r, i) => (
          <div key={r.decision_id} className="bg-bg-surface border border-border rounded p-4">
            <div className="flex items-start justify-between gap-4 mb-2">
              <span className="font-mono text-xs text-cargo-accent">{r.decision_id}</span>
              <span className="text-xs font-mono text-muted">#{i + 1}</span>
            </div>
            <ScoreBar score={r.score} />
            <p className="text-sm text-text-primary font-sans mt-2">{r.decision_text}</p>
            <div className="flex gap-4 mt-2">
              <span className="text-xs font-mono text-muted">{r.decision_type}</span>
              {r.outcome && (
                <span className="text-xs font-mono text-cargo-accent">{r.outcome}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
