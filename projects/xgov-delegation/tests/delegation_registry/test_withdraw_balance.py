import pytest
from algokit_utils import (
    AlgoAmount,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.voter.voter_client import VoterClient

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    ConfigDelegationRegistryArgs,
    DelegationRegistryClient,
    Fees,
)
from smart_contracts.common import constants as const
from smart_contracts.delegation_registry import config as regcfg
from smart_contracts.errors import std_errors as err


def test_withdraw_balance_success(
    delegation_registry_client: DelegationRegistryClient,
    voter: VoterClient,
) -> None:

    manager_address = delegation_registry_client.state.global_state.manager_address

    manager_start = delegation_registry_client.algorand.account.get_information(
        manager_address
    )
    registry_start = delegation_registry_client.algorand.account.get_information(
        delegation_registry_client.app_address
    )

    delegation_registry_client.send.withdraw_balance(
        params=CommonAppCallParams(
            extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
        ),
    )

    manager_end = delegation_registry_client.algorand.account.get_information(
        manager_address
    )

    txn_costs = 2 * const.MIN_FEE
    assert (
        manager_end.amount.amount_in_micro_algo
        - manager_start.amount.amount_in_micro_algo
        + txn_costs
        == registry_start.amount.amount_in_micro_algo
        - registry_start.min_balance.amount_in_micro_algo
        - delegation_registry_client.state.global_state.trigger_fund
    )


def test_withdraw_balance_not_manager(
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        delegation_registry_client.send.withdraw_balance(
            params=CommonAppCallParams(sender=no_role_account.address),
        )


def test_withdraw_balance_insufficient_funds(
    delegation_registry_client: DelegationRegistryClient,
    voter: VoterClient,
) -> None:

    # Use all funds for awards
    registry_start = delegation_registry_client.algorand.account.get_information(
        delegation_registry_client.app_address
    )

    representative_fee = regcfg.FEE_REPRESENTATIVE

    assert (
        delegation_registry_client.state.global_state.votes_left != 0
    ), "Error in test. Change values."
    vote_trigger_award = (
        registry_start.amount.amount_in_micro_algo
        - registry_start.min_balance.amount_in_micro_algo
    ) / delegation_registry_client.state.global_state.votes_left
    assert vote_trigger_award.is_integer(), "Error in test. Change values."
    vote_trigger_award = int(vote_trigger_award)

    vote_fees = Fees(
        xgov=vote_trigger_award,
        other=vote_trigger_award,
    )

    delegation_registry_client.send.config_delegation_registry(
        args=ConfigDelegationRegistryArgs(
            vote_fees=vote_fees,
            representative_fee=representative_fee,
            vote_trigger_award=vote_trigger_award,
        )
    )

    # Nothing to withdraw
    with pytest.raises(LogicError, match=err.INSUFFICIENT_FUNDS):
        delegation_registry_client.send.withdraw_balance()
