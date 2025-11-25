import pytest
from algokit_utils import (
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
)
from smart_contracts.errors import std_errors as err


def test_pause_registry_success(
    delegation_registry_client: DelegationRegistryClient,
) -> None:

    delegation_registry_client.send.pause_registry()

    assert delegation_registry_client.state.global_state.paused_registry == 1


def test_pause_registry_not_manager(
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        delegation_registry_client.send.pause_registry(
            params=CommonAppCallParams(sender=no_role_account.address),
        )
