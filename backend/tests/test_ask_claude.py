"""Claude is reserved for Ask; SDK checks use synthetic credentials without network."""
import sys
from types import SimpleNamespace as NS

from odin.llm import factory
from odin.llm import call
from langchain_core.messages import AIMessage
from pydantic import BaseModel


def test_only_ask_can_route_to_claude_by_default(monkeypatch):
    monkeypatch.setattr(factory, 'settings', lambda: NS(odin_force_provider=''))
    monkeypatch.setattr(factory, 'provider_available', lambda name: True)
    assert factory.chain_for('ask') == ['anthropic']
    assert factory.model_for('ask', 'anthropic') == 'claude-sonnet-5-5'
    for agent in ('odin', 'thor', 'norns', 'loki', 'heimdall', 'tyr', 'synth', 'email_parse'):
        assert 'anthropic' not in factory.chain_for(agent)


def test_sonnet_constructor_omits_unsupported_temperature(monkeypatch):
    monkeypatch.setitem(sys.modules, 'langchain_anthropic', NS(ChatAnthropic=lambda **kw: NS(kwargs=kw)))
    monkeypatch.setattr(factory, 'provider_cfg', lambda name: {
        'kind': 'anthropic', 'model': 'claude-sonnet-5-5', 'api_key': 'synthetic-test-key'})
    model = factory.chat_model.__wrapped__('anthropic', max_tokens=2048)
    assert model.kwargs['model'] == 'claude-sonnet-5-5'
    assert model.kwargs['max_tokens'] == 2048
    assert 'temperature' not in model.kwargs


def test_claude_uses_native_json_instead_of_forced_tool_output(monkeypatch):
    class Answer(BaseModel):
        ok: bool
    class Model:
        def with_structured_output(self, schema, **kwargs):
            assert kwargs['method'] == 'json_schema'
            assert kwargs['include_raw'] is True
            return NS(invoke=lambda *a, **k: {'raw': AIMessage(content='{"ok":true}'), 'parsed': Answer(ok=True)})
    monkeypatch.setattr(call, 'chain_for', lambda agent: ['anthropic'])
    monkeypatch.setattr(call, 'chat_model', lambda *a, **k: Model())
    monkeypatch.setattr(call, 'price', lambda *a: 0)
    assert call.structured('ask', Answer, 'system', 'question').ok
