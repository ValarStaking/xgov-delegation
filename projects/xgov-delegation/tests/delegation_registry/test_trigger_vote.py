import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.proposal_mock.proposal_mock_client import (
    DelVoterBoxArgs,
    ProposalMockClient,
    SetVoteOpenTsArgs,
)
from artifacts.representative.representative_client import (
    DeleteVoteArgs,
    RepresentativeClient,
)
from artifacts.voter.voter_client import SetWindowArgs, VoterClient

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    TriggerVoteArgs,
)
from smart_contracts.common import constants as const
from smart_contracts.errors import std_errors as err


def test_trigger_vote_success(
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
    proposal_voter: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    registry_start = delegation_registry_client.algorand.account.get_information(
        delegation_registry_client.app_address
    )
    start_votes_left = delegation_registry_client.state.global_state.votes_left
    start_trigger_fund = delegation_registry_client.state.global_state.trigger_fund

    proposal_id = proposal_voter.app_id
    xgov_address = voter.state.global_state.xgov_address

    delegation_registry_client.send.trigger_vote(
        args=TriggerVoteArgs(
            xgov_address=xgov_address,
            proposal_id=proposal_id,
        ),
        params=CommonAppCallParams(
            sender=no_role_account.address,
            extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
        ),
    )

    registry_end = delegation_registry_client.algorand.account.get_information(
        delegation_registry_client.app_address
    )
    end_votes_left = delegation_registry_client.state.global_state.votes_left
    end_trigger_fund = delegation_registry_client.state.global_state.trigger_fund

    assert start_votes_left == end_votes_left + 1
    assert (
        start_trigger_fund
        == end_trigger_fund
        + delegation_registry_client.state.global_state.vote_trigger_award
    )
    assert (registry_start.amount - registry_start.min_balance) - (
        registry_end.amount - registry_end.min_balance
    ) == delegation_registry_client.state.global_state.vote_trigger_award


def test_trigger_vote_paused_register(
    voter: VoterClient,
    delegation_registry_client_paused: DelegationRegistryClient,
    proposal_voter: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    proposal_id = proposal_voter.app_id
    xgov_address = voter.state.global_state.xgov_address

    with pytest.raises(LogicError, match=err.PAUSED_REGISTRY):
        delegation_registry_client_paused.send.trigger_vote(
            args=TriggerVoteArgs(
                xgov_address=xgov_address,
                proposal_id=proposal_id,
            ),
            params=CommonAppCallParams(
                sender=no_role_account.address,
                extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
            ),
        )


def test_trigger_vote_not_voter(
    delegation_registry_client: DelegationRegistryClient,
    proposal_voter: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    proposal_id = proposal_voter.app_id
    xgov_address = no_role_account.address

    with pytest.raises(LogicError, match=err.NOT_VOTER):
        delegation_registry_client.send.trigger_vote(
            args=TriggerVoteArgs(
                xgov_address=xgov_address,
                proposal_id=proposal_id,
            ),
            params=CommonAppCallParams(
                sender=no_role_account.address,
                extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
            ),
        )


def test_trigger_vote_invalid_proposal(
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
    proposal_fake_client: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    proposal_id = proposal_fake_client.app_id
    xgov_address = voter.state.global_state.xgov_address

    with pytest.raises(LogicError, match="error: assert failed pc=446"):
        delegation_registry_client.send.trigger_vote(
            args=TriggerVoteArgs(
                xgov_address=xgov_address,
                proposal_id=proposal_id,
            ),
            params=CommonAppCallParams(
                sender=no_role_account.address,
                extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
            ),
        )


def test_trigger_vote_no_votes_left(
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
    proposal_voter: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    proposal_id = proposal_voter.app_id
    xgov_address = voter.state.global_state.xgov_address

    # Trigger vote to clear number of paid votes
    delegation_registry_client.send.trigger_vote(
        args=TriggerVoteArgs(
            xgov_address=xgov_address,
            proposal_id=proposal_id,
        ),
        params=CommonAppCallParams(
            sender=no_role_account.address,
            extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
        ),
    )

    with pytest.raises(LogicError, match="error: assert failed pc=452"):
        delegation_registry_client.send.trigger_vote(
            args=TriggerVoteArgs(
                xgov_address=xgov_address,
                proposal_id=proposal_id,
            ),
            params=CommonAppCallParams(
                sender=no_role_account.address,
                extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
            ),
        )


def test_trigger_vote_with_window_success(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
    proposal_voter: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    proposal_id = proposal_voter.app_id
    xgov_address = voter.state.global_state.xgov_address

    latest_round = algorand_client.client.algod.status()["last-round"]
    block = algorand_client.client.algod.block_info(latest_round)
    latest_block_timestamp = block["block"]["ts"]

    proposal_voter.send.set_vote_open_ts(
        args=SetVoteOpenTsArgs(vote_open_ts=latest_block_timestamp - 1000),
    )
    voter.send.set_window(
        args=SetWindowArgs(window_ts=100),
        params=CommonAppCallParams(
            sender=xgov_address,
        ),
    )

    assert delegation_registry_client.send.trigger_vote(
        args=TriggerVoteArgs(
            xgov_address=xgov_address,
            proposal_id=proposal_id,
        ),
        params=CommonAppCallParams(
            sender=no_role_account.address,
            extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
        ),
    )


def test_trigger_vote_too_soon(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
    proposal_voter: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    proposal_id = proposal_voter.app_id
    xgov_address = voter.state.global_state.xgov_address

    latest_round = algorand_client.client.algod.status()["last-round"]
    block = algorand_client.client.algod.block_info(latest_round)
    latest_block_timestamp = block["block"]["ts"]

    proposal_voter.send.set_vote_open_ts(
        args=SetVoteOpenTsArgs(vote_open_ts=latest_block_timestamp + 1000),
    )
    voter.send.set_window(
        args=SetWindowArgs(window_ts=100),
        params=CommonAppCallParams(
            sender=xgov_address,
        ),
    )

    with pytest.raises(LogicError, match="error: assert failed pc=528"):
        delegation_registry_client.send.trigger_vote(
            args=TriggerVoteArgs(
                xgov_address=xgov_address,
                proposal_id=proposal_id,
            ),
            params=CommonAppCallParams(
                sender=no_role_account.address,
                extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
            ),
        )


def test_trigger_vote_rep_not_existent(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
    proposal_voter: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    proposal_id = proposal_voter.app_id
    xgov_address = voter.state.global_state.xgov_address

    # Delete representative
    representative = algorand_client.client.get_typed_app_client_by_id(
        typed_client=RepresentativeClient,
        app_id=voter.state.global_state.representative_app,
    )
    representative_address = representative.state.global_state.representative_address
    representative.send.delete_vote(
        args=DeleteVoteArgs(
            proposal_id=proposal_id,
        ),
        params=CommonAppCallParams(
            sender=representative_address,
            extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
        ),
    )
    delegation_registry_client.send.unregister_representative(
        params=CommonAppCallParams(
            sender=representative_address,
            extra_fee=AlgoAmount(micro_algo=3 * const.MIN_FEE),
        ),
    )

    with pytest.raises(LogicError, match="error: assert failed pc=538"):
        delegation_registry_client.send.trigger_vote(
            args=TriggerVoteArgs(
                xgov_address=xgov_address,
                proposal_id=proposal_id,
            ),
            params=CommonAppCallParams(
                sender=no_role_account.address,
                extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
            ),
        )


@pytest.mark.parametrize(
    "vote",
    ["not-submit", "paused"],
)
def test_trigger_vote_vote_invalid(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
    proposal_voter: ProposalMockClient,
    no_role_account: SigningAccount,
    vote: str,
) -> None:
    proposal_id = proposal_voter.app_id
    xgov_address = voter.state.global_state.xgov_address

    # Representative doesn't submit vote or is paused
    representative = algorand_client.client.get_typed_app_client_by_id(
        typed_client=RepresentativeClient,
        app_id=voter.state.global_state.representative_app,
    )
    representative_address = representative.state.global_state.representative_address
    if vote == "not-submit":
        representative.send.delete_vote(
            args=DeleteVoteArgs(
                proposal_id=proposal_id,
            ),
            params=CommonAppCallParams(
                sender=representative_address,
                extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
            ),
        )
    else:
        representative.send.pause(
            params=CommonAppCallParams(
                sender=representative_address,
            ),
        )

    with pytest.raises(LogicError, match="error: assert failed pc=592"):
        delegation_registry_client.send.trigger_vote(
            args=TriggerVoteArgs(
                xgov_address=xgov_address,
                proposal_id=proposal_id,
            ),
            params=CommonAppCallParams(
                sender=no_role_account.address,
                extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
            ),
        )


def test_trigger_vote_no_votes(
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
    proposal_voter: ProposalMockClient,
    no_role_account: SigningAccount,
) -> None:
    proposal_id = proposal_voter.app_id
    xgov_address = voter.state.global_state.xgov_address

    proposal_voter.send.del_voter_box(
        args=DelVoterBoxArgs(
            voter_address=xgov_address,
        )
    )

    with pytest.raises(LogicError, match="error: assert failed pc=646"):
        delegation_registry_client.send.trigger_vote(
            args=TriggerVoteArgs(
                xgov_address=xgov_address,
                proposal_id=proposal_id,
            ),
            params=CommonAppCallParams(
                sender=no_role_account.address,
                extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
            ),
        )
