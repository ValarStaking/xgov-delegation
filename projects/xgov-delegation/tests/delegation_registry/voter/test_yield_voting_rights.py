import pytest
from algokit_utils import (
    AlgoAmount,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.voter.voter_client import (
    VoterClient,
    YieldVotingRightsArgs,
)
from artifacts.xgov_registry_mock.xgov_registry_mock_client import (
    XgovRegistryMockClient,
)

from smart_contracts.common import constants as const
from smart_contracts.errors import std_errors as err


@pytest.mark.parametrize(
    "role",
    ["xgov", "manager"],
)
def test_yield_voting_rights_success(
    voter: VoterClient,
    xgov_registry_mock_client: XgovRegistryMockClient,
    role: str,
) -> None:

    xgov_address = voter.state.global_state.xgov_address
    if role == "xgov":
        sender = xgov_address
        new_voting_address = xgov_address
    else:
        sender = voter.state.global_state.manager_address
        new_voting_address = voter.state.global_state.manager_address

    voter.send.yield_voting_rights(
        args=YieldVotingRightsArgs(voting_address=new_voting_address),
        params=CommonAppCallParams(
            sender=sender,
            extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
        ),
    )

    assert (
        xgov_registry_mock_client.state.box.xgov_box.get_value(
            xgov_address
        ).voting_address
        == new_voting_address
    )


def test_yield_voting_rights_unauthorized(
    voter: VoterClient,
    no_role_account: SigningAccount,
) -> None:
    sender = no_role_account.address
    new_voting_address = no_role_account.address

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        voter.send.yield_voting_rights(
            args=YieldVotingRightsArgs(voting_address=new_voting_address),
            params=CommonAppCallParams(
                sender=sender,
                extra_fee=AlgoAmount(micro_algo=const.MIN_FEE),
            ),
        )
