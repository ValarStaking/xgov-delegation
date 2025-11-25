import pytest
from algokit_utils import (
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from artifacts.representative.representative_client import RepresentativeClient
from artifacts.voter.voter_client import (
    SetRepresentativeArgs,
    VoterClient,
)
from artifacts.xgov_registry_mock.xgov_registry_mock_client import (
    XgovRegistryMockClient,
)

from smart_contracts.errors import std_errors as err


@pytest.mark.parametrize(
    "role",
    ["xgov", "manager"],
)
def test_set_representative_success(
    voter: VoterClient,
    representative2: RepresentativeClient,
    role: str,
) -> None:

    new_representative_id = representative2.app_id
    if role == "xgov":
        sender = voter.state.global_state.xgov_address
    else:
        sender = voter.state.global_state.manager_address

    voter.send.set_representative(
        args=SetRepresentativeArgs(representative_id=new_representative_id),
        params=CommonAppCallParams(
            sender=sender,
        ),
    )

    assert voter.state.global_state.representative_app == new_representative_id


def test_set_representative_unauthorized(
    voter: VoterClient,
    representative2: RepresentativeClient,
    no_role_account: SigningAccount,
) -> None:
    new_representative_id = representative2.app_id
    sender = no_role_account.address

    with pytest.raises(LogicError, match=err.UNAUTHORIZED):
        voter.send.set_representative(
            args=SetRepresentativeArgs(representative_id=new_representative_id),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )


def test_set_representative_unrelated_app(
    voter: VoterClient,
    xgov_registry_fake_client: XgovRegistryMockClient,
) -> None:
    new_representative_id = xgov_registry_fake_client.app_id
    sender = voter.state.global_state.xgov_address

    with pytest.raises(LogicError, match=err.UNRELATED_APP):
        voter.send.set_representative(
            args=SetRepresentativeArgs(representative_id=new_representative_id),
            params=CommonAppCallParams(
                sender=sender,
            ),
        )
