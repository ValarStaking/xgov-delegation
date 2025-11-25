import pytest
from algokit_utils import SigningAccount
from algosdk.error import AlgodHTTPError
from artifacts.representative.representative_client import RepresentativeClient

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    GetRepresentativeAppIdArgs,
)


def test_get_representative_app_id_exists_success(
    representative: RepresentativeClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    representative_address = representative.state.global_state.representative_address
    result = delegation_registry_client.send.get_representative_app_id(
        args=GetRepresentativeAppIdArgs(representative_address=representative_address)
    )
    get_representative_id, exists = result.abi_return

    state_representative_id = (
        delegation_registry_client.state.box.representatives_box.get_value(
            representative_address
        )
    )

    assert exists
    assert get_representative_id == state_representative_id


def test_get_representative_box_not_exists_success(
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    representative_address = no_role_account.address
    result = delegation_registry_client.send.get_representative_app_id(
        args=GetRepresentativeAppIdArgs(representative_address=representative_address)
    )
    get_representative_id, exists = result.abi_return

    assert get_representative_id == 0

    with pytest.raises(AlgodHTTPError, match="box not found"):
        delegation_registry_client.state.box.voters_box.get_value(
            no_role_account.address
        )
