from typing import Iterable, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .formatting import Formatter


class ExerciseSet:
    def __init__(
        self,
        min_set=None,
        max_set=5,
        min_reps=None,
        max_reps=5,
        weight=0,
        bar=True,
        bar_weight=45,
        plate_breakdown_on=True,
        formatter: "Formatter | None" = None,
    ):
        self.min_set = min_set
        self.max_set = max_set
        self.min_reps = min_reps
        self.max_reps = max_reps
        self.bar = bar
        self.bar_weight = bar_weight
        self.weight = (
            weight  # Bar and bar weight must be before weight method is called.
        )
        self.plate_breakdown_on = plate_breakdown_on
        self.formatter = formatter

    def describe(self) -> dict:
        """Return a formatting-neutral representation of the set."""

        # Format sets.
        # 3x5
        if self.min_set is None:
            set_label = "%d" % (self.set)
        # (3-5) x 5
        elif self.min_set >= 0 and self.max_set > 0:
            set_label = "(%d-%d)" % (self.min_set, self.max_set)
        else:
            set_label = ""

        # Format reps
        # Single digit reps only ie 3x5
        if self.min_reps is None:
            rep_label = "%d" % (self.max_reps)
        elif self.min_reps >= 0 and self.max_reps > 0:
            rep_label = "(%d-%d)" % (self.min_reps, self.max_reps)
        else:
            rep_label = ""

        set_rep = "%s x %s" % (set_label, rep_label)

        if self.weight <= 0 and self.bar is False:
            weight_label = self.plate_breakdown
            breakdown = None
        else:
            # Use formatter if available, otherwise fallback to default "lbs" format
            if self.formatter and hasattr(self.formatter, 'format_weight'):
                weight_label = self.formatter.format_weight(self.weight)
            else:
                weight_label = "%d lbs" % (self.weight)
            breakdown = self.plate_breakdown if self.plate_breakdown_on else None

        return {
            "set_rep": set_rep,
            "weight_label": weight_label,
            "plate_breakdown": breakdown,
        }

    def __str__(self):
        info = self.describe()
        parts = [f"{info['set_rep']} - {info['weight_label']}"]

        if info["plate_breakdown"]:
            parts.append(info["plate_breakdown"])

        return " - ".join(parts)

    #######################
    # SETTERS AND GETTERS #
    #######################

    @property
    def plate_breakdown(self):
        return self.__plate_breakdown

    @plate_breakdown.setter
    def plate_breakdown(self, s):
        self.__plate_breakdown = s  # ? Change to self.calc_plate_breakdown()?

    @property
    def weight(self):
        return self.__weight

    @weight.setter
    def weight(self, w):
        self.__weight = w
        self.__plate_breakdown = self.calc_plate_breakdown()

    @property
    def set(self):
        return self.max_set

    @set.setter
    def set(self, s):
        self.max_set = s

    @property
    def reps(self):
        return self.max_reps

    @reps.setter
    def reps(self, r):
        self.max_reps = r

    def calc_lifting_weight(self, working_weight, multiplier):
        w = ExerciseSet.round_weight(working_weight * multiplier)

        if w == 0:
            self.weight = self.bar_weight
        else:
            self.weight = w

    def calc_weighted_pullup(self, working_weight, body_weight, multiplier):
        calc_weight = (working_weight * multiplier) - body_weight
        if calc_weight <= 0:
            self.weight = 0
        else:
            self.weight = calc_weight

        self.plate_breakdown = self.calc_plate_breakdown()

    # Takes arg of int value of weight and returns string of plates in format: 400# - (45 x 3) 35 5 2.5
    def calc_plate_breakdown(self, available_plates: Optional[List[int]] = None):
        corrected_weight = ExerciseSet.round_weight(self.weight)
        weight = corrected_weight

        # TODO: Turn on/off different plates with option flag, ie 55, 35, 15
        if available_plates is None:
            plates = [45, 35, 25, 15, 10, 5, 2.5]
        else:
            plates = sorted(available_plates, reverse=True)
        plate_count = [0] * len(
            plates
        )  # Initial array with same number of plates in plates array

        if corrected_weight > self.bar_weight and self.bar == True:
            weight -= self.bar_weight  # Subtract weight of bar

        if self.bar == True:
            weight /= 2  # Only worry about one side of the bar

        while weight > 0:
            for i, v in enumerate(plates):
                while weight >= v:
                    plate_count[i] += 1
                    weight -= v

        # Create string to return from function
        final_string = ""

        # Create string
        for i, v in enumerate(plate_count):
            if v > 1:
                final_string += "(%s x %d) " % (plates[i], v)  # (45 x 2)
            elif v == 1:
                final_string += "%s " % (plates[i])

        if self.bar == False and corrected_weight <= 0:
            final_string = "Bodyweight"
        elif self.bar == True and corrected_weight <= self.bar_weight:
            final_string = "Bar"

        return final_string.strip()

    # Round weight down to nearest multiple of 5
    @staticmethod
    def round_weight(weight):
        return int(5 * round(weight / 5))


