import pytest
from algokit_utils import (
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.voter.voter_client import SetWindowArgs, VoterClient

from smart_contracts.errors import std_errors as err


@pytest.mark.parametrize(
    "role",
    ["xgov", "manager"],
)
def test_set_window_success(
    voter: VoterClient,
    role: str,
) -> None:

    new_window_ts = 42
    if role == "xgov":
        sender = voter.state.global_state.xgov_address
    else:
        sender = voter.state.global_state.manager_address

    voter.send.set_window(
        args=SetWindowArgs(window_ts=new_window_ts),
        params=CommonAppCallParams(
            sender=sender,
        ),
    )

    assert voter.state.global_state.window_ts == new_window_ts


def test_set_window_unauthorized(
    voter: VoterClient,
    no_role_account: SigningAccount,
) -> None:
    new_window_ts = 42
    sender = no_role_account.address

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        voter.send.set_window(
            args=SetWindowArgs(window_ts=new_window_ts),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )
