import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
)
from artifacts.representative.representative_client import RepresentativeClient
from common.helpers import get_sc_representative_mbr

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    RegisterRepresentativeArgs,
)
from smart_contracts.common import constants as const
from smart_contracts.errors import std_errors as err
from tests.common import INITIAL_FUNDS


def test_register_representative_success(
    algorand_client: AlgorandClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
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

    representative_id = result.abi_return
    assert representative_id
    assert (
        delegation_registry_client.state.box.representatives_box.get_value(
            representative_address
        )
        == representative_id
    )

    representative = algorand_client.client.get_typed_app_client_by_id(
        typed_client=RepresentativeClient, app_id=representative_id
    )

    assert (
        representative.state.global_state.registry_app
        == delegation_registry_client.app_id
    )
    assert representative.state.global_state.paused == 0
    assert (
        representative.state.global_state.representative_address
        == representative_address
    )


def test_register_representative_paused_register(
    algorand_client: AlgorandClient,
    delegation_registry_client_paused: DelegationRegistryClient,
) -> None:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    representative_address = account.address

    pay_amount = (
        get_sc_representative_mbr()
        + delegation_registry_client_paused.state.global_state.representative_fee
    )
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=representative_address,
            receiver=delegation_registry_client_paused.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.PAUSED_REGISTRY):
        delegation_registry_client_paused.send.register_representative(
            args=RegisterRepresentativeArgs(
                payment=pay_txn,
            ),
            params=CommonAppCallParams(
                sender=representative_address,
                extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
            ),
        )


def test_register_representative_already_representative(
    algorand_client: AlgorandClient,
    representative: RepresentativeClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    representative_address = representative.state.global_state.representative_address

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

    with pytest.raises(LogicError, match=err.ALREADY_REPRESENTATIVE):
        delegation_registry_client.send.register_representative(
            args=RegisterRepresentativeArgs(
                payment=pay_txn,
            ),
            params=CommonAppCallParams(
                sender=representative_address,
                extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
            ),
        )


def test_register_representative_wrong_receiver(
    algorand_client: AlgorandClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
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
            receiver=representative_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.WRONG_RECEIVER):
        delegation_registry_client.send.register_representative(
            args=RegisterRepresentativeArgs(
                payment=pay_txn,
            ),
            params=CommonAppCallParams(
                sender=representative_address,
                extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
            ),
        )


def test_register_representative_wrong_amount(
    algorand_client: AlgorandClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    representative_address = account.address

    pay_amount = (
        get_sc_representative_mbr()
        + delegation_registry_client.state.global_state.representative_fee
    ) - 1
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=representative_address,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.WRONG_PAYMENT_AMOUNT):
        delegation_registry_client.send.register_representative(
            args=RegisterRepresentativeArgs(
                payment=pay_txn,
            ),
            params=CommonAppCallParams(
                sender=representative_address,
                extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
            ),
        )
