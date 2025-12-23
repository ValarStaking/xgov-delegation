import random
from dataclasses import dataclass

from algokit_utils import AlgorandClient, AppManager
from algosdk.constants import ZERO_ADDRESS
from algosdk.encoding import encode_address

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
)
from smart_contracts.representative import config as rep_cfg
from smart_contracts.voter import config as voter_cfg


def assert_registry_config(
    delegation_registry_client: DelegationRegistryClient,
    *,
    manager_address: str,
    xgov_registry_app: int,
    vote_fees: int,
    representative_fee: int,
    vote_trigger_award: int,
    paused_registry: int,
    votes_left: int,
    trigger_fund: int,
) -> None:
    global_state = delegation_registry_client.state.global_state
    assert global_state.manager_address == manager_address
    assert global_state.xgov_registry_app == xgov_registry_app
    assert global_state.vote_fees == vote_fees
    assert global_state.representative_fee == representative_fee
    assert global_state.vote_trigger_award == vote_trigger_award
    assert global_state.paused_registry == paused_registry
    assert global_state.votes_left == votes_left
    assert global_state.trigger_fund == trigger_fund


@dataclass(slots=True)
class Representative:
    id: int
    representative_address: str
    registry_app: int
    paused: int


@dataclass(slots=True)
class Voter:
    id: int
    xgov_address: str
    registry_app: int
    representative_app: int
    window_ts: int
    votes_left: int
    manager_address: str


@dataclass(slots=True)
class Contracts:
    representatives: list[Representative]
    voters: list[Voter]


def get_contracts(
    algorand_client: AlgorandClient,
    delegation_registry_client: DelegationRegistryClient,
) -> Contracts:
    account_info = algorand_client.client.algod.account_info(
        delegation_registry_client.app_address
    )

    representatives: list[Representative] = []
    voters: list[Voter] = []

    apps = account_info["created-apps"]

    for app in apps:
        app_id: int = app["id"]
        gs_raw = AppManager.decode_app_state(app["params"]["global-state"])
        num_uint_loc = app["params"]["local-state-schema"]["num-uint"]

        if num_uint_loc == rep_cfg.LOCAL_UINTS:
            representative = Representative(
                id=app_id,
                representative_address=encode_address(
                    gs_raw["representative_address"].value_raw
                ),
                registry_app=gs_raw["registry_app"].value,
                paused=gs_raw["paused"].value,
            )
            representatives.append(representative)

        elif num_uint_loc == voter_cfg.LOCAL_UINTS:
            voter = Voter(
                id=app_id,
                xgov_address=encode_address(gs_raw["xgov_address"].value_raw),
                registry_app=gs_raw["registry_app"].value,
                representative_app=gs_raw["representative_app"].value,
                window_ts=gs_raw["window_ts"].value,
                votes_left=gs_raw["votes_left"].value,
                manager_address=encode_address(gs_raw["manager_address"].value_raw),
            )
            voters.append(voter)

    return Contracts(representatives=representatives, voters=voters)


def get_available_voter(
    algorand_client: AlgorandClient,
    delegation_registry_client: DelegationRegistryClient,
) -> Voter | None:
    contracts = get_contracts(algorand_client, delegation_registry_client)

    available_voters: list[Voter] = []

    for voter in contracts.voters:
        if voter.xgov_address == ZERO_ADDRESS:
            available_voters.append(voter)

    available_voter = random.choice(available_voters) if available_voters else None

    return available_voter
