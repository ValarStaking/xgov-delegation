import base64

import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SigningAccount,
)

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    KeyRegRegistryArgs,
    KeyRegTxnInfo,
)
from smart_contracts.common import constants as const
from smart_contracts.errors import std_errors as err

key_reg_info_default = KeyRegTxnInfo(
    vote_first=1,
    vote_last=1_000_000,
    vote_key_dilution=1_000,
    vote_pk=bytes([0xAA] * 32),
    selection_pk=bytes([0xBB] * 32),
    state_proof_pk=bytes([0xCC] * 64),
)

key_dereg_info = KeyRegTxnInfo(
    vote_first=0,
    vote_last=0,
    vote_key_dilution=0,
    vote_pk=bytes(32),
    selection_pk=bytes(32),
    state_proof_pk=bytes(64),
)


def test_key_reg_registry_success(
    algorand_client: AlgorandClient,
    deployer: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=deployer.address,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=const.INCENTIVE_ELIGIBLE_FEE),
        )
    )

    delegation_registry_client.send.key_reg_registry(
        args=KeyRegRegistryArgs(
            payment=pay_txn,
            key_reg_info=key_reg_info_default,
        ),
    )

    registry_account = delegation_registry_client.algorand.account.get_information(
        delegation_registry_client.app_address
    )

    assert registry_account.status == "Online"
    assert registry_account.incentive_eligible
    key_reg_info = registry_account.participation
    assert (
        base64.b64decode(key_reg_info["selection-participation-key"])
        == key_reg_info_default.selection_pk
    )
    assert (
        base64.b64decode(key_reg_info["state-proof-key"])
        == key_reg_info_default.state_proof_pk
    )
    assert (
        base64.b64decode(key_reg_info["vote-participation-key"])
        == key_reg_info_default.vote_pk
    )
    assert key_reg_info["vote-first-valid"] == key_reg_info_default.vote_first
    assert key_reg_info["vote-last-valid"] == key_reg_info_default.vote_last
    assert key_reg_info["vote-key-dilution"] == key_reg_info_default.vote_key_dilution


def test_key_dereg_registry_success(
    algorand_client: AlgorandClient,
    deployer: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=deployer.address,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=const.INCENTIVE_ELIGIBLE_FEE),
        )
    )

    delegation_registry_client.send.key_reg_registry(
        args=KeyRegRegistryArgs(
            payment=pay_txn,
            key_reg_info=key_dereg_info,
        ),
    )

    registry_account = delegation_registry_client.algorand.account.get_information(
        delegation_registry_client.app_address
    )

    assert registry_account.status == "Offline"


def test_key_reg_registry_not_manager(
    algorand_client: AlgorandClient,
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=no_role_account.address,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=const.INCENTIVE_ELIGIBLE_FEE),
        )
    )

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        delegation_registry_client.send.key_reg_registry(
            args=KeyRegRegistryArgs(
                payment=pay_txn,
                key_reg_info=key_reg_info_default,
            ),
            params=CommonAppCallParams(sender=no_role_account.address),
        )
