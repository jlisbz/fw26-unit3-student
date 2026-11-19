"""
Group Scenario Implementation Module [GROUP TODO].

Instructions:
1. Update `SCENARIO_NAME` with your group's assigned track title.
2. Implement `inject_scenario_event()` to simulate your assigned disruption or workload spike.
3. Implement `compute_q_and_bounds()` to calculate the 4x6 Qualification Matrix Q and
   dynamic role capacity bounds (L_min, L_max) from live telemetry without hardcoding
   agent-to-role assignments.
"""
import math
from typing import Dict, List, Tuple
import numpy as np
from core.telemetry_bus import AGENTS, ROLES, AgentTelemetry, get_baseline_state

SCENARIO_NAME = "Track X: <Replace with Your Assigned Track Name>"
CRITICAL_BATTERY_THRESHOLD = 20.0
RSSI_PARTITION_THRESHOLD = -85.0

def inject_scenario_event() -> Tuple[Dict[str, AgentTelemetry], int]:
    """
    Simulate your group's assigned environmental disruption or workload spike.

    Track Reference:
      - Track 1 (Energy Evacuation): Set robot-a0 battery = 12.0 (< 20.0% cutoff)
      - Track 2 (Sensor Failure): Set robot-a1 lidar_ok = False
      - Track 3 (Communication Decay): Set robot-a0 distance_m = 120.0, rssi_dbm = -91.0;
        position robot-a1 at midpoint distance_m = 60.0
      - Track 4 (Flash Demand Spike): Set pending_jobs = 4
    """
    telemetry, pending_jobs = get_baseline_state()

    # TODO (Group Implementation):
    # Modify `telemetry` or `pending_jobs` for your group's assigned track.

    return telemetry, pending_jobs


def compute_q_and_bounds(
    telemetry: Dict[str, AgentTelemetry],
    pending_jobs: int,
) -> Tuple[np.ndarray, List[int], List[int]]:
    """
    Compute the 4x6 Qualification Matrix Q and role capacity vectors (L_min, L_max).
    Must produce valid optimal assignments for both Phase 1 (Baseline) and Phase 2 (Disrupted).

    Roles index order (ROLES):
      0: lead-scout
      1: precision-mapper
      2: cargo-carrier
      3: signal-relay
      4: charging
      5: standby
    """
    m, n = len(AGENTS), len(ROLES)
    Q = np.zeros((m, n))

    min_rssi = min(t.rssi_dbm for t in telemetry.values())
    max_dist = max(t.distance_m for t in telemetry.values())
    relay_needed = 1 if min_rssi < RSSI_PARTITION_THRESHOLD else 0
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
