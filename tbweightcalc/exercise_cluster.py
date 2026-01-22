from .exercise_set import ExerciseSet, optimize_warmup_weight, ensure_linear_warmup_progression
from .formatting import Formatter, PlainFormatter

# ---------------------------------------------------------------------------
# EXERCISE PROFILE DEFINITIONS
# ---------------------------------------------------------------------------

EXERCISE_PROFILES = {
    "squat": {
        "kind": "barbell",
        "warmup_scheme": "squat_bench",
        "top_scheme": "squat_bench",
    },
    "front squat": {
        "kind": "barbell",
        "warmup_scheme": "squat_bench",
        "top_scheme": "squat_bench",
    },
    "zercher squat": {
        "kind": "barbell",
        "warmup_scheme": "squat_bench",
        "top_scheme": "squat_bench",
    },
    "bench press": {
        "kind": "barbell",
        "warmup_scheme": "squat_bench",  # behaves like squat warmups but tweaked
        "top_scheme": "squat_bench",
    },
    "overhead press": {
        "kind": "barbell",
        "warmup_scheme": "squat_bench",  # same scheme, with bench-style multipliers
        "top_scheme": "squat_bench",
    },
    "deadlift": {
        "kind": "barbell",
        "warmup_scheme": "deadlift",
        "top_scheme": "deadlift",
    },
    "zercher deadlift": {
        "kind": "barbell",
        "warmup_scheme": "deadlift",
        "top_scheme": "deadlift",
    },
    "trap bar deadlift": {
        "kind": "barbell",
        "warmup_scheme": "deadlift",
        "top_scheme": "deadlift",
    },
    "rdl": {
        "kind": "barbell",
        "warmup_scheme": "deadlift",
        "top_scheme": "deadlift",
    },
    "weighted pullup": {
        "kind": "wpu",
        "warmup_scheme": None,
        "top_scheme": "wpu",
    },
}


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS FOR SET PATTERNS
# ---------------------------------------------------------------------------


def _build_warmup_sets(exercise: str) -> list[dict]:
    """Return warm-up set dictionaries based on exercise warmup scheme."""
    profile = EXERCISE_PROFILES.get(exercise)
    if not profile:
        return []

    scheme = profile["warmup_scheme"]

    # Squat / bench / front squat / overhead press warmups
    if scheme == "squat_bench":
        sets = [
            {"set": 2, "reps": 5, "multiplier": 0.0},
            {"set": 1, "reps": 5, "multiplier": 0.4},
            {"set": 1, "reps": 3, "multiplier": 0.6},
            {"set": 1, "reps": 2, "multiplier": 0.8},
        ]

        # Bench & OHP use slightly different multipliers
        if exercise in ("bench press", "overhead press"):
            bench_values = [0.0, 0.5, 0.7, 0.9]
            for i, d in enumerate(sets):
                d["multiplier"] = bench_values[i]

        return sets

    # Deadlift warmups
    if scheme == "deadlift":
        return [
            {"set": 2, "reps": 5, "multiplier": 0.4},
            {"set": 1, "reps": 3, "multiplier": 0.6},
            {"set": 1, "reps": 2, "multiplier": 0.85},
        ]

    return []


