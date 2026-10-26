"""An in-flight approved effect freezes its linked decision basis through repository writes."""
import pytest
from odin.core.context import run_ctx
from odin.db import repo, session
from odin.db.tables import Record
from odin.services import approvals
from odin.tools.registry import ApprovalRequired
from pydantic import BaseModel
from test_action_approvals import payload, store  # noqa: F401 -- shared disposable DB fixture


class Basis(BaseModel):
    id: str = "basis"
    status: str = "dismissed"
    amount: int = 0


@pytest.mark.parametrize("write", ["status", "put", "invalidate"])
@pytest.mark.usefixtures("store")
def test_repository_cannot_change_basis_of_executing_action(write):
    with run_ctx("a", user_role="admin"):
        with session.db() as db:
            db.add(Record(id="a|basis", company_id="a", kind="violation", contract_id="C01", status="confirmed",
                          data={"id": "basis", "status": "confirmed", "amount": 100}))
        repo.set_status("act", "draft", related_violation_ids=["basis"])
        approvals.approve("act", reviewer="admin@aurora.test")
        approvals.claim("act", "send_gmail", {**payload(), "thread_id": None})
        with pytest.raises(ApprovalRequired):
            if write == "status":
                repo.set_status("basis", "dismissed", amount=0)
            elif write == "put":
                repo.put("violation", Basis(), contract_id="C01")
            else:
                repo.invalidate(["violation"], "C01")
        assert repo.get("violation", "basis") == {"id": "basis", "status": "confirmed", "amount": 100}
