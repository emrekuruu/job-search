import json

from job_search.config import DIMENSIONS, settings
from job_search.data.sft_format import build_eval_sft, build_query_sft
from job_search.io_utils import write_jsonl


def _point_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)


def test_build_query_sft(tmp_path, monkeypatch):
    _point_data_dir(tmp_path, monkeypatch)
    write_jsonl(
        settings.dataset1_path,
        [
            {
                "id": 1,
                "category": "Finance",
                "resume": "Experienced analyst.",
                "reasoning": "think about roles",
                "queries": [{"search_term": "financial analyst", "location": "NYC"}],
            }
        ],
    )

    n = build_query_sft()
    assert n == 1

    rec = next(iter(open(settings.sft_dir / "query_gen.jsonl", encoding="utf-8")))
    msg = json.loads(rec)["messages"]
    assert [m["role"] for m in msg] == ["system", "user", "assistant"]
    assistant = msg[2]["content"]
    assert "<think>" in assistant and "think about roles" in assistant
    payload = json.loads(assistant.split("</think>")[-1])
    assert payload["queries"][0]["search_term"] == "financial analyst"


def test_build_eval_sft(tmp_path, monkeypatch):
    _point_data_dir(tmp_path, monkeypatch)
    dims = [{"name": d.name, "score": 10, "reasoning": "r"} for d in DIMENSIONS]
    write_jsonl(
        settings.dataset2_path,
        [
            {
                "resume_id": 1,
                "resume": "Experienced analyst.",
                "job": {
                    "title": "Analyst",
                    "company": "Acme",
                    "location": "NYC",
                    "description": "Do analysis.",
                    "job_url": "https://example.com/1",
                },
                "reasoning": "weigh the fit",
                "evaluation": {
                    "dimensions": dims,
                    "total": 10 * len(DIMENSIONS),
                    "overall_reasoning": "decent",
                },
            }
        ],
    )

    n = build_eval_sft()
    assert n == 1

    rec = next(iter(open(settings.sft_dir / "fit_eval.jsonl", encoding="utf-8")))
    msg = json.loads(rec)["messages"]
    assistant = msg[2]["content"]
    assert "<think>" in assistant and "weigh the fit" in assistant
    payload = json.loads(assistant.split("</think>")[-1])
    assert payload["total"] == 10 * len(DIMENSIONS)
    assert len(payload["dimensions"]) == len(DIMENSIONS)
