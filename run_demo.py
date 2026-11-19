"""
Unit 3 Two-Phase Swarm Orchestration Demo Runner (Provided).
Phase 1: Establishes nominal baseline equilibrium across all 4 robot pods.
Phase 2: Injects the group's assigned disruption/workload event and reconciles roles.
"""
import time
from kubernetes import client, config
from core.telemetry_bus import get_baseline_state
from core.swarm_orchestrator import apply_swarm_reconfiguration
from scenarios.group_scenario import (
    SCENARIO_NAME,
    inject_scenario_event,
    compute_q_and_bounds,
)


def main():
    try:
        config.load_kube_config()
    except Exception:
        config.load_incluster_config()

    core_api = client.CoreV1Api()

    # Phase 1: Establish Nominal Baseline Equilibrium
    base_telemetry, base_jobs = get_baseline_state()
    apply_swarm_reconfiguration(
        core_api,
        "Phase 1: Nominal Swarm Baseline",
        base_telemetry,
        base_jobs,
        compute_q_and_bounds,
    )
    time.sleep(2)

    # Phase 2: Inject Group Scenario & Reconcile Swarm Roles
    event_telemetry, event_jobs = inject_scenario_event()
    apply_swarm_reconfiguration(
        core_api,
        f"Phase 2: {SCENARIO_NAME}",
        event_telemetry,
        event_jobs,
        compute_q_and_bounds,
    )


if __name__ == "__main__":
    main()
