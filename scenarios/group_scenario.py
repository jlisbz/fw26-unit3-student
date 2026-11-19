import math
from typing import Dict, List, Tuple
import numpy as np
from core.telemetry_bus import AGENTS, ROLES, AgentTelemetry, get_baseline_state

SCENARIO_NAME = "Track 1: Critical Energy Evacuation & Handoff"
CRITICAL_BATTERY_THRESHOLD = 20.0
RSSI_PARTITION_THRESHOLD = -85.0

def inject_scenario_event() -> Tuple[Dict[str, AgentTelemetry], int]:
    """
    Simulate critical battery depletion on robot-a0 (12.0% < 20.0% safety threshold).
    """
    telemetry, pending_jobs = get_baseline_state()
    telemetry["robot-a0"].battery = 12.0
    return telemetry, pending_jobs


def compute_q_and_bounds(
    telemetry: Dict[str, AgentTelemetry],
    pending_jobs: int,
) -> Tuple[np.ndarray, List[int], List[int]]:
    """
    Computes Qualification Matrix Q and role capacity bounds (L_min, L_max).
    Enforces mandatory charging evacuation when battery < 20.0% while optimizing
    field role assignments across healthy agents.
    """
    m, n = len(AGENTS), len(ROLES)
    Q = np.zeros((m, n))

    min_rssi = min(t.rssi_dbm for t in telemetry.values())
    max_dist = max(t.distance_m for t in telemetry.values())
    relay_needed = 1 if min_rssi < -85.0 else 0
    midpoint_dist = max_dist / 2.0

    for i, name in enumerate(AGENTS):
        t = telemetry[name]
        bat = t.battery / 100.0

        # Preemptive energy safety cutoff (< 20%): force charging role, zero out field roles
        if t.battery < CRITICAL_BATTERY_THRESHOLD:
            Q[i, ROLES.index("charging")] = 1.00
            continue

        # r0: lead-scout (high battery + healthy LiDAR + forward range readiness)
        scout_pos = 0.08 if t.distance_m >= 40.0 else 0.0
        Q[i, ROLES.index("lead-scout")] = round(
            min(1.0, bat * (0.95 if t.lidar_ok else 0.05) + scout_pos), 3
        )

        # r1: precision-mapper (requires healthy LiDAR; optimal in mid-field 35-80m)
        field_factor = 1.0 if 35.0 <= t.distance_m <= 80.0 else 0.80
        Q[i, ROLES.index("precision-mapper")] = round(
            bat * 0.92 * field_factor if t.lidar_ok else 0.02, 3
        )

        # r2: cargo-carrier (battery * payload_cap)
        Q[i, ROLES.index("cargo-carrier")] = round(bat * t.payload_cap, 3)

        # r3: signal-relay (spatial midpoint affinity when relay is needed)
        if relay_needed and max_dist > 0:
            spatial_fit = max(0.0, 1.0 - abs(t.distance_m - midpoint_dist) / max_dist)
            Q[i, ROLES.index("signal-relay")] = round(spatial_fit, 3)
        else:
            Q[i, ROLES.index("signal-relay")] = 0.05

        # r4: charging (low affinity when battery >= 20%)
        Q[i, ROLES.index("charging")] = 0.05

        # r5: standby (energy-conserving dock reserve affinity near base)
        dock_bonus = 0.35 if t.distance_m <= 25.0 else 0.0
        Q[i, ROLES.index("standby")] = round(bat * 0.40 + dock_bonus, 3)

    required_carriers = min(2, max(1, math.ceil(pending_jobs / 2)))
    L_min = [1, 1, required_carriers, relay_needed, 0, 0]
    L_max = [1, 1, required_carriers, relay_needed, m, m]

    return Q, L_min, L_max