"""
Closed-Loop Kubernetes Swarm Orchestrator (Provided).
Evaluates Q and L via the group's scenario module, solves GRA via PuLP,
and idempotently patches live Kubernetes pod `ecargo.role` labels.
"""
from typing import Callable, Dict, List, Tuple
import numpy as np
from kubernetes import client
from rich.console import Console
from rich.table import Table
from core.telemetry_bus import AGENTS, ROLES, AgentTelemetry
from core.ecargo_gra_solver import solve_gra

console = Console()


def apply_swarm_reconfiguration(
    core_api: client.CoreV1Api,
    scenario_title: str,
    telemetry: Dict[str, AgentTelemetry],
    pending_jobs: int,
    q_bounds_fn: Callable[[Dict[str, AgentTelemetry], int], Tuple[np.ndarray, List[int], List[int]]],
    namespace: str = "default",
) -> np.ndarray:
    """
    Executes one closed-loop E-CARGO reconciliation cycle against the Kubernetes cluster.
    """
    console.rule(f"[bold cyan]{scenario_title}[/bold cyan]")

    # 1. Compute Q matrix and role range bounds (L_min, L_max)
    Q, L_min, L_max = q_bounds_fn(telemetry, pending_jobs)

    # 2. Solve E-CARGO Group Role Assignment
    X = solve_gra(Q, L_min, L_max)

    # 3. Display Assignment Table and Patch Kubernetes Pod Labels
    table = Table(title="Optimal E-CARGO Role Assignment (Matrix X)")
    table.add_column("Agent Pod", style="cyan", no_wrap=True)
    table.add_column("Battery", justify="right")
    table.add_column("LiDAR", justify="center")
    table.add_column("RSSI / Dist", justify="right")
    table.add_column("Previous Role", style="yellow")
    table.add_column("Assigned Role", style="bold green")
    table.add_column("Fitness Q[i,j]", justify="right", style="magenta")

    for i, pod_name in enumerate(AGENTS):
        role_idx = int(np.argmax(X[i]))
        new_role = ROLES[role_idx]
        fitness = Q[i, role_idx]
        t = telemetry[pod_name]

        # Read current role label from Kubernetes API
        pod = core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
        old_role = pod.metadata.labels.get("ecargo.role", "none")

        # Idempotent patch: only update Kubernetes metadata when role changes
        if old_role != new_role:
            patch_body = {"metadata": {"labels": {"ecargo.role": new_role}}}
            core_api.patch_namespaced_pod(name=pod_name, namespace=namespace, body=patch_body)

        table.add_row(
            pod_name,
            f"{t.battery:.0f}%",
            "OK" if t.lidar_ok else "FAIL",
            f"{t.rssi_dbm:.0f} dBm / {t.distance_m:.0f}m",
            old_role,
            new_role if old_role == new_role else f"{new_role} (UPDATED)",
            f"{fitness:.3f}",
        )

    console.print(table)
    total_score = float(np.sum(Q * X))
    console.print(f"[bold]Role Bounds L_min:[/bold] {L_min} | [bold]L_max:[/bold] {L_max}")
    console.print(f"[bold]Total Swarm Utility Score:[/bold] [green]{total_score:.3f}[/green]\n")
    return X