def get_plate_list(
    total_weight: float,
    bar_weight: float = 45.0,
    available_plates: Iterable[float] | None = None,
) -> List[float]:
    """
    Calculate the list of plates needed per side for a given total weight.

    Returns a sorted list (largest to smallest) of plates on one side of the bar.

    Example:
        total_weight = 185, bar_weight = 45
        per_side = (185 - 45) / 2 = 70
        plates needed: [45, 25] (one 45 and one 25 per side)
    """
    if total_weight <= bar_weight:
        return []

    if available_plates is None:
        available_plates = [45, 35, 25, 15, 10, 5, 2.5]

    plates_sorted = sorted(available_plates, reverse=True)
    per_side = (total_weight - bar_weight) / 2.0

    plates_on_bar: List[float] = []
    remaining = per_side

    for plate in plates_sorted:
        while remaining >= plate:
            plates_on_bar.append(plate)
            remaining -= plate

    return plates_on_bar


def plates_are_subset(warmup_plates: List[float], next_plates: List[float]) -> bool:
    """
    Check if warmup_plates is a subset of next_plates (can progress by only adding plates).

    Returns True if you can get from warmup_plates to next_plates by only adding plates,
    False if you'd need to remove any plates.

    Example:
        warmup_plates = [45, 25]  (185 lbs total)
        next_plates = [45, 35, 2.5]  (210 lbs total)
        Returns False because you'd need to remove the 25 to add 35+2.5

        warmup_plates = [45, 15]  (165 lbs total)
        next_plates = [45, 15, 5]  (175 lbs total)
        Returns True because you just add a 5 lb plate
    """
    warmup_count = {}
    for plate in warmup_plates:
        warmup_count[plate] = warmup_count.get(plate, 0) + 1

    next_count = {}
    for plate in next_plates:
        next_count[plate] = next_count.get(plate, 0) + 1

    # Check if all warmup plates are present in the next set
    for plate, count in warmup_count.items():
        if next_count.get(plate, 0) < count:
            return False

    return True


