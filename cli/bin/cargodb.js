#!/usr/bin/env node
const [,, cmd, ...args] = process.argv;
const BASE = "https://cargodb-o34wppiwiq-uc.a.run.app";

const commands = {
  health: async () => {
    const r = await fetch(`${BASE}/health`).catch(() => null);
    if (!r) return console.error("✗ Cannot reach cargodb agent");
    const d = await r.json();
    console.log(`✓ cargodb ${d.status ?? "ok"} — ${BASE}`);
  },
  demo: async () => {
    console.log("▶ Running Hormuz Crisis demo on cargodb...");
    const r = await fetch(`${BASE}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: "hormuz" }),
    }).catch(() => null);
    if (!r) return console.error("✗ Demo failed — is cargodb agent running?");
    const d = await r.json();
    console.log(JSON.stringify(d, null, 2));
  },
  init: async () => {
    console.log(`
ShipSafe Cargodb — powered by MongoDB Atlas
${"-".repeat(48)}
Agent URL : ${BASE}
Dashboard : https://cargodb-dashboard-336382452417.us-central1.run.app

To connect to your own data:
  1. Set credentials in GCP Secret Manager (project: shipsafe-ai)
  2. Run: npx shipsafe-cargodb demo

Health check:`);
    await commands.health();
  },
};

const fn = commands[cmd];
if (!fn) {
  console.log("Usage: npx shipsafe-cargodb <init|demo|health>");
  process.exit(1);
}
fn().catch(e => { console.error(e.message); process.exit(1); });
