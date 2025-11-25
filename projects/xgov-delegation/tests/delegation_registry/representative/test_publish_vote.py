import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SigningAccount,
)
from artifacts.proposal_mock.proposal_mock_client import ProposalMockClient
from artifacts.representative.representative_client import (
    PublishVoteArgs,
    RepresentativeClient,
    Vote,
)
from common.helpers import get_vote_mbr

from smart_contracts.common import constants as const
from smart_contracts.errors import std_errors as err


def is_vote_valid(vote: Vote) -> bool:
    return vote.approval + vote.rejection <= const.BPS


@pytest.mark.parametrize(
    "vote",
    [
        Vote(approval=const.BPS, rejection=0),
        Vote(approval=0, rejection=const.BPS),
        Vote(approval=const.BPS, rejection=const.BPS),
        Vote(approval=const.BPS // 2, rejection=const.BPS // 2),
    ],
)
def test_publish_vote(
    algorand_client: AlgorandClient,
    representative: RepresentativeClient,
    proposal_mock_client: ProposalMockClient,
    vote: Vote,
) -> None:
    sender = representative.state.global_state.representative_address
    proposal_id = proposal_mock_client.app_id
    pay_amount = get_vote_mbr()

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=representative.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    if is_vote_valid(vote):

        representative.send.publish_vote(
            args=PublishVoteArgs(
                payment=pay_txn,
                proposal_id=proposal_id,
                vote=vote,
            ),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )

        assert (
            representative.state.box.proposals_vote_box.get_value(proposal_id).approval
            == vote.approval
        )
        assert (
            representative.state.box.proposals_vote_box.get_value(proposal_id).rejection
            == vote.rejection
        )

    else:
        with pytest.raises(LogicError, match=err.VOTE_NOT_BPS):
            representative.send.publish_vote(
                args=PublishVoteArgs(
                    payment=pay_txn,
                    proposal_id=proposal_id,
                    vote=vote,
                ),
                params=CommonAppCallParams(
                    sender=sender,
                ),
            )


def test_publish_vote_unauthorized(
    algorand_client: AlgorandClient,
    representative: RepresentativeClient,
    proposal_mock_client: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    sender = no_role_account.address
    proposal_id = proposal_mock_client.app_id
    pay_amount = get_vote_mbr()
    vote = Vote(approval=const.BPS, rejection=0)

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=representative.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        representative.send.publish_vote(
            args=PublishVoteArgs(
                payment=pay_txn,
                proposal_id=proposal_id,
                vote=vote,
            ),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )


def test_publish_vote_invalid_proposal(
    algorand_client: AlgorandClient,
    representative: RepresentativeClient,
    proposal_fake_client: ProposalMockClient,
) -> None:
    sender = representative.state.global_state.representative_address
    proposal_id = proposal_fake_client.app_id
    pay_amount = get_vote_mbr()
    vote = Vote(approval=const.BPS, rejection=0)

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=representative.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.INVALID_PROPOSAL):
        representative.send.publish_vote(
            args=PublishVoteArgs(
                payment=pay_txn,
                proposal_id=proposal_id,
                vote=vote,
            ),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )


def test_publish_vote_paused(
    algorand_client: AlgorandClient,
    representative_paused: RepresentativeClient,
    proposal_mock_client: ProposalMockClient,
) -> None:
    sender = representative_paused.state.global_state.representative_address
    proposal_id = proposal_mock_client.app_id
    pay_amount = get_vote_mbr()
    vote = Vote(approval=const.BPS, rejection=0)

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=representative_paused.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.PAUSED):
        representative_paused.send.publish_vote(
            args=PublishVoteArgs(
                payment=pay_txn,
                proposal_id=proposal_id,
                vote=vote,
            ),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )


def test_publish_vote_already_published(
    algorand_client: AlgorandClient,
    representative_vote: RepresentativeClient,
    proposal_mock_client: ProposalMockClient,
) -> None:
    sender = representative_vote.state.global_state.representative_address
    proposal_id = proposal_mock_client.app_id
    pay_amount = get_vote_mbr()
    vote = Vote(approval=const.BPS, rejection=0)

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=representative_vote.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.VOTE_ALREADY_PUBLISHED):
        representative_vote.send.publish_vote(
            args=PublishVoteArgs(
                payment=pay_txn,
                proposal_id=proposal_id,
                vote=vote,
            ),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )


def test_publish_vote_wrong_receiver(
    algorand_client: AlgorandClient,
    representative: RepresentativeClient,
    proposal_mock_client: ProposalMockClient,
) -> None:
    sender = representative.state.global_state.representative_address
    proposal_id = proposal_mock_client.app_id
    pay_amount = get_vote_mbr()
    vote = Vote(approval=const.BPS, rejection=0)

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=sender,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.WRONG_RECEIVER):
        representative.send.publish_vote(
            args=PublishVoteArgs(
                payment=pay_txn,
                proposal_id=proposal_id,
                vote=vote,
            ),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )


def test_publish_vote_wrong_amount(
    algorand_client: AlgorandClient,
    representative: RepresentativeClient,
    proposal_mock_client: ProposalMockClient,
) -> None:
    sender = representative.state.global_state.representative_address
    proposal_id = proposal_mock_client.app_id
    pay_amount = get_vote_mbr() - 1
    vote = Vote(approval=const.BPS, rejection=0)

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=representative.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    with pytest.raises(LogicError, match=err.WRONG_PAYMENT_AMOUNT):
        representative.send.publish_vote(
            args=PublishVoteArgs(
                payment=pay_txn,
                proposal_id=proposal_id,
                vote=vote,
            ),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )
