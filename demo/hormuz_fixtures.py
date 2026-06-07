"""Hormuz Crisis demo fixtures — seed Atlas with historical decisions."""
HISTORICAL_DECISIONS = [
    {
        "decision_id": "dec-redsea-2024-001",
        "decision_type": "routing",
        "vessel_id": "mv-ever-given",
        "route_from": "Suez Canal",
        "route_to": "Rotterdam",
        "decision_text": (
            "Red Sea Houthi attacks forcing reroute. "
            "Cape of Good Hope route selected: +18% transit time, "
            "+12% fuel cost, avoids conflict zone."
        ),
        "outcome": "reroute_cape",
        "transit_time_delta_pct": 18.0,
        "fuel_cost_delta_pct": 12.0,
        "timestamp": "2024-01-10T08:00:00Z",
        "context_tags": ["red_sea", "houthi", "reroute", "cape"],
    },
    {
        "decision_id": "dec-redsea-2024-002",
        "decision_type": "routing",
        "vessel_id": "mv-cosco-shipping",
        "route_from": "Jeddah",
        "route_to": "Hamburg",
        "decision_text": (
            "Continued Red Sea threat. Second vessel rerouted Cape of Good Hope. "
            "Pattern confirmed: +18% transit time standard for this detour."
        ),
        "outcome": "reroute_cape",
        "transit_time_delta_pct": 18.0,
        "fuel_cost_delta_pct": 11.5,
        "timestamp": "2024-01-15T12:00:00Z",
        "context_tags": ["red_sea", "houthi", "reroute", "cape"],
    },
    {
        "decision_id": "dec-suez-2021-001",
        "decision_type": "routing",
        "vessel_id": "mv-ever-given-2",
        "route_from": "Asia",
        "route_to": "Europe",
        "decision_text": (
            "Suez Canal blocked. Rerouted via Cape of Good Hope. "
            "Delay: 6 days. Insurance claim filed."
        ),
        "outcome": "reroute_cape",
        "transit_time_delta_pct": 22.0,
        "fuel_cost_delta_pct": 15.0,
        "timestamp": "2021-03-25T06:00:00Z",
        "context_tags": ["suez", "blockage", "reroute", "cape"],
    },
    {
        "decision_id": "dec-hormuz-2019-001",
        "decision_type": "routing",
        "vessel_id": "mv-stena-impero",
        "route_from": "Bandar Abbas",
        "route_to": "Singapore",
        "decision_text": (
            "Iran-UK tensions in Hormuz Strait. Vessel diverted south. "
            "Oman Sea corridor used as temporary bypass."
        ),
        "outcome": "divert_oman_sea",
        "transit_time_delta_pct": 8.0,
        "fuel_cost_delta_pct": 5.0,
        "timestamp": "2019-07-19T00:00:00Z",
        "context_tags": ["hormuz", "iran", "tensions", "divert"],
    },
    {
        "decision_id": "dec-malacca-2023-001",
        "decision_type": "routing",
        "vessel_id": "mv-pacific-star",
        "route_from": "Singapore",
        "route_to": "Mumbai",
        "decision_text": (
            "Malacca Strait congestion. Lombok Strait alternative used. "
            "Minor delay of 2 days accepted."
        ),
        "outcome": "alternative_strait",
        "transit_time_delta_pct": 5.0,
        "fuel_cost_delta_pct": 3.0,
        "timestamp": "2023-08-01T00:00:00Z",
        "context_tags": ["malacca", "congestion", "lombok"],
    },
]

HORMUZ_CRISIS_EVENT = {
    "event_id": "evt-hormuz-2024-001",
    "event_type": "strait_closure",
    "affected_strait": "Hormuz",
    "vessels_affected": ["vessel-hormuz-01", "vessel-hormuz-02", "vessel-hormuz-03"],
    "severity": "CRITICAL",
    "description": (
        "Iran closes Hormuz Strait following escalating tensions. "
        "All tanker traffic halted. 20% of global oil supply affected."
    ),
    "timestamp": "2024-06-01T00:00:00Z",
}
