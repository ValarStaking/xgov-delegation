import random
from dataclasses import dataclass
from typing import Final

from algokit_utils import AlgorandClient, AppManager
from algosdk.constants import ZERO_ADDRESS
from algosdk.encoding import encode_address

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    DelegationRegistryClient,
)
from smart_contracts.common.constants import (
    ACCOUNT_MBR,
    DYNAMIC_BYTE_ARRAY_LENGTH_OVERHEAD,
    MAX_APP_TOTAL_ARG_LEN,
    MAX_PAGES_PER_APP,
    METHOD_SELECTOR_LENGTH,
    PER_BOX_MBR,
    PER_BYTE_IN_BOX_MBR,
    PER_BYTE_SLICE_ENTRY_MBR,
    PER_PAGE_MBR,
    PER_UINT_SLICE_ENTRY_MBR,
    SC_BOX_NAME_LEN,
    UINT64_LENGTH,
)
from smart_contracts.representative import config as rep_cfg
from smart_contracts.voter import config as voter_cfg


def load_sc_data_size_per_transaction() -> int:
    return (
        MAX_APP_TOTAL_ARG_LEN
        - METHOD_SELECTOR_LENGTH
        - SC_BOX_NAME_LEN
        - UINT64_LENGTH
        - DYNAMIC_BYTE_ARRAY_LENGTH_OVERHEAD
    )


REPRESENTATIVE_BOX_SIZE: Final[int] = 1 + 32 + 8
VOTER_BOX_SIZE: Final[int] = 1 + 32 + 8
PROPOSALS_VOTE_BOX_SIZE: Final[int] = 2 + 8 + 2 * 8


def get_box_mbr(size: int, *, name: bytes | None = None) -> int:
    _size = size
    _size += 0 if name is None else len(name)

    return PER_BOX_MBR + PER_BYTE_IN_BOX_MBR * _size


def get_sc_representative_mbr() -> int:
    return (
        get_box_mbr(size=REPRESENTATIVE_BOX_SIZE)
        + ACCOUNT_MBR
        + MAX_PAGES_PER_APP * PER_PAGE_MBR
        + rep_cfg.GLOBAL_UINTS * PER_UINT_SLICE_ENTRY_MBR
        + rep_cfg.GLOBAL_BYTES * PER_BYTE_SLICE_ENTRY_MBR
    )


def get_sc_voter_mbr() -> int:
    return (
        get_box_mbr(size=VOTER_BOX_SIZE)
        + ACCOUNT_MBR
        + MAX_PAGES_PER_APP * PER_PAGE_MBR
        + voter_cfg.GLOBAL_UINTS * PER_UINT_SLICE_ENTRY_MBR
        + voter_cfg.GLOBAL_BYTES * PER_BYTE_SLICE_ENTRY_MBR
    )


def get_sc_voter_unassigned_mbr() -> int:
    return (
        ACCOUNT_MBR
        + MAX_PAGES_PER_APP * PER_PAGE_MBR
        + voter_cfg.GLOBAL_UINTS * PER_UINT_SLICE_ENTRY_MBR
        + voter_cfg.GLOBAL_BYTES * PER_BYTE_SLICE_ENTRY_MBR
    )


def get_vote_mbr() -> int:
    return get_box_mbr(size=PROPOSALS_VOTE_BOX_SIZE)


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

    apps = account_info["created-apps"]  # type: ignore

    for app in apps:  # type: ignore
        app_id: int = app["id"]  # type: ignore
        gs_raw = AppManager.decode_app_state(app["params"]["global-state"])  # type: ignore
        num_uint_loc = app["params"]["local-state-schema"]["num-uint"]  # type: ignore

        if num_uint_loc == rep_cfg.LOCAL_UINTS:  # type: ignore
            representative = Representative(
                id=app_id,
                representative_address=encode_address(
                    gs_raw["representative_address"].value_raw
                ),  # type: ignore
                registry_app=gs_raw["registry_app"].value,  # type: ignore
                paused=gs_raw["paused"].value,  # type: ignore
            )
            representatives.append(representative)

        elif num_uint_loc == voter_cfg.LOCAL_UINTS:  # type: ignore
            voter = Voter(
                id=app_id,
                xgov_address=encode_address(gs_raw["xgov_address"].value_raw),  # type: ignore
                registry_app=gs_raw["registry_app"].value,  # type: ignore
                representative_app=gs_raw["representative_app"].value,  # type: ignore
                window_ts=gs_raw["window_ts"].value,  # type: ignore
                votes_left=gs_raw["votes_left"].value,  # type: ignore
                manager_address=encode_address(gs_raw["manager_address"].value_raw),  # type: ignore
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
