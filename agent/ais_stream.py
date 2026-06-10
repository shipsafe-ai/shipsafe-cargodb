"""
AIS stream integration for CargoDB.

On ShipStaticData events for tracked vessels:
  → writes a vessel_profile decision to Atlas with Voyage AI embeddings
  → MemoryRecall can then answer "have we tracked this vessel before?"

On PositionReport for vessels entering/exiting the Hormuz conflict zone:
  → triggers a conflict_check decision write
  → next routing decision will recall: "Ever Given last seen Hormuz, RESTRICTED status"

This demonstrates Atlas Vector Search recall over REAL vessel history,
not just seeded fixtures.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

log = logging.getLogger(__name__)

AISSTREAM_URL = "wss://stream.aisstream.io/v0/stream"

BOUNDING_BOX = {
    "MinLatitude": 24.0,
    "MaxLatitude": 28.0,
    "MinLongitude": 54.0,
    "MaxLongitude": 60.0,
}

TRACKED_MMSI = {
    "353136000",  # Ever Given
    "255806178",  # MSC Gülsün
    "440350900",  # HMM Algeciras
    "220625000",  # Maersk Mc-Kinney Møller
    "477310400",  # COSCO Shipping Universe
}

# Conflict zone: Hormuz chokepoint ±0.5 deg
CONFLICT_LAT = (26.0, 27.2)
CONFLICT_LON = (55.8, 57.0)

_static_cache: dict[str, dict[str, Any]] = {}
_conflict_events: list[dict[str, Any]] = []

# Callback: called with decision dict when a new memory-worthy event occurs
# Wire this to MemoryWriter.run() in main.py lifespan
_on_decision: Callable[[dict[str, Any]], Awaitable[None]] | None = None


def register_decision_callback(fn: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
    global _on_decision
    _on_decision = fn


def get_conflict_events() -> list[dict[str, Any]]:
    return list(_conflict_events)


def _in_conflict_zone(lat: float, lon: float) -> bool:
    return (CONFLICT_LAT[0] <= lat <= CONFLICT_LAT[1] and
            CONFLICT_LON[0] <= lon <= CONFLICT_LON[1])


async def _emit_decision(decision: dict[str, Any]) -> None:
    if _on_decision:
        try:
            await _on_decision(decision)
        except Exception as e:
            log.warning("Decision callback failed: %s", e)


async def _connect(api_key: str) -> None:
    try:
        import websockets  # type: ignore

        async with websockets.connect(AISSTREAM_URL) as ws:
            await ws.send(json.dumps({
                "APIKey": api_key,
                "BoundingBoxes": [[BOUNDING_BOX]],
                "FiltersShipMMSI": list(TRACKED_MMSI),
                "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
            }))
            log.info("AISstream connected — CargoDB vessel memory active")

            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    mtype = msg.get("MessageType", "")
                    meta = msg.get("Metadata", {})
                    body = msg.get("Message", {}).get(mtype, {})
                    mmsi = str(meta.get("MMSI") or body.get("UserID") or "")
                    if not mmsi:
                        continue

                    if mtype == "ShipStaticData":
                        name = (body.get("Name") or "").strip()
                        dest = (body.get("Destination") or "").strip()
                        imo = body.get("ImoNumber")
                        ship_type = body.get("Type")
                        _static_cache[mmsi] = {"name": name, "destination": dest, "imo": imo, "ship_type": ship_type}

                        # Write vessel profile to Atlas memory
                        await _emit_decision({
                            "decision_type": "vessel_profile",
                            "decision": f"Vessel {name} (MMSI {mmsi}, IMO {imo}) identified in Hormuz corridor. Destination: {dest}. Ship type: {ship_type}.",
                            "outcome": "tracked",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "metadata": {"mmsi": mmsi, "imo": imo, "destination": dest},
                        })

                    elif mtype == "PositionReport":
                        lat = body.get("Latitude", 0)
                        lon = body.get("Longitude", 0)
                        speed = body.get("Sog", 0)
                        nav_status = body.get("NavigationalStatus", 0)
                        static = _static_cache.get(mmsi, {})
                        name = static.get("name", mmsi)

                        if _in_conflict_zone(lat, lon):
                            event = {
                                "mmsi": mmsi,
                                "name": name,
                                "lat": lat, "lon": lon,
                                "speed": speed,
                                "nav_status": nav_status,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                            _conflict_events.insert(0, event)
                            if len(_conflict_events) > 100:
                                _conflict_events.pop()

                            await _emit_decision({
                                "decision_type": "routing",
                                "decision": f"Vessel {name} (MMSI {mmsi}) detected in Hormuz conflict zone at {lat:.4f}N {lon:.4f}E. Speed {speed:.1f}kn. Nav status {nav_status}.",
                                "outcome": "conflict_detected",
                                "timestamp": event["timestamp"],
                                "metadata": {"mmsi": mmsi, "lat": lat, "lon": lon, "speed": speed},
                            })

                except Exception:
                    continue

    except Exception as e:
        log.warning("AISstream disconnected: %s", e)
        await asyncio.sleep(10)


async def start_ais_feed(api_key: str) -> None:
    while True:
        await _connect(api_key)
        await asyncio.sleep(10)
