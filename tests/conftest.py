"""
Patches ML model loaders via sys.modules before any backend code is imported.
conftest.py is loaded first by pytest, so these patches apply to all test files.
"""
import sys
from unittest.mock import MagicMock

import numpy as np
import torch
import pytest

# ─────────────────────────────────────────────
# Mock: Random Forest model loader
# ─────────────────────────────────────────────
FEATURE_COLUMNS = [
    'URLLength', 'DomainLength', 'PathLength', 'NumDots',
    'NumHyphens', 'NumQuestionMarks', 'ContainsAtSymbol',
    'ContainsDoubleSlashRedirect', 'IsDomainIP', 'TLDLength',
    'NoOfSubDomain', 'IsHTTPS', 'HasTitle', 'HasFavicon',
    'HasDescription', 'HasPasswordField', 'HasHiddenFields',
    'NoOfImage', 'NoOfCSS', 'NoOfJS'
]

_mock_rf_model = MagicMock()
_mock_rf_model.predict.return_value = np.array([1])
_mock_rf_model.predict_proba.return_value = np.array([[0.15, 0.85]])

_mock_rf_loader = MagicMock()
_mock_rf_loader.model = _mock_rf_model
_mock_rf_loader.feature_columns = FEATURE_COLUMNS
sys.modules['backend.app.random_forest.model_loader'] = _mock_rf_loader

# ─────────────────────────────────────────────
# Mock: RoBERTa model loader
# ─────────────────────────────────────────────
_mock_logits = torch.tensor([[2.0, -1.0]])
_mock_roberta_output = MagicMock()
_mock_roberta_output.logits = _mock_logits

_mock_roberta_model = MagicMock()
_mock_roberta_model.return_value = _mock_roberta_output

_mock_tokenizer = MagicMock()
_mock_tokenizer.return_value = {
    "input_ids": torch.tensor([[0, 1, 2]]),
    "attention_mask": torch.tensor([[1, 1, 1]])
}

_mock_roberta_loader = MagicMock()
_mock_roberta_loader.model = _mock_roberta_model
_mock_roberta_loader.tokenizer = _mock_tokenizer
sys.modules['backend.app.roberta.model_loader'] = _mock_roberta_loader


# ─────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def safe_url():
    return "https://www.google.com"


@pytest.fixture
def phishing_url():
    return "http://192.168.1.1/login@paypal/verify/reset-password?account=steal"


@pytest.fixture
def url_features_safe():
    return {
        "url_length": 22,
        "domain_length": 14,
        "path_length": 1,
        "num_dots": 2,
        "num_hyphens": 0,
        "num_slashes": 2,
        "num_question_marks": 0,
        "has_https": True,
        "has_ip": False,
        "contains_at_symbol": False,
        "contains_double_slash_redirect": False,
        "num_subdomains": 1,
        "full_url": "https://www.google.com"
    }


@pytest.fixture
def url_features_phishing():
    return {
        "url_length": 90,
        "domain_length": 11,
        "path_length": 60,
        "num_dots": 5,
        "num_hyphens": 5,
        "num_slashes": 8,
        "num_question_marks": 2,
        "has_https": False,
        "has_ip": True,
        "contains_at_symbol": True,
        "contains_double_slash_redirect": True,
        "num_subdomains": 4,
        "full_url": "http://192.168.1.1/login@paypal/verify/reset-password?account=steal"
    }


@pytest.fixture
def domain_info_trusted():
    return {
        "domain": "google.com",
        "registrar": "MarkMonitor Inc.",
        "creation_date": "1997-09-15",
        "expiration_date": "2028-09-13",
        "domain_age_days": 10000,
        "tld": "com"
    }


@pytest.fixture
def domain_info_suspicious():
    return {
        "domain": "malicious.xyz",
        "registrar": "Unknown",
        "creation_date": "2026-06-01",
        "expiration_date": "2027-06-01",
        "domain_age_days": 6,
        "tld": "xyz"
    }


@pytest.fixture
def sample_html_safe():
    return """
    <html>
    <head>
        <title>Safe Page</title>
        <link rel="icon" href="/favicon.ico">
        <meta name="description" content="A safe page">
        <link rel="stylesheet" href="style.css">
        <script src="app.js"></script>
    </head>
    <body><img src="logo.png"></body>
    </html>
    """


@pytest.fixture
def sample_html_phishing():
    return """
    <html>
    <body>
        <form>
            <input type="password" name="pwd">
            <input type="hidden" name="token">
        </form>
    </body>
    </html>
    """
