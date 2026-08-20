"""Tests para el almacén de correcciones de usuario."""

import tempfile
from pathlib import Path

import pytest

from backend.app.services import feedback_store


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    """Cada test escribe en su propia base, no en la del repo."""
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(feedback_store, "_db_path", Path(tmp) / "feedback.db")
        monkeypatch.setattr(feedback_store, "_initialized", False)
        yield


def _record(url="https://example.com", predicted="HIGH", score=20, reported="LOW", **kw):
    return feedback_store.record(
        url=url,
        predicted_risk=predicted,
        predicted_score=score,
        reported_risk=reported,
        **kw,
    )


class TestRecording:
    def test_valid_correction_is_persisted(self):
        assert _record() is True
        assert feedback_store.stats()["total"] == 1

    def test_multiple_corrections_accumulate(self):
        for i in range(5):
            _record(url=f"https://site{i}.com")
        assert feedback_store.stats()["total"] == 5

    def test_optional_fields_are_stored(self):
        _record(confidence=0.85, variant="candidate")
        row = feedback_store.export_training_rows()[0]
        assert row["confidence"] == 0.85
        assert row["variant"] == "candidate"

    def test_missing_optional_fields_are_null(self):
        _record()
        row = feedback_store.export_training_rows()[0]
        assert row["confidence"] is None
        assert row["variant"] is None


class TestUrlPrivacy:
    def test_url_is_not_stored_in_clear(self):
        url = "https://banco-privado.example.com/cuenta"
        _record(url=url)
        row = feedback_store.export_training_rows()[0]
        assert url not in row["url_hash"]
        assert "banco-privado" not in row["url_hash"]

    def test_same_url_hashes_consistently(self):
        assert feedback_store.hash_url("https://a.com") == feedback_store.hash_url(
            "https://a.com"
        )

    def test_different_urls_hash_differently(self):
        assert feedback_store.hash_url("https://a.com") != feedback_store.hash_url(
            "https://b.com"
        )


class TestLabelValidation:
    def test_invalid_reported_label_is_rejected(self):
        assert _record(reported="TOTALLY_BOGUS") is False
        assert feedback_store.stats()["total"] == 0

    def test_empty_reported_label_is_rejected(self):
        assert _record(reported="") is False

    @pytest.mark.parametrize("label", ["LOW", "MEDIUM", "HIGH"])
    def test_all_valid_labels_are_accepted(self, label):
        assert _record(reported=label) is True


class TestStats:
    def test_false_positive_is_counted(self):
        """Predijimos HIGH, el usuario dice que era seguro."""
        _record(predicted="HIGH", reported="LOW")
        assert feedback_store.stats()["false_positives"] == 1

    def test_false_negative_is_counted(self):
        """Predijimos LOW, el usuario reporta phishing."""
        _record(predicted="LOW", reported="HIGH")
        assert feedback_store.stats()["false_negatives"] == 1

    def test_false_positives_and_negatives_are_distinguished(self):
        _record(url="https://a.com", predicted="HIGH", reported="LOW")
        _record(url="https://b.com", predicted="LOW", reported="HIGH")
        stats = feedback_store.stats()
        assert stats["false_positives"] == 1
        assert stats["false_negatives"] == 1

    def test_medium_corrections_are_neither(self):
        _record(predicted="MEDIUM", reported="LOW")
        stats = feedback_store.stats()
        assert stats["false_positives"] == 0
        assert stats["false_negatives"] == 0

    def test_grouping_by_predicted_risk(self):
        _record(url="https://a.com", predicted="HIGH")
        _record(url="https://b.com", predicted="HIGH")
        _record(url="https://c.com", predicted="LOW", reported="HIGH")
        assert feedback_store.stats()["by_predicted_risk"] == {"HIGH": 2, "LOW": 1}

    def test_empty_store_reports_zeros(self):
        stats = feedback_store.stats()
        assert stats["total"] == 0
        assert stats["false_positives"] == 0
        assert stats["false_negatives"] == 0


class TestExportAndClear:
    def test_export_returns_newest_first(self):
        _record(url="https://old.com", score=10)
        _record(url="https://new.com", score=90)
        rows = feedback_store.export_training_rows()
        assert rows[0]["predicted_score"] == 90

    def test_export_respects_limit(self):
        for i in range(10):
            _record(url=f"https://site{i}.com")
        assert len(feedback_store.export_training_rows(limit=3)) == 3

    def test_clear_removes_all_rows(self):
        for i in range(4):
            _record(url=f"https://site{i}.com")
        assert feedback_store.clear() == 4
        assert feedback_store.stats()["total"] == 0
