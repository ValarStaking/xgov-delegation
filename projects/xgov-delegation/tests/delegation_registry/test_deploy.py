from algokit_utils import SigningAccount

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
)
from smart_contracts.artifacts.xgov_registry_mock.xgov_registry_mock_client import (
    XgovRegistryMockClient,
)


def test_deploy_registry(
    delegation_registry_client_uninitialized: DelegationRegistryClient,
    xgov_registry_mock_client: XgovRegistryMockClient,
    deployer: SigningAccount,
) -> None:
    assert (
        delegation_registry_client_uninitialized.state.global_state.manager_address
        == deployer.address
    )
    assert (
        delegation_registry_client_uninitialized.state.global_state.xgov_registry_app
        == xgov_registry_mock_client.app_id
    )
    assert (
        delegation_registry_client_uninitialized.state.global_state.paused_registry == 1
    )
    assert delegation_registry_client_uninitialized.state.global_state.votes_left == 0
    assert delegation_registry_client_uninitialized.state.global_state.trigger_fund == 0
