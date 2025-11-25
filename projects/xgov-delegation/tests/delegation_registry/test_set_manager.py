import pytest
from algokit_utils import CommonAppCallParams, LogicError, SigningAccount

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    SetManagerArgs,
)
from smart_contracts.errors import std_errors as err


def test_set_manager_uninitialized_success(
    no_role_account: SigningAccount,
    delegation_registry_client_uninitialized: DelegationRegistryClient,
) -> None:
    delegation_registry_client_uninitialized.send.set_manager(
        args=SetManagerArgs(manager=no_role_account.address)
    )
    assert (
        delegation_registry_client_uninitialized.state.global_state.manager_address
        == no_role_account.address
    )


def test_set_manager_success(
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    delegation_registry_client.send.set_manager(
        args=SetManagerArgs(manager=no_role_account.address)
    )
    assert (
        delegation_registry_client.state.global_state.manager_address
        == no_role_account.address
    )


def test_set_xgov_manager_not_manager(
    no_role_account: SigningAccount,
    delegation_registry_client_uninitialized: DelegationRegistryClient,
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        delegation_registry_client_uninitialized.send.set_manager(
            args=SetManagerArgs(manager=no_role_account.address),
            params=CommonAppCallParams(sender=no_role_account.address),
        )
