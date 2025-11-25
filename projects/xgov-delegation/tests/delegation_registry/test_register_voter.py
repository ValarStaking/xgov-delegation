import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SigningAccount,
)
from artifacts.representative.representative_client import RepresentativeClient
from artifacts.voter.voter_client import VoterClient
from artifacts.xgov_registry_mock.xgov_registry_mock_client import (
    XgovRegistryMockClient,
)
from common.helpers import get_sc_voter_mbr

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    RegisterVoterArgs,
)
from smart_contracts.common import constants as const
from smart_contracts.errors import std_errors as err
from smart_contracts.voter import config as voter_cfg


@pytest.mark.parametrize("account_role", ["xgov", "voting"])
def test_register_voter(
    algorand_client: AlgorandClient,
    xgov_delegated: SigningAccount,
    representative: RepresentativeClient,
    delegation_registry_client: DelegationRegistryClient,
    xgov_registry_mock_client: XgovRegistryMockClient,
    account_role: str,
) -> None:
    representative_address = representative.state.global_state.representative_address
    xgov_address = xgov_delegated.address
    if account_role == "xgov":
        sender = xgov_registry_mock_client.state.box.xgov_box.get_value(
            xgov_address
        ).voting_address
    else:
        sender = xgov_address

    pay_amount = get_sc_voter_mbr()
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    result = delegation_registry_client.send.register_voter(
        args=RegisterVoterArgs(
            payment=pay_txn,
            xgov_address=xgov_address,
            representative_address=representative_address,
            window_ts=voter_cfg.DEFAULT_WINDOW_TS,
        ),
        params=CommonAppCallParams(
            sender=sender,
            extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
        ),
    )

    voter_id = result.abi_return
    assert voter_id
    assert (
        delegation_registry_client.state.box.voters_box.get_value(xgov_address)
        == voter_id
    )

    voter = algorand_client.client.get_typed_app_client_by_id(
        typed_client=VoterClient, app_id=voter_id
    )

    assert voter.state.global_state.registry_app == delegation_registry_client.app_id
    assert voter.state.global_state.xgov_address == xgov_address
    assert voter.state.global_state.manager_address == sender
    assert (
        voter.state.global_state.representative_app
        == delegation_registry_client.state.box.representatives_box.get_value(
            representative_address
        )
    )
    assert voter.state.global_state.window_ts == voter_cfg.DEFAULT_WINDOW_TS
    assert voter.state.global_state.votes_left == 0


def test_register_voter_paused_register(
    algorand_client: AlgorandClient,
    xgov: SigningAccount,
    representative: RepresentativeClient,
    delegation_registry_client_paused: DelegationRegistryClient,
) -> None:
    representative_address = representative.state.global_state.representative_address
    xgov_address = xgov.address
    sender = xgov_address

    pay_amount = get_sc_voter_mbr()
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client_paused.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.PAUSED_REGISTRY):
        delegation_registry_client_paused.send.register_voter(
            args=RegisterVoterArgs(
                payment=pay_txn,
                xgov_address=xgov_address,
                representative_address=representative_address,
                window_ts=voter_cfg.DEFAULT_WINDOW_TS,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
            ),
        )


def test_register_voter_already_voter(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    representative: RepresentativeClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    representative_address = representative.state.global_state.representative_address
    xgov_address = voter.state.global_state.xgov_address
    sender = xgov_address

    pay_amount = get_sc_voter_mbr()
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.ALREADY_VOTER):
        delegation_registry_client.send.register_voter(
            args=RegisterVoterArgs(
                payment=pay_txn,
                xgov_address=xgov_address,
                representative_address=representative_address,
                window_ts=voter_cfg.DEFAULT_WINDOW_TS,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
            ),
        )


def test_register_voter_not_representative(
    algorand_client: AlgorandClient,
    xgov_delegated: SigningAccount,
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    representative_address = no_role_account.address
    xgov_address = xgov_delegated.address
    sender = xgov_address

    pay_amount = get_sc_voter_mbr()
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.NOT_REPRESENTATIVE):
        delegation_registry_client.send.register_voter(
            args=RegisterVoterArgs(
                payment=pay_txn,
                xgov_address=xgov_address,
                representative_address=representative_address,
                window_ts=voter_cfg.DEFAULT_WINDOW_TS,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
            ),
        )


def test_register_voter_not_xgov(
    algorand_client: AlgorandClient,
    representative: RepresentativeClient,
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    representative_address = representative.state.global_state.representative_address
    xgov_address = no_role_account.address
    sender = xgov_address

    pay_amount = get_sc_voter_mbr()
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.NOT_XGOV):
        delegation_registry_client.send.register_voter(
            args=RegisterVoterArgs(
                payment=pay_txn,
                xgov_address=xgov_address,
                representative_address=representative_address,
                window_ts=voter_cfg.DEFAULT_WINDOW_TS,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
            ),
        )


def test_register_voter_unauthorized(
    algorand_client: AlgorandClient,
    xgov: SigningAccount,
    representative: RepresentativeClient,
    delegation_registry_client: DelegationRegistryClient,
    no_role_account: SigningAccount,
) -> None:
    representative_address = representative.state.global_state.representative_address
    xgov_address = xgov.address
    sender = no_role_account.address

    pay_amount = get_sc_voter_mbr()
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        delegation_registry_client.send.register_voter(
            args=RegisterVoterArgs(
                payment=pay_txn,
                xgov_address=xgov_address,
                representative_address=representative_address,
                window_ts=voter_cfg.DEFAULT_WINDOW_TS,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
            ),
        )


def test_register_voter_wrong_receiver(
    algorand_client: AlgorandClient,
    xgov: SigningAccount,
    representative: RepresentativeClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    representative_address = representative.state.global_state.representative_address
    xgov_address = xgov.address
    sender = xgov_address

    pay_amount = get_sc_voter_mbr()
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=xgov.address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.WRONG_RECEIVER):
        delegation_registry_client.send.register_voter(
            args=RegisterVoterArgs(
                payment=pay_txn,
                xgov_address=xgov_address,
                representative_address=representative_address,
                window_ts=voter_cfg.DEFAULT_WINDOW_TS,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
            ),
        )


def test_register_voter_wrong_amount(
    algorand_client: AlgorandClient,
    xgov: SigningAccount,
    representative: RepresentativeClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    representative_address = representative.state.global_state.representative_address
    xgov_address = xgov.address
    sender = xgov_address

    pay_amount = get_sc_voter_mbr() - 1
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.WRONG_PAYMENT_AMOUNT):
        delegation_registry_client.send.register_voter(
            args=RegisterVoterArgs(
                payment=pay_txn,
                xgov_address=xgov_address,
                representative_address=representative_address,
                window_ts=voter_cfg.DEFAULT_WINDOW_TS,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
            ),
        )
