from typing import Final

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
