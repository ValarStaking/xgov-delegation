import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SigningAccount,
)
from common.helpers import (
    get_sc_voter_unassigned_mbr,
    load_sc_data_size_per_transaction,
)

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    ConfigDelegationRegistryArgs,
    DelegationRegistryClient,
    Fees,
    InitContractArgs,
    LoadContractArgs,
    PrepareVoterArgs,
)
from smart_contracts.artifacts.voter.voter_client import (
    VoterFactory,
)
from smart_contracts.common import constants as const
from smart_contracts.delegation_registry import config as regcfg
from smart_contracts.errors import std_errors as err
from tests.delegation_registry.common import get_available_voter


def test_prepare_voter(
    algorand_client: AlgorandClient,
    delegation_registry_client_uninitialized: DelegationRegistryClient,
    deployer: SigningAccount,
) -> None:
    client = delegation_registry_client_uninitialized

    client.send.config_delegation_registry(
        args=ConfigDelegationRegistryArgs(
            vote_fees=Fees(
                xgov=regcfg.FEE_VOTE_XGOV,
                other=regcfg.FEE_VOTE_OTHER,
            ),
            representative_fee=regcfg.FEE_REPRESENTATIVE,
            vote_trigger_award=regcfg.VOTE_TRIGGER_AWARD,
        )
    )
    # Omit loading Representative SC as not needed for this test

    # Load Voter SC
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

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=deployer.address,
            receiver=client.app_address,
            amount=AlgoAmount(micro_algo=get_sc_voter_unassigned_mbr()),
        )
    )
    client.send.prepare_voter(
        args=PrepareVoterArgs(payment=pay_txn),
        params=CommonAppCallParams(
            extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
        ),
    )

    assert (
        get_available_voter(
            algorand_client=algorand_client,
            delegation_registry_client=delegation_registry_client_uninitialized,
        )
        is not None
    )


def test_prepare_voter_wrong_receiver(
    algorand_client: AlgorandClient,
    delegation_registry_client_uninitialized: DelegationRegistryClient,
    no_role_account: SigningAccount,
) -> None:
    client = delegation_registry_client_uninitialized
    sender = no_role_account.address

    client.send.config_delegation_registry(
        args=ConfigDelegationRegistryArgs(
            vote_fees=Fees(
                xgov=regcfg.FEE_VOTE_XGOV,
                other=regcfg.FEE_VOTE_OTHER,
            ),
            representative_fee=regcfg.FEE_REPRESENTATIVE,
            vote_trigger_award=regcfg.VOTE_TRIGGER_AWARD,
        )
    )
    # Omit loading Representative SC as not needed for this test

    # Load Voter SC
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

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=sender,
            amount=AlgoAmount(micro_algo=get_sc_voter_unassigned_mbr()),
        )
    )
    with pytest.raises(LogicError, match=err.WRONG_RECEIVER):
        client.send.prepare_voter(
            args=PrepareVoterArgs(payment=pay_txn),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
            ),
        )


def test_prepare_voter_wrong_amount(
    algorand_client: AlgorandClient,
    delegation_registry_client_uninitialized: DelegationRegistryClient,
    no_role_account: SigningAccount,
) -> None:
    client = delegation_registry_client_uninitialized
    sender = no_role_account.address

    client.send.config_delegation_registry(
        args=ConfigDelegationRegistryArgs(
            vote_fees=Fees(
                xgov=regcfg.FEE_VOTE_XGOV,
                other=regcfg.FEE_VOTE_OTHER,
            ),
            representative_fee=regcfg.FEE_REPRESENTATIVE,
            vote_trigger_award=regcfg.VOTE_TRIGGER_AWARD,
        )
    )
    # Omit loading Representative SC as not needed for this test

    # Load Voter SC
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

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=client.app_address,
            amount=AlgoAmount(micro_algo=get_sc_voter_unassigned_mbr() - 1),
        )
    )
    with pytest.raises(LogicError, match=err.WRONG_PAYMENT_AMOUNT):
        client.send.prepare_voter(
            args=PrepareVoterArgs(payment=pay_txn),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
            ),
        )
