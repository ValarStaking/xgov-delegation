import pytest
from algokit_utils import SigningAccount
from algosdk.error import AlgodHTTPError
from artifacts.voter.voter_client import VoterClient

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    GetVoterAppIdArgs,
)


def test_get_voter_app_id_exists_success(
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    xgov_address = voter.state.global_state.xgov_address
    result = delegation_registry_client.send.get_voter_app_id(
        args=GetVoterAppIdArgs(xgov_address=xgov_address)
    )
    get_voter_id, exists = result.abi_return

    state_voter_id = delegation_registry_client.state.box.voters_box.get_value(
        xgov_address
    )

    assert exists
    assert get_voter_id == state_voter_id


def test_get_xgov_box_not_exists_success(
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    result = delegation_registry_client.send.get_voter_app_id(
        args=GetVoterAppIdArgs(xgov_address=no_role_account.address)
    )
    get_voter_id, exists = result.abi_return

    assert get_voter_id == 0

    with pytest.raises(AlgodHTTPError, match="box not found"):
        delegation_registry_client.state.box.voters_box.get_value(
            no_role_account.address
        )
