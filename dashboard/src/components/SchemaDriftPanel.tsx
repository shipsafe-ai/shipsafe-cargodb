"use client";
import { useState, useEffect } from "react";

interface SchemaField {
  name: string;
  type: string;
  coverage: number;
  drift_risk: boolean;
}

interface SchemaReport {
  collection: string;
  fields: SchemaField[];
  total_fields: number;
  drift_fields: number;
}

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

export default function SchemaDriftPanel() {
  const [report, setReport] = useState<SchemaReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${BASE}/schema`)
      .then((r) => r.json())
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-2xl">
      <h2 className="text-sm font-mono text-muted uppercase tracking-widest mb-4">
        Schema Drift
      </h2>

      {loading && <div className="text-sm text-muted font-mono">Analyzing schema...</div>}
      {error && <div className="text-sm text-risk-high font-mono">{error}</div>}

      {report && (
        <>
          <div className="flex gap-6 mb-4">
            <Stat label="Collection" value={report.collection} />
            <Stat label="Fields" value={String(report.total_fields)} />
            <Stat
              label="Drift Risk"
              value={String(report.drift_fields)}
              highlight={report.drift_fields > 0}
            />
          </div>

          <div className="bg-bg-surface border border-border rounded overflow-hidden">
            <div className="grid grid-cols-4 px-4 py-2 border-b border-border text-xs font-mono text-muted uppercase tracking-widest">
              <span>Field</span>
              <span>Type</span>
              <span>Coverage</span>
              <span>Risk</span>
            </div>
            {report.fields.map((f) => (
              <div
                key={f.name}
                className={`grid grid-cols-4 px-4 py-2.5 border-b border-border text-sm ${
                  f.drift_risk ? "bg-risk-high/5" : ""
                }`}
              >
                <span className="font-mono text-text-primary">{f.name}</span>
                <span className="font-mono text-text-secondary">{f.type}</span>
                <span className="font-mono">
                  <span
                    className={
                      f.coverage >= 0.8
                        ? "text-risk-low"
                        : f.coverage >= 0.5
                        ? "text-risk-medium"
                        : "text-risk-high"
                    }
                  >
                    {(f.coverage * 100).toFixed(0)}%
                  </span>
                </span>
                <span>
                  {f.drift_risk ? (
                    <span className="text-xs font-mono text-risk-high">DRIFT</span>
                  ) : (
                    <span className="text-xs font-mono text-risk-low">OK</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="bg-bg-surface border border-border rounded px-4 py-3">
      <div className="text-xs font-mono text-muted uppercase tracking-widest mb-1">{label}</div>
      <div className={`text-lg font-mono ${highlight ? "text-risk-high" : "text-text-primary"}`}>
        {value}
      </div>
    </div>
  );
}
