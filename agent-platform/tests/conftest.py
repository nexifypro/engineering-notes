import pytest

from agentkit import issue_token
from servers import appointments, medications


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def fresh_stores():
    appointments.reset_store()
    medications.reset_store()
    yield


@pytest.fixture
def token():
    return issue_token("pat-1")


@pytest.fixture
def other_token():
    return issue_token("pat-2")


def meta_for(token: str) -> dict:
    return {"authorization": f"Bearer {token}"}
