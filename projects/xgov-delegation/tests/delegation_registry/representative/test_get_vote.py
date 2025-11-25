import pytest
from algokit_utils import CommonAppCallParams, SigningAccount
from algosdk.error import AlgodHTTPError
from artifacts.proposal_mock.proposal_mock_client import ProposalMockClient
from artifacts.representative.representative_client import (
    GetVoteBoxArgs,
    RepresentativeClient,
)


@pytest.mark.parametrize(
    "paused",
    [True, False],
)
def test_get_vote_success(
    representative_vote: RepresentativeClient,
    proposal_mock_client: ProposalMockClient,
    no_role_account: SigningAccount,
    paused: bool,  # noqa: FBT001
) -> None:
    proposal_id = proposal_mock_client.app_id

    if paused:
        representative_vote.send.pause(
            params=CommonAppCallParams(
                sender=representative_vote.state.global_state.representative_address,
            ),
        )

    result = representative_vote.send.get_vote(
        args=GetVoteBoxArgs(proposal_id=proposal_id),
        params=CommonAppCallParams(
            sender=no_role_account.address,
        ),
    )
    get_vote, valid = result.abi_return

    state_vote = representative_vote.state.box.proposals_vote_box.get_value(proposal_id)

    assert valid != paused
    assert get_vote == [state_vote.approval, state_vote.rejection]


@pytest.mark.parametrize(
    "paused",
    [True, False],
)
def test_get_vote_not_exists_success(
    representative_vote: RepresentativeClient,
    proposal_fake_client: ProposalMockClient,
    no_role_account: SigningAccount,
    paused: bool,  # noqa: FBT001
) -> None:
    proposal_id = proposal_fake_client.app_id

    if paused:
        representative_vote.send.pause(
            params=CommonAppCallParams(
                sender=representative_vote.state.global_state.representative_address,
            ),
        )

    result = representative_vote.send.get_vote(
        args=GetVoteBoxArgs(proposal_id=proposal_id),
        params=CommonAppCallParams(
            sender=no_role_account.address,
        ),
    )
    get_vote, valid = result.abi_return

    assert not valid
    assert get_vote == [0, 0]

    with pytest.raises(AlgodHTTPError, match="box not found"):
        representative_vote.state.box.proposals_vote_box.get_value(proposal_id)
