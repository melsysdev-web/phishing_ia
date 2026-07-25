"""
Unit tests for ContentClassifierService.
The transformers pipeline is mocked so no model is loaded.
"""
from unittest.mock import MagicMock, patch

from backend.app.services.content_classifier_service import ContentClassifierService

_SHORT_TEXT = "Texto muy corto."                      # << 300 chars
_NEAR_MIN   = "A" * 299                               # 299 chars — just under threshold
_AT_MIN     = "A" * 300                               # 300 chars — exactly at threshold
_NORMAL     = "A" * 500                               # normal text
_LONG       = "A" * 2500                              # > 2000 chars


def _mock_pipeline(label: str, score: float):
    """Return a callable that mimics a transformers pipeline returning one result."""
    pipe = MagicMock()
    pipe.return_value = [{"label": label, "score": score}]
    return pipe


# ─── Threshold: _MIN_TEXT_CHARS = 300 ────────────────────────────────────────

class TestMinimumThreshold:

    def test_empty_string_returns_no_content(self):
        result = ContentClassifierService.analyze("")
        assert result["verdict"] == "no_content"

    def test_whitespace_only_returns_no_content(self):
        result = ContentClassifierService.analyze("   \n\t  ")
        assert result["verdict"] == "no_content"

    def test_text_under_300_returns_no_content(self):
        result = ContentClassifierService.analyze(_SHORT_TEXT)
        assert result["verdict"] == "no_content"

    def test_text_299_chars_returns_no_content(self):
        result = ContentClassifierService.analyze(_NEAR_MIN)
        assert result["verdict"] == "no_content"

    def test_no_content_has_unknown_label(self):
        result = ContentClassifierService.analyze(_SHORT_TEXT)
        assert result["label"] == "UNKNOWN"

    def test_no_content_has_zero_confidence(self):
        result = ContentClassifierService.analyze(_SHORT_TEXT)
        assert result["confidence"] == 0.0

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_text_exactly_300_chars_is_classified(self, mock_load):
        mock_load.return_value = _mock_pipeline("REAL", 0.9)
        result = ContentClassifierService.analyze(_AT_MIN)
        assert result["verdict"] != "no_content"
        mock_load.assert_called_once()

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_text_over_300_chars_is_classified(self, mock_load):
        mock_load.return_value = _mock_pipeline("REAL", 0.88)
        result = ContentClassifierService.analyze(_NORMAL)
        assert result["verdict"] != "no_content"


# ─── Truncation at _MAX_TEXT_CHARS = 2000 ────────────────────────────────────

class TestMaxTruncation:

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_text_over_2000_is_truncated_before_pipeline(self, mock_load):
        pipe = _mock_pipeline("REAL", 0.9)
        mock_load.return_value = pipe
        ContentClassifierService.analyze(_LONG)
        called_text = pipe.call_args[0][0]
        assert len(called_text) == 2000

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_text_under_2000_is_not_truncated(self, mock_load):
        pipe = _mock_pipeline("FAKE", 0.8)
        mock_load.return_value = pipe
        text = "B" * 800
        ContentClassifierService.analyze(text)
        called_text = pipe.call_args[0][0]
        assert len(called_text) == 800


# ─── Label normalization ──────────────────────────────────────────────────────

class TestLabelNormalization:

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_real_label_stays_real(self, mock_load):
        mock_load.return_value = _mock_pipeline("REAL", 0.92)
        result = ContentClassifierService.analyze(_NORMAL)
        assert result["label"] == "REAL"
        assert result["verdict"] == "real"

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_fake_label_stays_fake(self, mock_load):
        mock_load.return_value = _mock_pipeline("FAKE", 0.87)
        result = ContentClassifierService.analyze(_NORMAL)
        assert result["label"] == "FAKE"
        assert result["verdict"] == "fake"

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_true_label_normalized_to_real(self, mock_load):
        """Remote model (hamzab) returns TRUE/FALSE instead of REAL/FAKE."""
        mock_load.return_value = _mock_pipeline("TRUE", 0.95)
        result = ContentClassifierService.analyze(_NORMAL)
        assert result["label"] == "REAL"
        assert result["verdict"] == "real"

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_false_label_normalized_to_fake(self, mock_load):
        mock_load.return_value = _mock_pipeline("FALSE", 0.78)
        result = ContentClassifierService.analyze(_NORMAL)
        assert result["label"] == "FAKE"
        assert result["verdict"] == "fake"

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_raw_label_preserved(self, mock_load):
        mock_load.return_value = _mock_pipeline("TRUE", 0.91)
        result = ContentClassifierService.analyze(_NORMAL)
        assert result["raw_label"] == "TRUE"


# ─── Response shape ───────────────────────────────────────────────────────────

class TestResponseShape:

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_success_response_has_required_keys(self, mock_load):
        mock_load.return_value = _mock_pipeline("REAL", 0.9)
        result = ContentClassifierService.analyze(_NORMAL)
        assert {"verdict", "label", "confidence", "raw_label"}.issubset(result.keys())

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_confidence_is_float_in_range(self, mock_load):
        mock_load.return_value = _mock_pipeline("FAKE", 0.76)
        result = ContentClassifierService.analyze(_NORMAL)
        assert 0.0 <= result["confidence"] <= 1.0

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_confidence_rounded_to_4_decimals(self, mock_load):
        mock_load.return_value = _mock_pipeline("REAL", 0.123456789)
        result = ContentClassifierService.analyze(_NORMAL)
        # round(0.123456789, 4) = 0.1235
        assert result["confidence"] == round(0.123456789, 4)

    def test_no_content_response_has_required_keys(self):
        result = ContentClassifierService.analyze(_SHORT_TEXT)
        assert {"verdict", "label", "confidence"}.issubset(result.keys())


# ─── Error handling ───────────────────────────────────────────────────────────

class TestErrorHandling:

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_pipeline_exception_returns_error_dict(self, mock_load):
        pipe = MagicMock(side_effect=RuntimeError("CUDA out of memory"))
        mock_load.return_value = pipe
        result = ContentClassifierService.analyze(_NORMAL)
        assert "error" in result
        assert "CUDA out of memory" in result["error"]

    @patch("backend.app.services.content_classifier_service._load_pipeline")
    def test_pipeline_exception_does_not_raise(self, mock_load):
        pipe = MagicMock(side_effect=Exception("unexpected"))
        mock_load.return_value = pipe
        result = ContentClassifierService.analyze(_NORMAL)   # must not raise
        assert "error" in result
