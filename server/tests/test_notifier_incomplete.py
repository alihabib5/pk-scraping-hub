"""A run that stopped short must say so in its email, not announce a clean finish."""

import pytest

from app.core import exports, run_manager
from app.services import notifier


@pytest.fixture
def sent(monkeypatch):
    mails = []
    monkeypatch.setattr(notifier, "_recipients", lambda: ["a@example.test"])
    monkeypatch.setattr(run_manager, "get_run", lambda run_id: {"run_id": run_id})
    monkeypatch.setattr(exports, "excel_bytes", lambda run: (b"x", "f.xlsx"))
    monkeypatch.setattr(notifier, "_send_email", lambda to, subject, body, data, name: mails.append((subject, body)))
    return mails


def test_a_clean_run_is_announced_as_complete(sent):
    notifier._notify("r1", "punjab", 5)
    assert "Complete" in sent[0][0] and "Incomplete" not in sent[0][1]


def test_an_incomplete_run_says_so_in_the_subject_and_body(sent):
    notifier._notify("r1", "punjab", 5, "Stopped at page 3 <b>of</b> 9")
    subject, body = sent[0]
    assert "INCOMPLETE" in subject and "Complete —" not in subject
    assert "Stopped at page 3 &lt;b&gt;of&lt;/b&gt; 9" in body
