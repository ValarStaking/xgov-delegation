from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
)


def assert_registry_config(
    delegation_registry_client: DelegationRegistryClient,
    *,
    manager_address: str,
    xgov_registry_app: int,
    vote_fees: int,
    representative_fee: int,
    vote_trigger_award: int,
    paused_registry: int,
    votes_left: int,
    trigger_fund: int,
) -> None:
    global_state = delegation_registry_client.state.global_state
    assert global_state.manager_address == manager_address
    assert global_state.xgov_registry_app == xgov_registry_app
    assert global_state.vote_fees == vote_fees
    assert global_state.representative_fee == representative_fee
    assert global_state.vote_trigger_award == vote_trigger_award
    assert global_state.paused_registry == paused_registry
    assert global_state.votes_left == votes_left
    assert global_state.trigger_fund == trigger_fund
