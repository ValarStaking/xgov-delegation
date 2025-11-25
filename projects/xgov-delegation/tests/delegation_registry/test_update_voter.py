import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.voter.voter_client import VoterClient, VoterFactory
from common.helpers import load_sc_data_size_per_transaction

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    InitContractArgs,
    LoadContractArgs,
    UpdateVoterArgs,
)
from smart_contracts.common import constants as const
from smart_contracts.delegation_registry import config as regcfg
from smart_contracts.errors import std_errors as err


def test_update_voter_success(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:

    # Load new representative SC
    voter_factory = algorand_client.client.get_typed_app_factory(
        typed_factory=VoterFactory,
    )
    compiled_sc = voter_factory.app_factory.compile()
    approval_program = compiled_sc.approval_program + compiled_sc.approval_program

    delegation_registry_client.send.init_contract(
        args=InitContractArgs(
            contract=regcfg.CONTRACT_VOTER_BOX,
            size=len(approval_program),
        ),
    )

    data_size_per_transaction = load_sc_data_size_per_transaction()
    bulks = 1 + len(approval_program) // data_size_per_transaction
    for i in range(bulks):
        chunk = approval_program[
            i * data_size_per_transaction : (i + 1) * data_size_per_transaction
        ]
        delegation_registry_client.send.load_contract(
            args=LoadContractArgs(
                contract=regcfg.CONTRACT_VOTER_BOX,
                offset=i * data_size_per_transaction,
                data=chunk,
            ),
        )

    delegation_registry_client.send.update_voter(
        args=UpdateVoterArgs(xgov_address=voter.state.global_state.xgov_address),
        params=CommonAppCallParams(
            extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
        ),
    )

    updated = algorand_client.app.get_by_id(voter.app_id)

    assert updated.approval_program == approval_program


def test_update_voter_not_manager(
    no_role_account: SigningAccount,
    voter: VoterClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        delegation_registry_client.send.update_voter(
            args=UpdateVoterArgs(xgov_address=voter.state.global_state.xgov_address),
            params=CommonAppCallParams(
                sender=no_role_account.address,
                extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
            ),
        )


def test_update_voter_not_existing(
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    with pytest.raises(LogicError, match=err.NOT_VOTER):
        delegation_registry_client.send.update_voter(
            args=UpdateVoterArgs(xgov_address=no_role_account.address),
            params=CommonAppCallParams(
                extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
            ),
        )
