import pytest
from algokit_utils import (
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.voter.voter_client import AssignXgovArgs, VoterClient

from smart_contracts.errors import std_errors as err


def test_assign_xgov_not_creator(
    voter: VoterClient,
    no_role_account: SigningAccount,
) -> None:
    sender = no_role_account.address

    with pytest.raises(LogicError, match=err.NOT_CREATOR):
        voter.send.assign_xgov(
            args=AssignXgovArgs(
                xgov_address=sender,
                manager_address=sender,
            ),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )
