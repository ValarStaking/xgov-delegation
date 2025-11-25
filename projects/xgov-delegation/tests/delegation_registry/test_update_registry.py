import pytest
from algokit_utils import (
    AppClientCompilationParams,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
)
from smart_contracts.errors import std_errors as err


def test_update_registry_success(
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    delegation_registry_client.send.update.update_registry(
        compilation_params=AppClientCompilationParams(
            deploy_time_params={"entropy": b""}
        )
    )


def test_update_registry_not_manager(
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        delegation_registry_client.send.update.update_registry(
            compilation_params=AppClientCompilationParams(
                deploy_time_params={"entropy": b""}
            ),
            params=CommonAppCallParams(sender=no_role_account.address),
        )
