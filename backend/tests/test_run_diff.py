from odin.services.runs import diff_states


def _st(findings, actions, exp):
    return {"findings": {k: {"contract_id": "C", "claim": k} for k in findings},
            "actions": {k: {"contract_id": "C", "subject": k} for k in actions},
            "exposure": {"expected": exp[0], "worst_case": exp[1], "currency": "INR"}}


def test_first_run_everything_new():
    d = diff_states(None, _st(["a"], ["x"], (1, 2)))
    assert d["first_run"] and len(d["new_findings"]) == 1 and d["exposure_delta"] is None


def test_new_resolved_and_exposure_delta():
    d = diff_states(_st(["a", "b"], ["x"], (100, 200)), _st(["b", "c"], ["y"], (150, 180)))
    assert [f["claim"] for f in d["new_findings"]] == ["c"]
    assert [f["claim"] for f in d["resolved_findings"]] == ["a"]
    assert [a["subject"] for a in d["new_actions"]] == ["y"] and [a["subject"] for a in d["resolved_actions"]] == ["x"]
    assert d["exposure_delta"] == {"expected": 50, "worst_case": -20, "currency": "INR"}
