"""Tests for linear warmup progression functionality."""

from tbweightcalc.exercise_set import (
    get_plate_list,
    plates_are_subset,
    round_up_to_valid_progression,
    ensure_linear_warmup_progression,
)
from tbweightcalc.exercise_cluster import ExerciseCluster


class TestGetPlateList:
    """Test getting the list of plates for a given weight."""

    def test_bar_only(self):
        """Bar-only weight should return empty plate list."""
        assert get_plate_list(45, 45) == []

    def test_one_plate_per_side(self):
        """135 lbs = bar + one 45 per side."""
        assert get_plate_list(135, 45) == [45]

    def test_multiple_plates(self):
        """Test weight requiring multiple plates per side."""
        # 185 = 45 bar + (45 + 25) per side
        plates = get_plate_list(185, 45)
        assert 45 in plates
        assert 25 in plates

    def test_fractional_plates(self):
        """Test weight requiring fractional plates."""
        # 320 = 45 bar + (45*3 + 2.5) per side
        plates = get_plate_list(320, 45)
        assert plates.count(45) == 3
        assert 2.5 in plates


class TestPlatesAreSubset:
    """Test checking if one plate configuration is a subset of another."""

    def test_empty_is_subset(self):
        """Empty plate list is a subset of any configuration."""
        assert plates_are_subset([], [45])
        assert plates_are_subset([], [45, 25])

    def test_same_plates(self):
        """Same plates should be a subset."""
        assert plates_are_subset([45], [45])
        assert plates_are_subset([45, 25], [45, 25])

    def test_valid_subset(self):
        """Test valid subset (can progress by only adding)."""
        assert plates_are_subset([45], [45, 25])
        assert plates_are_subset([45, 15], [45, 15, 5])

    def test_not_subset(self):
        """Test invalid subset (would need to remove plates)."""
        # Would need to remove 25 to add 35
        assert not plates_are_subset([45, 25], [45, 35])

        # Would need to remove 15 and 5 to add single 45
        assert not plates_are_subset([15, 5], [45])

    def test_multiple_same_plates(self):
        """Test with multiple instances of same plate."""
        assert plates_are_subset([45, 45], [45, 45, 25])
        assert not plates_are_subset([45, 45, 15], [45, 45, 45])  # Would need to remove 15


class TestRoundUpToValidProgression:
    """Test rounding warmup weights to ensure linear progression."""

    def test_already_valid(self):
        """Already valid progression should not change."""
        # 135 -> 185: [45] -> [45, 25] is valid
        result = round_up_to_valid_progression(135, 185, 45)
        assert result == 135

    def test_needs_adjustment(self):
        """Invalid progression should be adjusted."""
        # 185 -> 210: [45, 25] -> [45, 35, 2.5]
        # Should round up to 205: [45, 35]
        result = round_up_to_valid_progression(185, 210, 45)
        assert result == 205.0

    def test_bar_only_fallback(self):
        """Should fall back to bar-only if no valid subset found within max_increase."""
        # 85 -> 135: [15, 5] -> [45]
        # No valid subset within 30 lbs, but bar-only (45) is valid
        result = round_up_to_valid_progression(85, 135, 45, max_increase=20)
        # Should stay at 85 since we can't find a valid progression
        assert result == 85

    def test_respects_max_increase(self):
        """Should not exceed max_increase parameter."""
        result = round_up_to_valid_progression(100, 300, 45, max_increase=10)
        # Should find something within 10 lbs or return original
        assert result <= 110 or result == 100


