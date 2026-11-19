"""
E-CARGO Group Role Assignment (GRA) Linear Optimization Solver (Provided).
Solves the Integer Linear Program (ILP) maximizing total swarm fitness Q * X
subject to agent assignment and role staffing constraints [L_min, L_max].
"""
from typing import List
import numpy as np
import pulp
from core.telemetry_bus import AGENTS, ROLES


def solve_gra(Q: np.ndarray, L_min: List[int], L_max: List[int]) -> np.ndarray:
    """
    Solves the E-CARGO Group Role Assignment Integer Linear Program.

    Args:
        Q: (m x n) numpy array of qualification scores in [0.0, 1.0]
        L_min: list of length n specifying minimum agents required per role
        L_max: list of length n specifying maximum agents allowed per role

    Returns:
        X: (m x n) binary numpy array where X[i, j] == 1 assigns agent i to role j
    """
    expected_shape = (len(AGENTS), len(ROLES))
    if Q.shape != expected_shape:
        raise ValueError(f"Expected Q matrix of shape {expected_shape}, got {Q.shape}.")
    if len(L_min) != len(ROLES) or len(L_max) != len(ROLES):
        raise ValueError(f"L_min and L_max must each have length {len(ROLES)}.")
    if np.allclose(Q, 0.0):
        raise ValueError(
            "Qualification Matrix Q is all zeros. "
            "Implement compute_q_and_bounds() in scenarios/group_scenario.py first."
        )

    m, n = Q.shape
    prob = pulp.LpProblem("ECARGO_Swarm_GRA", pulp.LpMaximize)

    x = pulp.LpVariable.dicts(
        "X", ((i, j) for i in range(m) for j in range(n)), cat="Binary"
    )

    # Objective: Maximize total swarm capability score
    prob += pulp.lpSum(Q[i][j] * x[i, j] for i in range(m) for j in range(n))

    # Constraint 1: Each agent is assigned to exactly one active role
    for i in range(m):
        prob += pulp.lpSum(x[i, j] for j in range(n)) == 1

    # Constraint 2: Each role j satisfies [L_min[j], L_max[j]] staffing bounds
    for j in range(n):
        prob += pulp.lpSum(x[i, j] for i in range(m)) >= L_min[j]
        prob += pulp.lpSum(x[i, j] for i in range(m)) <= L_max[j]

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise RuntimeError(
            f"GRA Optimization infeasible or failed with status: {pulp.LpStatus[status]}. "
            f"Check L_min={L_min} and L_max={L_max}."
        )

    X = np.zeros((m, n), dtype=int)
    for i in range(m):
        for j in range(n):
            X[i, j] = int(round(pulp.value(x[i, j])))
    return X
