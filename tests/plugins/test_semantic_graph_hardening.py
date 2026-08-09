from __future__ import annotations

import json
from pathlib import Path

import pytest

from plugins.semantic_graph import graph
from plugins.semantic_graph.exporter import export_graph
from plugins.semantic_graph.retrieval import search_and_rank
from plugins.semantic_graph.runtime import SemanticGraphRuntime
from plugins.semantic_graph.sanitize import sanitize_metadata, sanitize_text


from plugins.semantic_graph.store import SemanticGraphStore


def store(tmp_path: Path) -> SemanticGraphStore:
    s = SemanticGraphStore(tmp_path / "semantic.db")
    s.ensure_ready()
    return s


def node(identity: str, label: str, *, authority="assistant", status="candidate"):
    return {
        "temp_id": identity,
        "node_type": "Preference",
        "label": label,
        "summary": label,
        "identity_key": identity,
        "status": status,
        "authority": authority,
        "confidence": 0.9,
        "salience": 0.8,
        "evidence": [],
    }


def test_secret_redaction_never_leaves_values():
    cases = [
        "Authorization: Bearer shortsecret",
        '{"api_key":"sk-secret-value"}',
        '{"token": "opaque-secret"}',
        'api_key="sk-secret-value"',
        "token: 'opaque-secret'",
    ]
    for raw in cases:
        cleaned = sanitize_text(raw, max_chars=500).text
        assert "shortsecret" not in cleaned
        assert "secret-value" not in cleaned
        assert "opaque-secret" not in cleaned


def test_metadata_secret_keys_redact_values():
    cleaned = sanitize_metadata(
        {
            "secret": "opaque-secret",
            "authorization": "Bearer opaque-token",
            "nested": {"access_token": "nested-secret"},
            "safe": "visible",
        }
    )
    encoded = json.dumps(cleaned, ensure_ascii=False)
    assert "opaque-secret" not in encoded
    assert "opaque-token" not in encoded
    assert "nested-secret" not in encoded
    assert cleaned["safe"] == "visible"


def test_finalize_isolated_and_stable_evaluation_target(tmp_path):
    s = store(tmp_path)
    run_a = s.create_run(objective="a")["run_id"]
    run_b = s.create_run(objective="b")["run_id"]
    frag_a = {"summary":"a", "nodes":[node("a", "A")], "edges":[],
              "evaluations":[{"target_temp_id":"a","verdict":"support","score":1,"criteria":{},"notes":""}]}
    frag_b = {"summary":"b", "nodes":[node("b", "B")], "edges":[], "evaluations":[]}
    ra = graph.apply_fragment_to_store(s, run_a, frag_a, producer_role="x")
    rb = graph.apply_fragment_to_store(s, run_b, frag_b, producer_role="x")
    assert ra["success"] and rb["success"]
    graph.promote_strict(s, run_a)
    assert s.get_node(ra["nodes"][0])["status"] == "accepted"
    assert s.get_node(rb["nodes"][0])["status"] == "candidate"


def test_export_run_scope(tmp_path):
    s = store(tmp_path)
    a = s.create_run(objective="a")["run_id"]
    b = s.create_run(objective="b")["run_id"]
    fa = {"summary":"a", "nodes":[node("a", "only-a")], "edges":[]}
    fb = {"summary":"b", "nodes":[node("b", "only-b")], "edges":[]}
    graph.apply_fragment_to_store(s, a, fa, producer_role="x")
    graph.apply_fragment_to_store(s, b, fb, producer_role="x")
    out = export_graph(s, run_id=a, format="json", export_root=tmp_path / "exports")
    payload = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert [n["label"] for n in payload["nodes"]] == ["only-a"]


def test_child_subagent_hook_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    rt = SemanticGraphRuntime(config=rt_config(capture_subagents=True))
    rt.on_subagent_start(
        parent_session_id="ps", parent_turn_id="pt", child_subagent_id="child",
        child_role="leaf", child_goal="goal",
    )
    rt.on_subagent_stop(
        parent_session_id="ps", parent_turn_id="pt", child_session_id="cs",
        child_role="leaf", child_summary="done", child_status="ok", duration_ms=12,
        tool_call_history=[{"result":"sk-secret-value"}],
    )
    events = rt.store()._connect
    with rt.store()._connect() as conn:
        rows = conn.execute("select payload_json from graph_events").fetchall()
    assert any("child" in row[0] or "done" in row[0] for row in rows)
    assert all("sk-secret-value" not in row[0] for row in rows)


def rt_config(**kwargs):
    from plugins.semantic_graph.config import SemanticGraphConfig
    return SemanticGraphConfig(db_subdir="semantic-graph", **kwargs)


def test_retrieval_english_and_japanese(tmp_path):
    s = store(tmp_path)
    for ident, label in [("en", "User prefers TypeScript for frontend"), ("ja", "フロントエンドではTypeScriptを好む")]:
        s.upsert_node({"node_id":"node_"+ident,"node_type":"Preference","subtype":"",
                       "label":label,"normalized_label":label.casefold(),"summary":label,
                       "identity_key":ident,"status":"asserted","authority":"user",
                       "confidence":.95,"salience":.9})
    assert search_and_rank(s, "frontend language preference", min_confidence=.5)
    assert search_and_rank(s, "フロントは何の言語が好き？", min_confidence=.5)


def test_fragment_apply_rolls_back_on_failure(tmp_path, monkeypatch):
    s = store(tmp_path)
    run = s.create_run(objective="atomic")["run_id"]
    original = s.insert_evidence
    def fail(*args, **kwargs):
        raise RuntimeError("mid-apply")
    monkeypatch.setattr(s, "insert_evidence", fail)
    art = s.upsert_artifact({"artifact_type":"document","content":"quote","content_hash":"h",
                             "authority":"user","session_id":"s","turn_id":"t"})
    frag = {"summary":"x", "nodes":[{**node("x","quote",authority="user",status="asserted"),
             "evidence":[{"artifact_id":art["artifact_id"],"start_char":0,"end_char":5,"quote":"quote","relation":"supports","confidence":1}]}],"edges":[]}
    with pytest.raises(RuntimeError):
        graph.apply_fragment_to_store(s, run, frag, producer_role="x")
    assert s.list_fragments_for_run(run) == []
    assert s.list_nodes() == []
    monkeypatch.setattr(s, "insert_evidence", original)
    assert graph.apply_fragment_to_store(s, run, frag, producer_role="x")["success"]


def test_schema_filters_are_effective(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    rt = SemanticGraphRuntime(config=rt_config(min_recall_confidence=.1))
    s = rt.store()
    s.upsert_node({"node_id":"n","node_type":"Preference","subtype":"frontend","label":"TypeScript frontend","normalized_label":"typescript frontend","summary":"TypeScript","identity_key":"x","status":"asserted","authority":"user","confidence":.9,"salience":.9})
    result = json.loads(rt.handle_search({"query":"TypeScript","subtypes":["frontend"],"authorities":["user"]}))
    assert result["count"] == 1
    result = json.loads(rt.handle_search({"query":"TypeScript","subtypes":["other"]}))
    assert result["count"] == 0


def test_core_redactor_is_used_for_persistence(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    rt = SemanticGraphRuntime(config=rt_config(capture_turns=True, auto_extract="off"))
    rt.on_post_llm_call(session_id="s", turn_id="t", user_message="api_key=sk-secret-value", assistant_response="ok")
    raw = json.dumps(rt.store().list_artifacts())
    assert "sk-secret-value" not in raw
    assert "secret-value" not in raw
    assert "api_key" in raw