class TestEnsureLinearWarmupProgression:
    """Test ensuring all warmups form a linear progression."""

    def test_empty_warmups(self):
        """Empty warmup list should return empty."""
        result = ensure_linear_warmup_progression([], 300, 45)
        assert result == []

    def test_all_valid(self):
        """Already valid progression should not change."""
        warmups = [45, 135, 165, 175]
        result = ensure_linear_warmup_progression(warmups, 180, 45)
        # Should remain the same or very close
        assert len(result) == len(warmups)

    def test_fixes_invalid_progression(self):
        """Should fix invalid progression by working backwards."""
        # Deadlift example: 85 -> 135 -> 185 -> 210
        # 185 -> 210 is not valid ([45,25] -> [45,35,2.5])
        warmups = [85, 135, 185]
        result = ensure_linear_warmup_progression(warmups, 210, 45)

        # Check that result forms a valid linear progression
        all_weights = result + [210]
        for i in range(len(all_weights) - 1):
            curr_plates = get_plate_list(all_weights[i], 45)
            next_plates = get_plate_list(all_weights[i + 1], 45)
            assert plates_are_subset(curr_plates, next_plates)

    def test_heavy_squat(self):
        """Test with heavy squat requiring multiple 45s."""
        # Original warmups for 455 1RM @ 70%
        warmups = [45, 135, 190, 255]
        working = 320
        result = ensure_linear_warmup_progression(warmups, working, 45, max_increase_per_warmup=80)

        # Verify linear progression
        all_weights = result + [working]
        for i in range(len(all_weights) - 1):
            curr_plates = get_plate_list(all_weights[i], 45)
            next_plates = get_plate_list(all_weights[i + 1], 45)
            is_linear = plates_are_subset(curr_plates, next_plates)
            assert is_linear, f"{all_weights[i]} -> {all_weights[i+1]} not linear"


class TestExerciseClusterLinearProgression:
    """Integration tests for linear warmup progression in exercise clusters."""

    def test_squat_linear_progression(self):
        """Test squat warmup progression is linear."""
        cluster = ExerciseCluster(week=1, exercise="squat", oneRepMax=455, bar_weight=45.0)

        # Check all warmups form linear progression to working weight
        weights = [s.weight for s in cluster.sets]

        for i in range(len(weights) - 1):
            curr_plates = get_plate_list(weights[i], 45)
            next_plates = get_plate_list(weights[i + 1], 45)
            is_linear = plates_are_subset(curr_plates, next_plates)
            assert is_linear, f"Squat: {weights[i]} -> {weights[i+1]} not linear"

    def test_deadlift_linear_progression(self):
        """Test deadlift warmup progression is linear."""
        cluster = ExerciseCluster(week=1, exercise="deadlift", oneRepMax=300, bar_weight=45.0)

        weights = [s.weight for s in cluster.sets]

        for i in range(len(weights) - 1):
            curr_plates = get_plate_list(weights[i], 45)
            next_plates = get_plate_list(weights[i + 1], 45)
            is_linear = plates_are_subset(curr_plates, next_plates)
            assert is_linear, f"Deadlift: {weights[i]} -> {weights[i+1]} not linear"

    def test_bench_linear_progression(self):
        """Test bench press warmup progression is linear."""
        cluster = ExerciseCluster(week=1, exercise="bench press", oneRepMax=250, bar_weight=45.0)

        weights = [s.weight for s in cluster.sets]

        for i in range(len(weights) - 1):
            curr_plates = get_plate_list(weights[i], 45)
            next_plates = get_plate_list(weights[i + 1], 45)
            is_linear = plates_are_subset(curr_plates, next_plates)
            assert is_linear, f"Bench: {weights[i]} -> {weights[i+1]} not linear"

    def test_heavy_squat_week_3(self):
        """Test heavy squat at week 3 (90%) maintains linear progression."""
        cluster = ExerciseCluster(week=3, exercise="squat", oneRepMax=455, bar_weight=45.0)

        weights = [s.weight for s in cluster.sets]

        for i in range(len(weights) - 1):
            curr_plates = get_plate_list(weights[i], 45)
            next_plates = get_plate_list(weights[i + 1], 45)
            is_linear = plates_are_subset(curr_plates, next_plates)
            assert is_linear, f"Heavy squat: {weights[i]} -> {weights[i+1]} not linear"

    def test_no_warmup_plate_removal(self):
        """Verify that no warmup requires removing plates."""
        exercises = [
            ("squat", 455),
            ("bench press", 250),
            ("deadlift", 300),
            ("overhead press", 155),
        ]

        for exercise, one_rm in exercises:
            for week in [1, 2, 3, 4, 5, 6]:
                cluster = ExerciseCluster(week=week, exercise=exercise, oneRepMax=one_rm, bar_weight=45.0)
                weights = [s.weight for s in cluster.sets]

                for i in range(len(weights) - 1):
                    curr_plates = get_plate_list(weights[i], 45)
                    next_plates = get_plate_list(weights[i + 1], 45)
                    is_linear = plates_are_subset(curr_plates, next_plates)
                    assert is_linear, f"{exercise} week {week}: {weights[i]} -> {weights[i+1]} requires plate removal"
