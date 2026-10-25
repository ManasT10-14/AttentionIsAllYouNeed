"""Ask Odin — Q&A over contracts with verified citations (refuses without evidence)."""
from __future__ import annotations

from odin.agents.base import j, prompt
from odin.core import citations
from odin.core.config import odin_config
from odin.core.context import run_ctx
from odin.core.models import AskAnswer
from odin.llm.call import structured
from odin.retrieval import hybrid


def ask(company_id: str, question: str, contract_ids: list[str] | None = None) -> dict:
    with run_ctx(company_id, agent="ask"):
        queries = [question]
        if odin_config()["retrieval"].get("multi_query"):
            from pydantic import BaseModel

            class Q(BaseModel):
                queries: list[str]
            queries += structured("ask", Q, "Rewrite the question into 3 short search queries for contract clauses.",
                                  question).queries[:3]
        seen, hits = set(), []
        for q in queries:
            for h in hybrid.search(q, contract_ids=contract_ids):
                if h.clause_id not in seen:
                    seen.add(h.clause_id)
                    hits.append(h)
        passages = [h.as_dict(1500) for h in hits[:12]]
        ans = structured("ask", AskAnswer, prompt("ask"),
                         f"Question: {question}\n\n<document contract_id=\"multiple\">\n{j(passages)}\n</document>",
                         tools=["get_clause", "hybrid_search"])
        ans.citations = citations.verify_all(ans.citations)
        if ans.citations and not any(c.verified for c in ans.citations):
            ans.insufficient_evidence = True
            ans.answer = "I could not verify any supporting clause for this answer. " + ans.answer
        return {**ans.model_dump(mode="json"), "passages": passages}
