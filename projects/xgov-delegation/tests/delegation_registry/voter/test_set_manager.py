import pytest
from algokit_utils import (
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.voter.voter_client import SetManagerArgs, VoterClient

from smart_contracts.errors import std_errors as err


@pytest.mark.parametrize(
    "role",
    ["xgov", "manager"],
)
def test_set_manager_success(
    voter: VoterClient,
    role: str,
    no_role_account: SigningAccount,
) -> None:

    new_manager_address = no_role_account.address
    if role == "xgov":
        sender = voter.state.global_state.xgov_address
    else:
        sender = voter.state.global_state.manager_address

    voter.send.set_manager(
        args=SetManagerArgs(manager_address=new_manager_address),
        params=CommonAppCallParams(
            sender=sender,
        ),
    )

    assert voter.state.global_state.manager_address == new_manager_address


def test_set_manager_unauthorized(
    voter: VoterClient,
    no_role_account: SigningAccount,
) -> None:
    new_manager_address = no_role_account.address
    sender = no_role_account.address

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        voter.send.set_manager(
            args=SetManagerArgs(manager_address=new_manager_address),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )
