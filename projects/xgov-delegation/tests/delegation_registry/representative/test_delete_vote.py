import pytest
from algokit_utils import (
    AlgoAmount,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError
from artifacts.proposal_mock.proposal_mock_client import (
    ProposalMockClient,
    SetStatusArgs,
)
from artifacts.representative.representative_client import (
    DeleteVoteArgs,
    RepresentativeClient,
)

from smart_contracts.common import constants as const
from smart_contracts.errors import std_errors as err
from smart_contracts.proposal import enums as prop_cfg


def test_delete_vote_success(
    representative_vote: RepresentativeClient,
    proposal_mock_client: ProposalMockClient,
) -> None:
    sender = representative_vote.state.global_state.representative_address
    proposal_id = proposal_mock_client.app_id

    representative_vote.send.delete_vote(
        args=DeleteVoteArgs(
            proposal_id=proposal_id,
        ),
        params=CommonAppCallParams(
            sender=sender,
            extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
        ),
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        representative_vote.state.box.proposals_vote_box.get_value(proposal_id)


def test_delete_vote_unauthorized(
    representative_vote: RepresentativeClient,
    proposal_mock_client: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    sender = no_role_account.address
    proposal_id = proposal_mock_client.app_id

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        representative_vote.send.delete_vote(
            args=DeleteVoteArgs(
                proposal_id=proposal_id,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
            ),
        )


def test_delete_vote_is_voting(
    representative_vote: RepresentativeClient,
    proposal_mock_client: ProposalMockClient,
) -> None:
    sender = representative_vote.state.global_state.representative_address
    proposal_id = proposal_mock_client.app_id

    proposal_mock_client.send.set_status(
        args=SetStatusArgs(status=prop_cfg.STATUS_VOTING)
    )

    with pytest.raises(LogicError, match=err.PROPOSAL_VOTING):
        representative_vote.send.delete_vote(
            args=DeleteVoteArgs(
                proposal_id=proposal_id,
            ),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
            ),
        )
