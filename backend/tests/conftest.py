import pytest

from app.gateway.router import LLMGateway
from tests import fakes


@pytest.fixture(autouse=True)
def clear_scripts():
    fakes.SCRIPTS.clear()
    yield
    fakes.SCRIPTS.clear()


@pytest.fixture
def make_gateway():
    def build(names=("alpha", "beta", "gamma"), models=None, **overrides) -> LLMGateway:
        gw = LLMGateway(fakes.settings(**overrides))
        models = models or {}
        gw.providers = {n: fakes.fake_provider(n, models.get(n, ("main",))) for n in names}
        return gw

    return build
