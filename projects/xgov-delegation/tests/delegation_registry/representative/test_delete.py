import pytest
from algokit_utils import (
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.representative.representative_client import RepresentativeClient

from smart_contracts.errors import std_errors as err


def test_delete_not_creator(
    representative: RepresentativeClient,
    no_role_account: SigningAccount,
) -> None:

    with pytest.raises(LogicError, match=err.NOT_CREATOR):
        representative.send.delete.delete(
            params=CommonAppCallParams(
                sender=no_role_account.address,
            ),
        )
