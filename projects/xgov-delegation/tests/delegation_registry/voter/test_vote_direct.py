import pytest
from algokit_utils import (
    AlgoAmount,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.proposal_mock.proposal_mock_client import (
    ProposalMockClient,
    SetVoterBoxArgs,
)
from artifacts.voter.voter_client import VoteDirectArgs, VoteRaw, VoterClient

from smart_contracts.common import constants as const
from smart_contracts.errors import std_errors as err


@pytest.mark.parametrize(
    "role",
    ["xgov", "manager"],
)
def test_vote_direct_success(
    voter: VoterClient,
    proposal_mock_client: ProposalMockClient,
    role: str,
) -> None:

    xgov_address = voter.state.global_state.xgov_address
    votes = 42
    proposal_mock_client.send.set_voter_box(
        args=SetVoterBoxArgs(
            voter_address=xgov_address,
            votes=votes,
        )
    )

    proposal_id = proposal_mock_client.app_id
    vote = VoteRaw(approvals=votes, rejections=0)
    if role == "xgov":
        sender = xgov_address
    else:
        sender = voter.state.global_state.manager_address

    voter.send.vote_direct(
        args=VoteDirectArgs(proposal_id=proposal_id, vote=vote),
        params=CommonAppCallParams(
            sender=sender,
            extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
        ),
    )


def test_vote_direct_unauthorized(
    voter: VoterClient,
    proposal_mock_client: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:

    xgov_address = voter.state.global_state.xgov_address
    votes = 42
    proposal_mock_client.send.set_voter_box(
        args=SetVoterBoxArgs(
            voter_address=xgov_address,
            votes=votes,
        )
    )

    proposal_id = proposal_mock_client.app_id
    vote = VoteRaw(approvals=votes, rejections=0)
    sender = no_role_account.address

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        voter.send.vote_direct(
            args=VoteDirectArgs(proposal_id=proposal_id, vote=vote),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
            ),
        )


def test_vote_direct_invalid_proposal(
    voter: VoterClient,
    proposal_fake_client: ProposalMockClient,
) -> None:

    xgov_address = voter.state.global_state.xgov_address
    votes = 42
    proposal_fake_client.send.set_voter_box(
        args=SetVoterBoxArgs(
            voter_address=xgov_address,
            votes=votes,
        )
    )

    proposal_id = proposal_fake_client.app_id
    vote = VoteRaw(approvals=votes, rejections=0)
    sender = xgov_address

    with pytest.raises(LogicError, match=err.INVALID_PROPOSAL):
        voter.send.vote_direct(
            args=VoteDirectArgs(proposal_id=proposal_id, vote=vote),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
            ),
        )