def _build_top_sets(exercise: str, week: int) -> list[dict]:
    """Return working/top-set dictionaries based on exercise and week."""
    scheme = EXERCISE_PROFILES.get(exercise, {}).get("top_scheme")

    if scheme == "squat_bench":
        if week == 3:
            return [
                {
                    "min_set": 3,
                    "max_set": 4,
                    "reps": 3,
                    "range": True,
                    "multiplier": 1.0,
                }
            ]
        if week == 5:
            return [
                {
                    "min_set": 3,
                    "max_set": 5,
                    "reps": 3,
                    "range": True,
                    "multiplier": 1.0,
                }
            ]
        if week == 6:
            return [
                {
                    "min_set": 3,
                    "max_set": 4,
                    "min_reps": 1,
                    "max_reps": 2,
                    "range": True,
                    "multiplier": 1.0,
                }
            ]
        return [
            {
                "min_set": 3,
                "max_set": 5,
                "reps": 5,
                "range": True,
                "multiplier": 1.0,
            }
        ]

    if scheme == "deadlift":
        if week in (3, 5):
            return [
                {
                    "min_set": 1,
                    "max_set": 3,
                    "reps": 3,
                    "range": True,
                    "multiplier": 1.0,
                }
            ]
        if week == 6:
            return [
                {
                    "min_set": 1,
                    "max_set": 3,
                    "min_reps": 1,
                    "max_reps": 2,
                    "range": True,
                    "multiplier": 1.0,
                }
            ]
        return [
            {
                "min_set": 1,
                "max_set": 3,
                "reps": 5,
                "range": True,
                "multiplier": 1.0,
            }
        ]

    # WPU: reuse squat/bench week pattern for top sets (multiplier=1.0),
    # but weight calculation is done via calc_weighted_pullup.
    if scheme == "wpu":
        return _build_top_sets("squat", week)

    return []


# ---------------------------------------------------------------------------
# EXERCISE CLUSTER CLASS
# ---------------------------------------------------------------------------


