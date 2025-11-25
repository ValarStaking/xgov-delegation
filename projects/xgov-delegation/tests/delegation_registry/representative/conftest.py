import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    PaymentParams,
)
from artifacts.proposal_mock.proposal_mock_client import ProposalMockClient
from common.helpers import get_vote_mbr

from smart_contracts.artifacts.representative.representative_client import (
    PublishVoteArgs,
    RepresentativeClient,
    Vote,
)
from smart_contracts.common import constants as const


@pytest.fixture(scope="function")
def representative_paused(
    representative: RepresentativeClient,
) -> RepresentativeClient:
    sender = representative.state.global_state.representative_address

    representative.send.pause(
        params=CommonAppCallParams(
            sender=sender,
        ),
    )

    return representative


@pytest.fixture(scope="function")
def representative_vote(
    algorand_client: AlgorandClient,
    representative: RepresentativeClient,
    proposal_mock_client: ProposalMockClient,
) -> RepresentativeClient:
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

    representative.send.publish_vote(
        args=PublishVoteArgs(
            payment=pay_txn,
            proposal_id=proposal_id,
            vote=Vote(
                approval=const.BPS,
                rejection=0,
            ),
        ),
        params=CommonAppCallParams(
            sender=sender,
        ),
    )

    return representative
