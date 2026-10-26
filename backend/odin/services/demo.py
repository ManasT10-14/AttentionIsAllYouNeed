"""Legacy demo controls delegate to the official pack and its staged simulation."""
from odin.core.context import run_ctx
from odin.services import bundle, simulation, runs


def seed(company_id: str, analyze: bool = True) -> dict:
    return bundle.import_bundle(company_id, analyze=analyze)


def play(company_id: str, delay_seconds: float = 20) -> dict:
    """Compatibility endpoint; events are assessed sequentially instead of a timed sample email feed."""
    with run_ctx(company_id):
        s = simulation.state()
        next_date = next((d for d in s["checkpoints"] if d > s["sim_now"]), None)
    if not next_date:
        return {"queued": 0, "status": "complete"}
    if 1 not in s["drops_loaded"]:
        simulation.load_drop(company_id, 1)
    if next_date > s["checkpoints"][0] and 2 not in s["drops_loaded"]:
        simulation.load_drop(company_id, 2)
    from datetime import date
    def go(run_id):
        simulation.advance(company_id, date.fromisoformat(next_date))
        with run_ctx(company_id):
            incomplete = any(e.get("status") in ("received", "processing", "needs_review") or e.get("impact_review_required") for e in bundle.repo.query("event"))
        return "partial" if incomplete else "done"
    return {"run_id": runs.start(company_id, "simulation", go), "until": next_date}