class ExerciseCluster:
    SQUAT = "squat"
    BENCHPRESS = "bench press"
    DEADLIFT = "deadlift"
    ZERCHER_DEADLIFT = "zercher deadlift"
    TRAP_BAR_DEADLIFT = "trap bar deadlift"
    RDL = "rdl"
    WPU = "weighted pullup"
    OHP = "overhead press"
    FRONT_SQUAT = "front squat"
    ZERCHER_SQUAT = "zercher squat"

    def __init__(
        self,
        week=1,
        exercise="",
        oneRepMax=0,
        body_weight=None,
        bar_weight=45.0,
        bar_label: str | None = None,
        formatter: Formatter | None = None,
    ):
        self.week = week
        self.exercise = exercise
        self.oneRepMax = oneRepMax
        self.body_weight = body_weight
        self.bar_weight = bar_weight
        self.bar_label = bar_label
        self.sets: list[ExerciseSet] = []
        self.formatter = formatter or PlainFormatter()
        self.calc_sets()

    def __str__(self):
        return self.render()

    def render(self, formatter: Formatter | None = None) -> str:
        fmt = formatter or self.formatter or PlainFormatter()
        out = []
        last = len(self.sets) - 1

        for i, s in enumerate(self.sets):
            info = s.describe()
            line = f"{info['set_rep']} - {info['weight_label']}"
            if info["plate_breakdown"]:
                line += f" - {info['plate_breakdown']}"

            if i == last:
                line = fmt.bold(line)

            out.append(fmt.list_item(line))

        return "\n".join(out)

    def __getitem__(self, item):
        return self.sets[item]

    # ------------------------- PROPERTIES -------------------------

    @property
    def week(self):
        return self.__week

    @week.setter
    def week(self, w):
        w = int(w)
        if w not in range(1, 7):
            w = 1
        self.__week = w

        multipliers = {1: 0.70, 2: 0.80, 3: 0.90, 4: 0.75, 5: 0.85, 6: 0.95}
        self.week_multiplier = multipliers[w]

    @property
    def week_multiplier(self):
        return self.__week_multiplier

    @week_multiplier.setter
    def week_multiplier(self, m: float):
        self.__week_multiplier = m
        # keep label behavior compatible with older code/tests
        self.label = m

    @property
    def label(self) -> str:
        return self.__label

    @label.setter
    def label(self, _m):
        # derive label text from current multiplier
        self.__label = f"{int(self.week_multiplier * 100)}%"

    @property
    def working_weight(self):
        return ExerciseSet.round_weight(self.oneRepMax * self.week_multiplier)

    def add(self, set_obj: ExerciseSet):
        self.sets.append(set_obj)

    # ------------------------- MAIN LOGIC -------------------------

    def calc_sets(self):
        profile = EXERCISE_PROFILES.get(self.exercise)
        if not profile:
            self.sets = []
            return

        setdefs: list[dict] = []

        # Warm-ups only for barbell lifts
        if profile["kind"] == "barbell":
            setdefs.extend(_build_warmup_sets(self.exercise))

        # Top sets
        setdefs.extend(_build_top_sets(self.exercise, self.week))

        # First pass: build all sets and compute raw weights
        built_sets: list[ExerciseSet] = []
        for d in setdefs:
            s = ExerciseSet(bar_weight=self.bar_weight, bar_label=self.bar_label, formatter=self.formatter)

            # Deal with set/reps vs ranges
            if d.get("range"):
                if "min_set" in d:
                    s.min_set = d["min_set"]
                if "max_set" in d:
                    s.max_set = d["max_set"]
                if "min_reps" in d:
                    s.min_reps = d["min_reps"]
                if "max_reps" in d:
                    s.max_reps = d["max_reps"]
                if "set" in d:
                    s.set = d["set"]
                if "reps" in d:
                    s.reps = d["reps"]
            else:
                s.set = d["set"]
                s.reps = d["reps"]

            kind = profile["kind"]

            # BARBELL LIFTS -------------------------------------------------
            if kind == "barbell":
                s.calc_lifting_weight(self.working_weight, d["multiplier"])

            # WEIGHTED PULLUPS ----------------------------------------------
            elif kind == "wpu":
                s.bar = False
                s.calc_weighted_pullup(
                    self.working_weight,
                    self.body_weight,
                    d["multiplier"],
                )
                # Plate breakdown only when total weight > 45#
                s.plate_breakdown_on = s.weight > 45

            built_sets.append(s)

        # Second pass: apply warmup optimization with lookahead
        if profile["kind"] == "barbell":
            # First, apply individual warmup optimizations (reduce plate clutter)
            # NOTE: We skip this optimization pass because it can create non-linearities
            # that conflict with the second pass. The second pass (ensure_linear_warmup_progression)
            # now handles all warmup optimization including linear progression.
            # for idx, (d, s) in enumerate(zip(setdefs, built_sets)):
            #     if d.get("multiplier", 1.0) < 1.0:
            #         next_weight = None
            #         for next_set in built_sets[idx + 1 :]:
            #             next_weight = next_set.weight
            #             break
            #
            #         s.weight = optimize_warmup_weight(
            #             total_weight=s.weight,
            #             bar_weight=self.bar_weight,
            #             threshold=2.5,
            #             next_total_weight=next_weight,
            #         )

            # Second, ensure linear progression (work backwards to fix any issues)
            warmup_weights = []
            warmup_indices = []
            working_weight = None

            for idx, (d, s) in enumerate(zip(setdefs, built_sets)):
                if d.get("multiplier", 1.0) < 1.0:
                    warmup_weights.append(s.weight)
                    warmup_indices.append(idx)
                else:
                    # This is the working set
                    working_weight = s.weight
                    break  # Only care about first working set for warmup progression

            if warmup_weights and working_weight:
                # Allow up to 25% increase per warmup to ensure linear progression
                # For heavy lifts, this might mean significant jumps
                max_pct_increase = 0.25
                max_increase = max(30.0, working_weight * max_pct_increase)

                adjusted_warmups = ensure_linear_warmup_progression(
                    warmup_weights,
                    working_weight,
                    bar_weight=self.bar_weight,
                    max_increase_per_warmup=max_increase,
                )

                # Apply the adjusted weights back to the sets
                for idx, adjusted_weight in zip(warmup_indices, adjusted_warmups):
                    built_sets[idx].weight = adjusted_weight

        # Save sets
        self.sets = built_sets
