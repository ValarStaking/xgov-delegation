import pytest
from algokit_utils import (
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.proposal_mock.proposal_mock_client import ProposalMockClient
from artifacts.voter.voter_client import VoterClient, VoteRepresentativeArgs

from smart_contracts.errors import std_errors as err


def test_vote_representative_not_creator(
    voter: VoterClient,
    proposal_mock_client: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    proposal_id = proposal_mock_client.app_id

    with pytest.raises(LogicError, match=err.NOT_CREATOR):
        voter.send.vote_representative(
            args=VoteRepresentativeArgs(proposal_id=proposal_id),
            params=CommonAppCallParams(
                sender=no_role_account.address,
            ),
        )
