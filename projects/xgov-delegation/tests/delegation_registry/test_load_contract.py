import pytest
from algokit_utils import (
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from common.helpers import load_sc_data_size_per_transaction

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    InitContractArgs,
    LoadContractArgs,
)
from smart_contracts.artifacts.voter.voter_client import (
    VoterFactory,
)
from smart_contracts.delegation_registry import config as regcfg
from smart_contracts.errors import std_errors as err


def test_load_contract_success(
    algorand_client: AlgorandClient,
    delegation_registry_client_uninitialized: DelegationRegistryClient,
) -> None:

    voter_factory = algorand_client.client.get_typed_app_factory(
        typed_factory=VoterFactory,
    )

    compiled_sc = voter_factory.app_factory.compile()

    delegation_registry_client_uninitialized.send.init_contract(
        args=InitContractArgs(
            contract=regcfg.CONTRACT_VOTER_BOX,
            size=len(compiled_sc.approval_program),
        ),
    )

    data_size_per_transaction = load_sc_data_size_per_transaction()
    bulks = 1 + len(compiled_sc.approval_program) // data_size_per_transaction
    for i in range(bulks):
        chunk = compiled_sc.approval_program[
            i * data_size_per_transaction : (i + 1) * data_size_per_transaction
        ]
        delegation_registry_client_uninitialized.send.load_contract(
            args=LoadContractArgs(
                contract=regcfg.CONTRACT_VOTER_BOX,
                offset=i * data_size_per_transaction,
                data=chunk,
            ),
        )

    assert (
        delegation_registry_client_uninitialized.state.box.voter_approval_program
        == compiled_sc.approval_program
    )


def test_load_contract_not_manager(
    no_role_account: SigningAccount,
    delegation_registry_client_uninitialized: DelegationRegistryClient,
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        delegation_registry_client_uninitialized.send.load_contract(
            args=LoadContractArgs(
                contract=regcfg.CONTRACT_VOTER_BOX,
                offset=0,
                data=bytes(1),
            ),
            params=CommonAppCallParams(sender=no_role_account.address),
        )
