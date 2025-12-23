import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError
from artifacts.voter.voter_client import VoterClient
from artifacts.xgov_registry_mock.xgov_registry_mock_client import (
    DelXgovBoxArgs,
    XgovRegistryMockClient,
)

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
    UnregisterVoterArgs,
)
from smart_contracts.common import constants as const
from smart_contracts.errors import std_errors as err


@pytest.mark.parametrize("account_role", ["xgov", "voting", "any-not-xgov"])
def test_unregister_voter_success(
    algorand_client: AlgorandClient,
    voter: VoterClient,
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
    xgov_registry_mock_client: XgovRegistryMockClient,
    account_role: str,
) -> None:

    xgov_address = voter.state.global_state.xgov_address

    if account_role == "voting":
        sender = voter.state.global_state.manager_address
    elif account_role == "xgov":
        sender = xgov_address
    elif account_role == "any-not-xgov":
        sender = no_role_account.address
        # Unsubscribe xGov from the xGovRegistry
        xgov_registry_mock_client.send.del_xgov_box(
            args=DelXgovBoxArgs(xgov_address=xgov_address)
        )

    delegation_registry_client.send.unregister_voter(
        args=UnregisterVoterArgs(xgov_address=xgov_address),
        params=CommonAppCallParams(
            sender=sender,
            extra_fee=AlgoAmount(micro_algo=6 * const.MIN_FEE),
        ),
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        delegation_registry_client.state.box.voters_box.get_value(xgov_address)

    with pytest.raises(Exception, match="application does not exist"):
        algorand_client.client.algod.application_info(voter.app_id)


def test_unregister_voter_paused_register(
    voter: VoterClient,
    delegation_registry_client_paused: DelegationRegistryClient,
) -> None:
    xgov_address = voter.state.global_state.xgov_address
    sender = xgov_address

    with pytest.raises(LogicError, match=err.PAUSED_REGISTRY):
        delegation_registry_client_paused.send.unregister_voter(
            args=UnregisterVoterArgs(xgov_address=xgov_address),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=5 * const.MIN_FEE),
            ),
        )


def test_unregister_voter_not_voter(
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    xgov_address = no_role_account.address
    sender = xgov_address

    with pytest.raises(LogicError, match=err.NOT_VOTER):
        delegation_registry_client.send.unregister_voter(
            args=UnregisterVoterArgs(xgov_address=xgov_address),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=5 * const.MIN_FEE),
            ),
        )


def test_unregister_voter_unauthorized(
    voter: VoterClient,
    no_role_account: SigningAccount,
    delegation_registry_client: DelegationRegistryClient,
) -> None:
    xgov_address = voter.state.global_state.xgov_address
    sender = no_role_account.address

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        delegation_registry_client.send.unregister_voter(
            args=UnregisterVoterArgs(xgov_address=xgov_address),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=5 * const.MIN_FEE),
            ),
        )
