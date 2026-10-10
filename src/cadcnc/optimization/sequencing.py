"""Operation sequencing, precedence constraints, and 2-opt TSP rapid path optimization."""

import math
from typing import Dict, List, Tuple
from cadcnc.schemas.common import Point3D

def euclidean_distance_2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def compute_tour_length(points: List[Tuple[float, float]], order: List[int]) -> float:
    if len(order) < 2:
        return 0.0
    tot = 0.0
    for i in range(len(order) - 1):
        tot += euclidean_distance_2d(points[order[i]], points[order[i + 1]])
    return tot

def solve_tsp_2opt(points: List[Tuple[float, float]]) -> List[int]:
    """Orders 2D points to minimize rapid travel distance using Nearest Neighbor + 2-Opt."""
    n = len(points)
    if n <= 2:
        return list(range(n))

    # 1. Nearest Neighbor initial tour starting at origin or point 0
    visited = [False] * n
    tour = [0]
    visited[0] = True

    for _ in range(n - 1):
        curr = tour[-1]
        best_dist = float("inf")
        best_next = -1
        for j in range(n):
            if not visited[j]:
                d = euclidean_distance_2d(points[curr], points[j])
                if d < best_dist:
                    best_dist = d
                    best_next = j
        tour.append(best_next)
        visited[best_next] = True

    # 2. Iterative 2-Opt local search
    improved = True
    iterations = 0
    max_iterations = 100

    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        best_distance = compute_tour_length(points, tour)

        for i in range(1, n - 1):
            for k in range(i + 1, n):
                # Reverse sub-tour between i and k
                new_tour = tour[:i] + tour[i:k + 1][::-1] + tour[k + 1:]
                new_distance = compute_tour_length(points, new_tour)
                if new_distance < (best_distance - 1e-4):
                    tour = new_tour
                    best_distance = new_distance
                    improved = True
                    break
            if improved:
                break

    return tour
