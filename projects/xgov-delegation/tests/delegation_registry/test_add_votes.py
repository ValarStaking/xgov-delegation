import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SigningAccount,
)
from artifacts.voter.voter_client import VoterClient

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    AddVotesArgs,
    DelegationRegistryClient,
)
from smart_contracts.common import constants as const
from smart_contracts.errors import std_errors as err


@pytest.mark.parametrize(
    "account_role, add_votes",
    [
        ("xgov", 1),
        ("xgov", 333),
        ("other", 1),
        ("other", 42),
    ],
)
def test_add_votes_success(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
    no_role_account: SigningAccount,
    account_role: str,
    add_votes: int,
) -> None:
    registry_start = delegation_registry_client.algorand.account.get_information(
        delegation_registry_client.app_address
    )
    start_votes_left = delegation_registry_client.state.global_state.votes_left
    start_trigger_fund = delegation_registry_client.state.global_state.trigger_fund

    xgov_address = voter.state.global_state.xgov_address
    if account_role == "xgov":
        sender = xgov_address
        pay_amount = (
            delegation_registry_client.state.global_state.vote_fees.xgov * add_votes
        )
    else:
        sender = no_role_account.address
        pay_amount = (
            delegation_registry_client.state.global_state.vote_fees.other * add_votes
        )

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    delegation_registry_client.send.add_votes(
        args=AddVotesArgs(
            payment=pay_txn,
            xgov_address=xgov_address,
            add_votes=add_votes,
        ),
        params=CommonAppCallParams(
            sender=sender,
            extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
        ),
    )

    registry_end = delegation_registry_client.algorand.account.get_information(
        delegation_registry_client.app_address
    )
    end_votes_left = delegation_registry_client.state.global_state.votes_left
    end_trigger_fund = delegation_registry_client.state.global_state.trigger_fund

    assert start_votes_left == end_votes_left - add_votes
    assert (
        start_trigger_fund
        == end_trigger_fund
        - delegation_registry_client.state.global_state.vote_trigger_award * add_votes
    )
    assert (registry_end.amount - registry_end.min_balance) - (
        registry_start.amount - registry_start.min_balance
    ) == pay_amount


def test_add_votes_paused_register(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    delegation_registry_client_paused: DelegationRegistryClient,
) -> None:
    xgov_address = voter.state.global_state.xgov_address
    sender = xgov_address
    add_votes = 1
    pay_amount = (
        delegation_registry_client_paused.state.global_state.vote_fees.xgov * add_votes
    )

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client_paused.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.PAUSED_REGISTRY):
        delegation_registry_client_paused.send.add_votes(
            args=AddVotesArgs(
                payment=pay_txn,
                xgov_address=xgov_address,
                add_votes=add_votes,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
            ),
        )


def test_add_votes_not_voter(
    algorand_client: AlgorandClient,
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    xgov_address = no_role_account.address
    sender = xgov_address
    add_votes = 1
    pay_amount = (
        delegation_registry_client.state.global_state.vote_fees.xgov * add_votes
    )

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.NOT_VOTER):
        delegation_registry_client.send.add_votes(
            args=AddVotesArgs(
                payment=pay_txn,
                xgov_address=xgov_address,
                add_votes=add_votes,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
            ),
        )


def test_add_votes_wrong_receiver(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    xgov_address = voter.state.global_state.xgov_address
    sender = xgov_address
    add_votes = 1
    pay_amount = (
        delegation_registry_client.state.global_state.vote_fees.xgov * add_votes
    )

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=xgov_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.WRONG_RECEIVER):
        delegation_registry_client.send.add_votes(
            args=AddVotesArgs(
                payment=pay_txn,
                xgov_address=xgov_address,
                add_votes=add_votes,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
            ),
        )


def test_add_votes_wrong_amount(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    xgov_address = voter.state.global_state.xgov_address
    sender = xgov_address
    add_votes = 1
    pay_amount = (
        delegation_registry_client.state.global_state.vote_fees.xgov * add_votes
    ) - 1

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.WRONG_PAYMENT_AMOUNT):
        delegation_registry_client.send.add_votes(
            args=AddVotesArgs(
                payment=pay_txn,
                xgov_address=xgov_address,
                add_votes=add_votes,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
            ),
        )
