from typing import List, Optional
from typing import Iterable


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

    def __str__(self):
        str, set, rep = "", "", ""

        # Format sets.
        # 3x5
        if self.min_set == None:
            set = "%d" % (self.set)  # 3
        # (3-5) x 5
        elif self.min_set >= 0 and self.max_set > 0:
            set = "(%d-%d)" % (self.min_set, self.max_set)

        # Format reps
        # Single digit reps only ie 3x5
        if self.min_reps == None:
            rep = "%d" % (self.max_reps)
        elif self.min_reps >= 0 and self.max_reps > 0:
            rep = "(%d-%d)" % (self.min_reps, self.max_reps)

        # Combine set and rep strings
        str = "%s x %s" % (set, rep)  # 3x5 or (3-4)x(1-2)

        if self.weight <= 0 and self.bar == False:
            # Plate breakdown = Bodyweight
            str += " - %s" % self.plate_breakdown
        else:
            str += " - %d lbs" % (self.weight)

        # Add plate breakdown
        if self.plate_breakdown_on:
            str += " - %s" % self.plate_breakdown

        return str

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


def optimize_warmup_weight(
    total_weight: float,
    *,
    bar_weight: float = 45.0,
    available_plates: Iterable[float] | None = None,
    threshold: float = 2.5,
) -> float:
    """
    For warm-up sets ONLY:
      If the per-side plate total is within `threshold` lb of a single plate,
      round UP to that plate to reduce number of plates.

    Example:
      total_weight = 90  (45 bar + 22.5/side)
      per_side = (90 - 45) / 2 = 22.5
      available_plates = [45, 35, 25, 15, 10, 5, 2.5]

      next plate >= 22.5 is 25
      25 - 22.5 = 2.5 <= threshold -> optimized total = 45 + 25*2 = 95
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

    candidate: float | None = None

    for p in plates_sorted:
        if p >= per_side:
            # First plate that is >= current per-side load
            if p - per_side <= threshold:
                candidate = p
            break

    if candidate is None:
        return total_weight

    optimized_total = bar_weight + candidate * 2.0
    return optimized_total


def optimize_warmup_weight(
    total_weight: float,
    *,
    bar_weight: float = 45.0,
    available_plates: Iterable[float] | None = None,
    threshold: float = 2.5,
) -> float:
    """
    For warm-up sets ONLY:
      If the *small plates* on each side are within `threshold` lb of the next
      single plate, round that remainder UP to reduce plate clutter.

    Logic (per side):
      per_side = (total - bar) / 2

      base_plate = largest plate <= per_side  (e.g. 45)
      remainder  = per_side - base_plate      (e.g. 22.5 from 15+5+2.5)

      If there is a plate `p` such that:
        p >= remainder and (p - remainder) <= threshold,
      then:
        new_per_side = base_plate + p
        new_total = bar + 2 * new_per_side

    Example:
      total = 180  (45 bar + (45+15+5+2.5) per side)
      per_side = (180 - 45) / 2 = 67.5
      base_plate = 45
      remainder = 22.5
      next plate >= 22.5 is 25
      25 - 22.5 = 2.5 <= threshold

      -> per_side -> 45 + 25 = 70
      -> total -> 45 + 2 * 70 = 185
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

    # 1) Choose the "big" base plate that we always keep on the bar.
    #    If no plate <= per_side, base_plate is 0 (only small stuff).
    non_bigger = [p for p in plates_sorted if p <= per_side]
    base_plate = max(non_bigger) if non_bigger else 0.0

    remainder = per_side - base_plate
    if remainder <= 0:
        return total_weight

    # 2) Find a single plate that can replace the remainder
    candidate: float | None = None
    for p in plates_sorted:
        if p >= remainder:
            if p - remainder <= threshold:
                candidate = p
            break

    if candidate is None:
        return total_weight

    new_per_side = base_plate + candidate
    optimized_total = bar_weight + 2.0 * new_per_side
    return optimized_total


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
      Try to reduce plate clutter on each side by rounding the *small plates*
      up to a single plate if the difference is within `threshold`.

    Additionally, if the *next* set will require a "big" plate (>=
    ``big_plate_min``) and the current per-side load is reasonably close to
    that plate (within ``big_plate_slack``), round UP to that big plate so the
    bar is pre-loaded for the upcoming set.

    Per-side logic:
      per_side = (total - bar) / 2

      base_total = sum of as many largest plates (e.g. 45s) as possible
      remainder  = per_side - base_total    (represents small plates)

      If there exists a plate p such that:
        p >= remainder and (p - remainder) <= threshold
      then:
        new_per_side = base_total + p
        new_total = bar + 2 * new_per_side

    Examples:
      1) 180 lb total:
         per_side = (180 - 45) / 2 = 67.5
         largest plate = 45

         base_total: 67.5 - 45 = 22.5 → base_total=45, remainder=22.5
         next plate >= 22.5 is 25 (gap = 2.5 <= threshold)

         → per_side -> 45 + 25 = 70
         → total -> 45 + 2*70 = 185 (i.e., (45 x 2) 25)

      2) 290 lb total:
         per_side = (290 - 45) / 2 = 122.5
         base_total: 122.5 - 45 = 77.5, 77.5 - 45 = 32.5
                     → base_total = 90, remainder = 32.5
         next plate >= 32.5 is 35 (gap = 2.5)

         → per_side -> 90 + 35 = 125
         → total -> 45 + 2*125 = 295 (i.e., (45 x 2) 35)
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

    # Prefer pre-loading a big plate if the next set will use one soon and
    # we're close enough to justify the jump.
    if next_total_weight and next_total_weight > bar_weight:
        next_per_side = (next_total_weight - bar_weight) / 2.0
        big_candidates = [
            p for p in plates_sorted if p >= big_plate_min and p <= next_per_side
        ]
        next_big_plate = max(big_candidates) if big_candidates else None

        if next_big_plate and per_side < next_big_plate:
            gap = next_big_plate - per_side
            if gap <= big_plate_slack:
                return bar_weight + 2.0 * next_big_plate

    # 1) Peel off as many largest plates as possible (base stack of 45s, 35s, etc.)
    largest = max(plates_sorted)
    base_total = 0.0

    while per_side - largest >= 0:
        base_total += largest
        per_side -= largest

    remainder = per_side
    if remainder <= 0:
        return total_weight

    # 2) Try to replace the remainder with a single plate
    candidate: float | None = None
    for p in plates_sorted:
        if p >= remainder:
            if p - remainder <= threshold:
                candidate = p
            break

    if candidate is None:
        return total_weight

    new_per_side = base_total + candidate
    optimized_total = bar_weight + 2.0 * new_per_side
    return optimized_total
