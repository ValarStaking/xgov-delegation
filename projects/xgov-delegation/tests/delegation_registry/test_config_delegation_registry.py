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
    ConfigDelegationRegistryArgs,
    DelegationRegistryClient,
    Fees,
)
from smart_contracts.common import constants as const
from smart_contracts.delegation_registry import config as regcfg
from smart_contracts.errors import std_errors as err


def test_config_delegation_registry_success(
    delegation_registry_client_uninitialized: DelegationRegistryClient,
) -> None:

    vote_fees = Fees(
        xgov=regcfg.FEE_VOTE_XGOV,
        other=regcfg.FEE_VOTE_OTHER,
    )
    representative_fee = regcfg.FEE_REPRESENTATIVE
    vote_trigger_award = regcfg.VOTE_TRIGGER_AWARD

    delegation_registry_client_uninitialized.send.config_delegation_registry(
        args=ConfigDelegationRegistryArgs(
            vote_fees=vote_fees,
            representative_fee=representative_fee,
            vote_trigger_award=vote_trigger_award,
        )
    )
    assert (
        delegation_registry_client_uninitialized.state.global_state.vote_fees
        == vote_fees
    )
    assert (
        delegation_registry_client_uninitialized.state.global_state.representative_fee
        == regcfg.FEE_REPRESENTATIVE
    )
    assert (
        delegation_registry_client_uninitialized.state.global_state.vote_trigger_award
        == regcfg.VOTE_TRIGGER_AWARD
    )


def test_config_delegation_registry_not_manager(
    no_role_account: SigningAccount,
    delegation_registry_client_uninitialized: DelegationRegistryClient,
) -> None:

    vote_fees = Fees(
        xgov=regcfg.FEE_VOTE_XGOV,
        other=regcfg.FEE_VOTE_OTHER,
    )
    representative_fee = regcfg.FEE_REPRESENTATIVE
    vote_trigger_award = regcfg.VOTE_TRIGGER_AWARD

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        delegation_registry_client_uninitialized.send.config_delegation_registry(
            args=ConfigDelegationRegistryArgs(
                vote_fees=vote_fees,
                representative_fee=representative_fee,
                vote_trigger_award=vote_trigger_award,
            ),
            params=CommonAppCallParams(sender=no_role_account.address),
        )


def test_config_delegation_registry_inconsistent_vote_fees(
    delegation_registry_client_uninitialized: DelegationRegistryClient,
) -> None:

    vote_fees = Fees(
        xgov=1,
        other=0,
    )
    representative_fee = regcfg.FEE_REPRESENTATIVE
    vote_trigger_award = regcfg.VOTE_TRIGGER_AWARD

    with pytest.raises(LogicError, match=err.INCONSISTENT_VOTE_FEES):
        delegation_registry_client_uninitialized.send.config_delegation_registry(
            args=ConfigDelegationRegistryArgs(
                vote_fees=vote_fees,
                representative_fee=representative_fee,
                vote_trigger_award=vote_trigger_award,
            )
        )


def test_config_delegation_registry_inconsistent_trigger_award(
    delegation_registry_client_uninitialized: DelegationRegistryClient,
) -> None:

    vote_fees = Fees(
        xgov=0,
        other=regcfg.FEE_VOTE_OTHER,
    )
    representative_fee = regcfg.FEE_REPRESENTATIVE
    vote_trigger_award = regcfg.VOTE_TRIGGER_AWARD

    with pytest.raises(LogicError, match=err.INCONSISTENT_TRIGGER_AWARD):
        delegation_registry_client_uninitialized.send.config_delegation_registry(
            args=ConfigDelegationRegistryArgs(
                vote_fees=vote_fees,
                representative_fee=representative_fee,
                vote_trigger_award=vote_trigger_award,
            )
        )


def test_config_delegation_registry_trigger_fund_insufficient(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:

    xgov_address = voter.state.global_state.xgov_address
    sender = xgov_address
    # Add a vote
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=regcfg.FEE_VOTE_XGOV),
        )
    )
    delegation_registry_client.send.add_votes(
        args=AddVotesArgs(
            payment=pay_txn,
            xgov_address=xgov_address,
            add_votes=1,
        ),
        params=CommonAppCallParams(
            sender=sender,
            extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
        ),
    )

    vote_fees = Fees(
        xgov=regcfg.FEE_VOTE_XGOV,
        other=regcfg.FEE_VOTE_OTHER,
    )
    representative_fee = regcfg.FEE_REPRESENTATIVE
    vote_trigger_award = 10_000_000_000

    with pytest.raises(LogicError, match=err.TRIGGER_FUND_INSUFFICIENT):
        delegation_registry_client.send.config_delegation_registry(
            args=ConfigDelegationRegistryArgs(
                vote_fees=vote_fees,
                representative_fee=representative_fee,
                vote_trigger_award=vote_trigger_award,
            )
        )
