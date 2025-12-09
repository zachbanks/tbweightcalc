from __future__ import annotations


def calculate_one_rm(weight: float, reps: int) -> int:
    if weight <= 0:
        raise ValueError("Weight must be positive.")
    if reps < 1:
        raise ValueError("Reps must be at least 1.")

    # If it was truly a 1-rep max, return it directly
    if reps == 1:
        return int(round(weight))

    # Epley formula for reps > 1
    one_rm = weight * (1 + reps / 30.0)
    return int(round(one_rm))
