"""
Telemetry & Environment State Aggregator (Provided).
Models asynchronous hardware telemetry collected from distributed robot agents.
"""
from dataclasses import dataclass
from typing import Dict, Tuple

ROLES = [
    "lead-scout",        # r0: Forward exploration & pathfinding
    "precision-mapper",  # r1: High-res 3D LiDAR environment mapping
    "cargo-carrier",     # r2: Heavy payload transport
    "signal-relay",      # r3: Stationary wireless mesh repeater
    "charging",          # r4: Docked power recovery
    "standby",           # r5: Idle reserve capacity
]

AGENTS = ["robot-a0", "robot-a1", "robot-a2", "robot-a3"]


@dataclass
class AgentTelemetry:
    battery: float         # 0.0 to 100.0 (%)
    lidar_ok: bool         # True if LiDAR sensor is healthy
    payload_cap: float     # Normalized payload capacity (0.0 to 1.0)
    rssi_dbm: float        # Signal strength to gateway (e.g., -65 dBm)
    distance_m: float      # Distance from base gateway in meters


def get_baseline_state() -> Tuple[Dict[str, AgentTelemetry], int]:
    """
    Returns nominal swarm telemetry and external job queue depth.
    """
    telemetry = {
        "robot-a0": AgentTelemetry(battery=95.0, lidar_ok=True,  payload_cap=0.50, rssi_dbm=-62.0, distance_m=40.0),
        "robot-a1": AgentTelemetry(battery=90.0, lidar_ok=True,  payload_cap=0.85, rssi_dbm=-68.0, distance_m=60.0),
        "robot-a2": AgentTelemetry(battery=88.0, lidar_ok=True,  payload_cap=0.95, rssi_dbm=-70.0, distance_m=50.0),
        "robot-a3": AgentTelemetry(battery=92.0, lidar_ok=True,  payload_cap=0.80, rssi_dbm=-60.0, distance_m=20.0),
    }
    pending_cargo_jobs = 1
    return telemetry, pending_cargo_jobs
