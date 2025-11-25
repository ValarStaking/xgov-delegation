import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.representative.representative_client import (
    RepresentativeClient,
    RepresentativeFactory,
)
from common.helpers import load_sc_data_size_per_transaction

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    InitContractArgs,
    LoadContractArgs,
    UpdateRepresentativeArgs,
)
from smart_contracts.common import constants as const
from smart_contracts.delegation_registry import config as regcfg
from smart_contracts.errors import std_errors as err


def test_update_representative_success(
    algorand_client: AlgorandClient,
    representative: RepresentativeClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:

    # Load new representative SC
    representative_factory = algorand_client.client.get_typed_app_factory(
        typed_factory=RepresentativeFactory,
    )
    compiled_sc = representative_factory.app_factory.compile()
    approval_program = compiled_sc.approval_program + compiled_sc.approval_program

    delegation_registry_client.send.init_contract(
        args=InitContractArgs(
            contract=regcfg.CONTRACT_REPRESENTATIVE_BOX,
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
                contract=regcfg.CONTRACT_REPRESENTATIVE_BOX,
                offset=i * data_size_per_transaction,
                data=chunk,
            ),
        )

    delegation_registry_client.send.update_representative(
        args=UpdateRepresentativeArgs(
            representative_address=representative.state.global_state.representative_address
        ),
        params=CommonAppCallParams(
            extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
        ),
    )

    updated = algorand_client.app.get_by_id(representative.app_id)

    assert updated.approval_program == approval_program


def test_update_representative_not_manager(
    no_role_account: SigningAccount,
    representative: RepresentativeClient,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        delegation_registry_client.send.update_representative(
            args=UpdateRepresentativeArgs(
                representative_address=representative.state.global_state.representative_address
            ),
            params=CommonAppCallParams(
                sender=no_role_account.address,
                extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
            ),
        )


def test_update_representative_not_existing(
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    with pytest.raises(LogicError, match=err.NOT_REPRESENTATIVE):
        delegation_registry_client.send.update_representative(
            args=UpdateRepresentativeArgs(
                representative_address=no_role_account.address
            ),
            params=CommonAppCallParams(
                extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
            ),
        )
