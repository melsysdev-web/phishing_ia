"""Tests para la asignación de variantes de scoring (A/B)."""

from unittest.mock import patch

from backend.app.core import experiment


def _env(**kwargs):
    return patch.dict("os.environ", kwargs, clear=False)


class TestDefaultsOff:
    def test_experiment_is_disabled_without_configuration(self):
        with patch.dict("os.environ", {}, clear=True):
            assert experiment.assign("https://example.com") == experiment.CONTROL
            assert experiment.status()["enabled"] is False

    def test_zero_rollout_sends_everything_to_control(self):
        with _env(EXPERIMENT_ROLLOUT="0.0"):
            urls = [f"https://site{i}.com" for i in range(50)]
            assert all(experiment.assign(u) == experiment.CONTROL for u in urls)


class TestRollout:
    def test_full_rollout_sends_everything_to_variant(self):
        with _env(EXPERIMENT_ROLLOUT="1.0", EXPERIMENT_VARIANT="candidate"):
            urls = [f"https://site{i}.com" for i in range(50)]
            assert all(experiment.assign(u) == "candidate" for u in urls)

    def test_partial_rollout_splits_traffic(self):
        with _env(EXPERIMENT_ROLLOUT="0.5", EXPERIMENT_VARIANT="candidate"):
            urls = [f"https://site{i}.com" for i in range(400)]
            variant_count = sum(1 for u in urls if experiment.assign(u) == "candidate")
            # Reparto por hash: no es exacto, pero debe rondar la mitad.
            assert 140 < variant_count < 260

    def test_variant_name_is_configurable(self):
        with _env(EXPERIMENT_ROLLOUT="1.0", EXPERIMENT_VARIANT="scorer_v2"):
            assert experiment.assign("https://example.com") == "scorer_v2"


class TestDeterminism:
    def test_same_url_always_gets_same_variant(self):
        with _env(EXPERIMENT_ROLLOUT="0.5"):
            url = "https://example.com/page"
            assignments = {experiment.assign(url) for _ in range(20)}
            assert len(assignments) == 1

    def test_different_urls_can_get_different_variants(self):
        with _env(EXPERIMENT_ROLLOUT="0.5", EXPERIMENT_VARIANT="candidate"):
            urls = [f"https://site{i}.com" for i in range(200)]
            assert len({experiment.assign(u) for u in urls}) == 2


class TestMalformedConfiguration:
    def test_non_numeric_rollout_falls_back_to_disabled(self):
        with _env(EXPERIMENT_ROLLOUT="abc"):
            assert experiment.assign("https://example.com") == experiment.CONTROL

    def test_rollout_above_one_is_ignored(self):
        with _env(EXPERIMENT_ROLLOUT="5.0"):
            assert experiment.assign("https://example.com") == experiment.CONTROL

    def test_negative_rollout_is_ignored(self):
        with _env(EXPERIMENT_ROLLOUT="-1"):
            assert experiment.assign("https://example.com") == experiment.CONTROL

    def test_empty_rollout_is_ignored(self):
        with _env(EXPERIMENT_ROLLOUT=""):
            assert experiment.assign("https://example.com") == experiment.CONTROL


class TestStatus:
    def test_status_reports_active_configuration(self):
        with _env(EXPERIMENT_ROLLOUT="0.25", EXPERIMENT_VARIANT="scorer_v2"):
            status = experiment.status()
            assert status["enabled"] is True
            assert status["rollout"] == 0.25
            assert status["variant"] == "scorer_v2"
            assert status["control"] == experiment.CONTROL
