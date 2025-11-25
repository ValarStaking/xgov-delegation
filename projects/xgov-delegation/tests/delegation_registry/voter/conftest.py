import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    PaymentParams,
)
from artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    RegisterRepresentativeArgs,
)
from common.helpers import get_sc_representative_mbr

from smart_contracts.artifacts.representative.representative_client import (
    RepresentativeClient,
)
from smart_contracts.common import constants as const
from tests.common import INITIAL_FUNDS


@pytest.fixture(scope="function")
def representative2(
    algorand_client: AlgorandClient,
    delegation_registry_client: DelegationRegistryClient,
) -> RepresentativeClient:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    representative_address = account.address

    pay_amount = (
        get_sc_representative_mbr()
        + delegation_registry_client.state.global_state.representative_fee
    )
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=representative_address,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    result = delegation_registry_client.send.register_representative(
        args=RegisterRepresentativeArgs(
            payment=pay_txn,
        ),
        params=CommonAppCallParams(
            sender=representative_address,
            extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
        ),
    )

    client = algorand_client.client.get_typed_app_client_by_id(
        typed_client=RepresentativeClient, app_id=result.abi_return
    )

    return client