def round_up_to_valid_progression(
    current_weight: float,
    next_weight: float,
    bar_weight: float = 45.0,
    available_plates: Iterable[float] | None = None,
    max_increase: float = 30.0,
) -> float:
    """
    Round up current_weight to ensure a valid linear progression to next_weight.

    A valid progression means you can move from current to next by only ADDING plates,
    never removing them. If current weight requires removing plates to reach next,
    round current up to a weight that allows adding plates only.

    Strategy:
        - Find all possible plate combinations that are subsets of the next weight's plates
        - Choose the combination closest to current_weight (but >= current_weight)
        - Only adjust if within max_increase

    Args:
        current_weight: The current warmup weight
        next_weight: The next set's weight (either another warmup or working weight)
        bar_weight: Weight of the barbell
        available_plates: List of available plate weights
        max_increase: Maximum amount to increase current weight to fix progression (lbs)

    Returns:
        Adjusted current_weight that allows linear progression
    """
    if available_plates is None:
        available_plates = [45, 35, 25, 15, 10, 5, 2.5]

    # Get plates for current and next weights
    current_plates = get_plate_list(current_weight, bar_weight, available_plates)
    next_plates = get_plate_list(next_weight, bar_weight, available_plates)

    # If already a valid progression, return as-is
    if plates_are_subset(current_plates, next_plates):
        return current_weight

    # Generate all valid subsets of next_plates and find the best one
    # A valid subset is one that:
    # 1. Is a proper subset of next_plates (fewer or equal plates)
    # 2. Results in a weight >= current_weight
    # 3. Results in a weight < next_weight
    # 4. Is within max_increase of current_weight

    # Strategy: Build plate combinations from next_plates, starting with larger subsets
    # and working down, to find one closest to current_weight

    from itertools import combinations

    next_plate_count = {}
    for plate in next_plates:
        next_plate_count[plate] = next_plate_count.get(plate, 0) + 1

    # Create a list of (plate, count) for easier manipulation
    plate_items = list(next_plate_count.items())

    best_weight = None
    best_diff = float('inf')

    # Try all possible combinations of plates that are subsets of next_plates
    # We'll iterate through possible subset configurations
    def generate_subsets(plate_items):
        """Generate all valid subsets of plate combinations."""
        if not plate_items:
            yield []
            return

        plate, max_count = plate_items[0]
        rest = plate_items[1:]

        # For this plate, try using 0 to max_count of them
        for count in range(max_count + 1):
            for rest_subset in generate_subsets(rest):
                yield [(plate, count)] + rest_subset if count > 0 else rest_subset

    for subset_config in generate_subsets(plate_items):
        # Calculate the weight for this subset
        subset_plates = []
        for plate, count in subset_config:
            subset_plates.extend([plate] * count)

        test_weight = bar_weight + 2.0 * sum(subset_plates)

        # Check if this is a valid candidate
        # We want weights that are:
        # 1. Greater than or equal to current_weight
        # 2. Less than next_weight (strictly less to avoid duplicate weights)
        # 3. Within max_increase of current_weight
        # 4. Form a valid subset (plates are subset of next_plates)

        if (test_weight >= current_weight and
            test_weight < next_weight and
            test_weight <= current_weight + max_increase):

            diff = test_weight - current_weight
            if diff < best_diff:
                best_diff = diff
                best_weight = test_weight

    # If no valid weight found that's >= current_weight, try rounding DOWN
    # to the next lower valid subset. This is acceptable for warmups.
    if best_weight is None:
        # Find the largest valid subset that's less than current_weight
        for subset_config in generate_subsets(plate_items):
            subset_plates = []
            for plate, count in subset_config:
                subset_plates.extend([plate] * count)

            test_weight = bar_weight + 2.0 * sum(subset_plates)

            # Look for weights less than current but still reasonable
            # Allow rounding down to bar weight as last resort
            allow_bar_only = (test_weight == bar_weight)

            if (test_weight < current_weight and
                test_weight < next_weight and
                (test_weight >= current_weight * 0.5 or allow_bar_only)):  # No more than 50% decrease

                if best_weight is None or test_weight > best_weight:
                    best_weight = test_weight

    # Return the best weight found, or original if none found
    return best_weight if best_weight is not None else current_weight


