"""CargoDB CLI — init, demo, connect commands."""
import asyncio
import json
import sys
from typing import Optional

import click

API_URL_DEFAULT = "http://localhost:8080"


def _api_url(ctx: click.Context) -> str:
    return ctx.obj.get("api_url", API_URL_DEFAULT)


@click.group()
@click.option("--api-url", default=API_URL_DEFAULT, envvar="CARGODB_API_URL")
@click.pass_context
def cli(ctx: click.Context, api_url: str) -> None:
    """CargoDB — persistent semantic memory for AI agents."""
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Verify CargoDB connection and Atlas Vector Search wiring."""
    import urllib.request

    url = f"{_api_url(ctx)}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            click.echo(f"CargoDB OK — db: {data.get('db')}")
    except Exception as e:
        click.echo(f"Connection failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def demo(ctx: click.Context) -> None:
    """Run Hormuz Crisis demo scenario end-to-end."""
    asyncio.run(_run_demo(ctx))


async def _run_demo(ctx: click.Context) -> None:
    import urllib.request

    event = {
        "event_id": "evt-hormuz-demo-001",
        "event_type": "strait_closure",
        "affected_strait": "Hormuz",
        "vessels_affected": ["vessel-hormuz-01", "vessel-hormuz-02"],
        "severity": "CRITICAL",
        "timestamp": "2024-06-01T00:00:00Z",
    }

    click.echo("Hormuz Crisis event firing...")
    click.echo(f"Event: {json.dumps(event, indent=2)}\n")

    url = f"{_api_url(ctx)}/run"
    body = json.dumps(event).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
    except Exception as e:
        click.echo(f"Demo failed: {e}", err=True)
        sys.exit(1)

    click.echo(f"Decision ID: {result['decision_id']}")
    click.echo(f"Status: {result['status']}")

    similar = result.get("similar_decisions", [])
    if similar:
        click.echo(f"\nSimilar past decisions ({len(similar)}):")
        for s in similar[:3]:
            score_pct = int(s.get("score", 0) * 100)
            click.echo(f"  {s['decision_id']} — {score_pct}% similar")
            if s.get("decision_text"):
                click.echo(f"    {s['decision_text'][:80]}")
    else:
        click.echo("\nNo similar decisions found (first run).")

    verdict = result.get("verdict", {})
    risk = verdict.get("risk_level", "UNKNOWN")
    click.echo(f"\nCritic verdict: {risk}")
    if verdict.get("concerns"):
        for c in verdict["concerns"]:
            click.echo(f"  ⚠ {c}")

    click.echo(f"\nAwaiting human approval. Use: cargodb approve {result['decision_id']}")


@cli.command()
@click.argument("decision_id")
@click.option("--approve/--reject", default=True)
@click.option("--approver", default="operator", prompt="Approver name")
@click.pass_context
def approve(ctx: click.Context, decision_id: str, approve: bool, approver: str) -> None:
    """Approve or reject a pending decision."""
    import urllib.request

    payload = json.dumps({
        "decision_id": decision_id,
        "approved": approve,
        "approver": approver,
    }).encode()
    url = f"{_api_url(ctx)}/approve"
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            action = "Approved" if approve else "Rejected"
            click.echo(f"{action}: {result['decision_id']} by {result['approver']}")
    except Exception as e:
        click.echo(f"Failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option("--top-k", default=5, type=int)
@click.pass_context
def search(ctx: click.Context, query: str, top_k: int) -> None:
    """Search similar decisions by query text."""
    import urllib.request

    payload = json.dumps({"query_text": query, "top_k": top_k}).encode()
    url = f"{_api_url(ctx)}/decisions/similar"
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
    except Exception as e:
        click.echo(f"Search failed: {e}", err=True)
        sys.exit(1)

    decisions = result.get("decisions", [])
    if not decisions:
        click.echo("No similar decisions found.")
        return
    for d in decisions:
        score_pct = int(d.get("score", 0) * 100)
        click.echo(f"{d['decision_id']} [{score_pct}%] — {d.get('decision_text', '')[:80]}")


if __name__ == "__main__":
    cli()
