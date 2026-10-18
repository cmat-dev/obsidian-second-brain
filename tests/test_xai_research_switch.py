"""OSB_XAI_RESEARCH switches every xAI (Grok) call off with one setting.

Some users cannot or will not send research to xAI: cost, data residency, or a
policy on which providers may see vault material. Before this switch the only
way to stop it was to edit grok.py, and /youtube and /podcast fell back to
Grok whenever Gemini failed. What is pinned here: with the switch off no
request is made, /research-deep records X queries as skipped rather than
failed, the summarisers stop instead of falling back, and the default is on.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))


@pytest.mark.parametrize("value", ["0", "false", "OFF", " no "])
def test_off_values_switch_it_off(monkeypatch, value):
    from research.lib import config

    monkeypatch.setenv("OSB_XAI_RESEARCH", value)
    assert config.xai_research_enabled() is False


@pytest.mark.parametrize("value", [None, "", "1", "true", "on"])
def test_it_is_on_by_default_and_for_anything_else(monkeypatch, value):
    from research.lib import config

    if value is None:
        monkeypatch.delenv("OSB_XAI_RESEARCH", raising=False)
    else:
        monkeypatch.setenv("OSB_XAI_RESEARCH", value)
    assert config.xai_research_enabled() is True


def test_grok_call_refuses_before_any_request(monkeypatch):
    from research.lib import grok

    def no_network(*args, **kwargs):
        raise AssertionError("a request was made with xAI research off")

    monkeypatch.setattr(grok.requests, "post", no_network)
    monkeypatch.setattr(grok, "XAI_API_KEY", lambda: pytest.fail("the key was read"))
    monkeypatch.setenv("OSB_XAI_RESEARCH", "0")
    with pytest.raises(grok.XaiResearchDisabled, match="OSB_XAI_RESEARCH"):
        grok.call("hello", command="test")


def test_summarisers_stop_instead_of_falling_back_to_grok():
    """Both Gemini-first summarisers check the switch before their Grok fallback."""
    for name in ("youtube_extract.py", "podcast_extract.py"):
        source = (REPO_ROOT / "scripts" / "research" / name).read_text(encoding="utf-8")
        guard = source.index("if result is None and not config.xai_research_enabled():")
        fallback = source.index("grok.call(")
        assert guard < fallback, f"{name} reaches grok.call before checking the switch"


class _StopAtSynthesis(BaseException):
    """BaseException: Phase 4's own `except Exception` must not swallow it."""


def test_research_deep_skips_x_queries_when_off(monkeypatch):
    from research import research_deep
    from research.lib import grok, perplexity, web_reader

    monkeypatch.setenv("OSB_XAI_RESEARCH", "0")
    monkeypatch.setattr(research_deep, "vault_scan", lambda topic: [])
    monkeypatch.setattr(research_deep, "load_baseline", lambda hits: "")
    monkeypatch.setattr(research_deep, "parse_queries",
                        lambda text: [("what do people say", "x"), ("what is new", "web")])
    monkeypatch.setattr(web_reader, "available", lambda: False)
    monkeypatch.setattr(grok, "call", lambda *a, **k: pytest.fail("grok.call reached"))
    seen = {}

    def fake_perplexity(prompt, **kwargs):
        if kwargs.get("model") == "sonar-reasoning-pro":  # Phase 4: inspect, then stop
            seen["findings"] = prompt
            raise _StopAtSynthesis
        return {"text": "gaps", "citations": []}

    monkeypatch.setattr(perplexity, "call", fake_perplexity)
    with pytest.raises(_StopAtSynthesis):
        research_deep.run_paid_deep("topic")
    assert "[SKIPPED: xAI research is off (OSB_XAI_RESEARCH=0)]" in seen["findings"]
    assert "FAILED" not in seen["findings"], "a switched-off source is not a failure"
    assert "### Web - what is new" in seen["findings"], "web queries still run"


@pytest.mark.skipif(sys.platform == "win32", reason="install.sh is exercised under bash on POSIX")
def test_installer_skips_x_commands_when_off(tmp_path):
    home = tmp_path / "home"
    (home / ".claude" / "commands").mkdir(parents=True)
    (home / ".claude" / "skills").mkdir(parents=True)
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "OSB_XAI_RESEARCH": "0"}
    subprocess.run(
        ["bash", str(REPO_ROOT / "install.sh")], input="n\n", text=True,
        env=env, cwd=REPO_ROOT, capture_output=True, timeout=120,
    )
    installed = {p.name for p in (home / ".claude" / "commands").iterdir()}
    assert "research.md" in installed, "the installer ran"
    assert "x-read.md" not in installed and "x-pulse.md" not in installed