def ensure_linear_warmup_progression(
    warmup_weights: List[float],
    working_weight: float,
    bar_weight: float = 45.0,
    available_plates: Iterable[float] | None = None,
    max_increase_per_warmup: float = 30.0,
) -> List[float]:
    """
    Ensure all warmup weights form a linear progression to working weight.

    Works backwards from the working weight to ensure each warmup can progress
    to the next by only adding plates, never removing them.

    Args:
        warmup_weights: List of warmup weights in order (lightest to heaviest)
        working_weight: The final working set weight
        bar_weight: Weight of the barbell
        available_plates: List of available plate weights
        max_increase_per_warmup: Max amount to increase any single warmup weight

    Returns:
        Adjusted list of warmup weights ensuring linear progression
    """
    if not warmup_weights:
        return []

    if available_plates is None:
        available_plates = [45, 35, 25, 15, 10, 5, 2.5]

    # Work backwards from working weight
    adjusted_weights = warmup_weights.copy()

    # Start from the last warmup and work backwards
    # Each weight must be a valid progression to the next weight
    all_weights = adjusted_weights + [working_weight]

    # Keep iterating until all progressions are linear or no more changes
    max_iterations = 10
    iteration = 0
    changed = True

    while changed and iteration < max_iterations:
        changed = False
        iteration += 1

        # Process backwards: for each warmup, ensure it can progress to next
        for i in range(len(all_weights) - 2, -1, -1):
            current = all_weights[i]
            next_weight = all_weights[i + 1]

            # Also get previous weight to ensure monotonically increasing
            prev_weight = all_weights[i - 1] if i > 0 else bar_weight

            # Check if current can progress linearly to next
            current_plates = get_plate_list(current, bar_weight, available_plates)
            next_plates = get_plate_list(next_weight, bar_weight, available_plates)

            # Check two conditions:
            # 1. Linear progression (plates are subset)
            # 2. Monotonic increasing (current <= next)
            needs_adjustment = (
                not plates_are_subset(current_plates, next_plates) or
                current > next_weight
            )

            if needs_adjustment:
                # Need to adjust current weight
                # Special case: if current > next_weight, set current = next_weight
                # This ensures monotonicity (same weight is okay for warmups)
                if current > next_weight:
                    adjusted = next_weight
                else:
                    # Normal case: current <= next_weight but not a valid progression
                    adjusted = round_up_to_valid_progression(
                        current,
                        next_weight,
                        bar_weight,
                        available_plates,
                        max_increase=max_increase_per_warmup,
                    )

                # If we couldn't find a valid adjustment within max_increase,
                # only fall back to bar-only if this is the FIRST warmup
                # For other warmups, keep the original weight (better to have a small
                # non-linearity than to make everything bar-only)
                if adjusted == current and i == 0:
                    # First warmup: check if bar-only is a valid progression to next
                    bar_only_plates = get_plate_list(bar_weight, bar_weight, available_plates)
                    if plates_are_subset(bar_only_plates, next_plates):
                        adjusted = bar_weight

                # Check if adjusted forms a valid linear progression to next
                adjusted_plates = get_plate_list(adjusted, bar_weight, available_plates)
                next_plates_check = get_plate_list(next_weight, bar_weight, available_plates)
                is_valid_progression = plates_are_subset(adjusted_plates, next_plates_check)

                # CRITICAL: Ensure monotonically STRICTLY increasing (except first warmup)
                # Only the first warmup can be bar-only. All subsequent warmups must be heavier.
                # Also ensure the adjusted weight forms a valid linear progression to next.
                if i > 0 and (adjusted <= prev_weight or not is_valid_progression):
                    # For non-first warmups, we need:
                    # 1. adjusted > prev_weight (strictly increasing)
                    # 2. adjusted plates ⊆ next_weight plates (linear progression)

                    # Try to find a valid weight that's between prev_weight and next_weight
                    # AND forms a valid linear progression to next_weight

                    # Get all valid subsets of next_plates
                    next_plates_list = get_plate_list(next_weight, bar_weight, available_plates)
                    next_plate_count = {}
                    for plate in next_plates_list:
                        next_plate_count[plate] = next_plate_count.get(plate, 0) + 1

                    plate_items = list(next_plate_count.items())

                    def generate_subsets(items):
                        if not items:
                            yield []
                            return
                        plate, max_count = items[0]
                        rest = items[1:]
                        for count in range(max_count + 1):
                            for rest_subset in generate_subsets(rest):
                                yield [(plate, count)] + rest_subset if count > 0 else rest_subset

                    # Find the smallest valid weight that's > prev_weight and < next_weight
                    best_candidate = None
                    for subset_config in generate_subsets(plate_items):
                        subset_plates = []
                        for plate, count in subset_config:
                            subset_plates.extend([plate] * count)
                        test_weight = bar_weight + 2.0 * sum(subset_plates)

                        if test_weight > prev_weight and test_weight < next_weight:
                            if best_candidate is None or test_weight < best_candidate:
                                best_candidate = test_weight

                    if best_candidate:
                        adjusted = best_candidate
                    else:
                        # No valid weight between prev and next - keep original
                        # This will create a non-linearity, but that's better than duplicates
                        adjusted = current

                # Handle the case where adjusted < prev_weight (backward progression)
                elif adjusted < prev_weight:
                    # Try using prev_weight if it forms a valid progression to next
                    prev_plates = get_plate_list(prev_weight, bar_weight, available_plates)
                    if plates_are_subset(prev_plates, next_plates):
                        # Great! Previous weight works for this progression
                        adjusted = prev_weight
                    else:
                        # Previous weight also doesn't work. Two options:
                        # 1. Use adjusted anyway (creates backward progression but linear)
                        # 2. Keep original (maintains forward progression but not linear)
                        #
                        # We choose option 1: accept the backward progression and let the
                        # next iteration fix the previous warmup to match or be less than this one
                        pass  # Keep adjusted as-is

                if adjusted != all_weights[i]:
                    all_weights[i] = adjusted
                    changed = True

    # Return just the warmup weights (exclude working weight)
    return all_weights[:-1]


