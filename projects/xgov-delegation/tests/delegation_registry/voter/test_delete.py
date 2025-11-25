import pytest
from algokit_utils import (
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.voter.voter_client import VoterClient

from smart_contracts.errors import std_errors as err


def test_delete_not_creator(
    voter: VoterClient,
    no_role_account: SigningAccount,
) -> None:

    with pytest.raises(LogicError, match=err.NOT_CREATOR):
        voter.send.delete.delete(
            params=CommonAppCallParams(
                sender=no_role_account.address,
            ),
        )
