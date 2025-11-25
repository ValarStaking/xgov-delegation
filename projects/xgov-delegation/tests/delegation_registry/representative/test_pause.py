import pytest
from algokit_utils import (
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.representative.representative_client import RepresentativeClient

from smart_contracts.errors import std_errors as err


def test_pause_success(
    representative: RepresentativeClient,
) -> None:
    assert representative.state.global_state.paused == 0

    sender = representative.state.global_state.representative_address
    representative.send.pause(
        params=CommonAppCallParams(
            sender=sender,
        ),
    )

    assert representative.state.global_state.paused == 1


def test_pause_unauthorized(
    representative: RepresentativeClient,
    no_role_account: SigningAccount,
) -> None:
    sender = no_role_account.address

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        representative.send.pause(
            params=CommonAppCallParams(
                sender=sender,
            ),
        )