def optimize_warmup_weight(
    total_weight: float,
    *,
    bar_weight: float = 45.0,
    available_plates: Iterable[float] | None = None,
    threshold: float = 2.5,
    next_total_weight: float | None = None,
    big_plate_min: float = 45.0,
    big_plate_slack: float = 10.0,
) -> float:
    """
    For warm-up sets ONLY:
      1. Round small plates up to reduce clutter (within threshold)
      2. If next set uses a big plate we're close to, pre-load it
      3. Ensure linear progression (only adding plates, never removing)

    The linear progression check ensures that you can move from this warmup
    to the next set by only adding plates, never removing them.

    Examples:
      1) Current: 185 (45+25 per side), Next: 210 (45+35+2.5)
         Problem: Must remove 25 to add 35+2.5
         Solution: Round 185 up to 190 (45+35 +2.5) so you just add 35 plate

      2) Current: 165 (45+15 per side), Next: 175 (45+15+5)
         Valid: Just add 5 lb plate
         No adjustment needed
    """
    # Nothing to optimize if we're at or below bar weight
    if total_weight <= bar_weight:
        return total_weight

    if available_plates is None:
        available_plates = [45, 35, 25, 15, 10, 5, 2.5]

    plates_sorted = sorted(available_plates)
    per_side = (total_weight - bar_weight) / 2.0
    if per_side <= 0:
        return total_weight

    # PHASE 1: Pre-load big plate if next set needs it and we're close
    if next_total_weight and next_total_weight > bar_weight:
        next_per_side = (next_total_weight - bar_weight) / 2.0
        big_candidates = [
            p for p in plates_sorted if p >= big_plate_min and p <= next_per_side
        ]
        next_big_plate = max(big_candidates) if big_candidates else None

        if next_big_plate and per_side < next_big_plate:
            gap = next_big_plate - per_side
            if gap <= big_plate_slack:
                preload_weight = bar_weight + 2.0 * next_big_plate
                # Still check linear progression for safety
                if next_total_weight:
                    return round_up_to_valid_progression(
                        preload_weight,
                        next_total_weight,
                        bar_weight,
                        available_plates,
                        max_increase=0,  # Already made our adjustment
                    )
                return preload_weight

    # PHASE 2: Optimize small plates (reduce clutter)
    # Peel off as many largest plates as possible
    largest = max(plates_sorted)
    base_total = 0.0
    remaining_per_side = per_side

    while remaining_per_side >= largest:
        base_total += largest
        remaining_per_side -= largest

    remainder = remaining_per_side

    # Try to replace remainder with a single plate
    optimized_weight = total_weight
    if remainder > 0:
        candidate: float | None = None
        for p in plates_sorted:
            if p >= remainder:
                if p - remainder <= threshold:
                    candidate = p
                break

        if candidate is not None:
            new_per_side = base_total + candidate
            optimized_weight = bar_weight + 2.0 * new_per_side

    # PHASE 3: Ensure linear progression to next set
    # Always check if we need to adjust for linear progression, regardless of whether
    # we optimized in phase 2
    if next_total_weight and next_total_weight > optimized_weight:
        adjusted = round_up_to_valid_progression(
            optimized_weight,
            next_total_weight,
            bar_weight,
            available_plates,
            max_increase=20.0,  # Allow up to 20 lbs increase to fix progression
        )
        # Only use the adjusted weight if it actually improved the progression
        if adjusted != optimized_weight:
            optimized_weight = adjusted

    return optimized_weight
