import pytest
from algokit_utils import (
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.representative.representative_client import RepresentativeClient

from smart_contracts.errors import std_errors as err


def test_resume_success(
    representative_paused: RepresentativeClient,
) -> None:
    assert representative_paused.state.global_state.paused == 1

    sender = representative_paused.state.global_state.representative_address
    representative_paused.send.resume(
        params=CommonAppCallParams(
            sender=sender,
        ),
    )

    assert representative_paused.state.global_state.paused == 0


def test_resume_unauthorized(
    representative_paused: RepresentativeClient,
    no_role_account: SigningAccount,
) -> None:
    sender = no_role_account.address

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        representative_paused.send.resume(
            params=CommonAppCallParams(
                sender=sender,
            ),
        )
