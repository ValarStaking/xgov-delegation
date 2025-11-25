import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError
from artifacts.representative.representative_client import RepresentativeClient

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
)
from smart_contracts.common import constants as const
from smart_contracts.errors import std_errors as err


def test_unregister_representative_success(
    algorand_client: AlgorandClient,
    representative: RepresentativeClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:

    representative_address = representative.state.global_state.representative_address
    delegation_registry_client.send.unregister_representative(
        params=CommonAppCallParams(
            sender=representative_address,
            extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
        ),
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        delegation_registry_client.state.box.representatives_box.get_value(
            representative_address
        )

    with pytest.raises(Exception, match="application does not exist"):
        algorand_client.client.algod.application_info(representative.app_id)


def test_unregister_representative_paused_register(
    representative: RepresentativeClient,
    delegation_registry_client_paused: DelegationRegistryClient,
) -> None:
    with pytest.raises(LogicError, match=err.PAUSED_REGISTRY):
        delegation_registry_client_paused.send.unregister_representative(
            params=CommonAppCallParams(
                sender=representative.state.global_state.representative_address,
                extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
            ),
        )


def test_unregister_representative_not_representative(
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:

    with pytest.raises(LogicError, match=err.NOT_REPRESENTATIVE):
        delegation_registry_client.send.unregister_representative(
            params=CommonAppCallParams(
                sender=no_role_account.address,
                extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
            ),
        )
