from typing import Final

# State Schema
GLOBAL_BYTES: Final[int] = 32
GLOBAL_UINTS: Final[int] = 32
LOCAL_BYTES: Final[int] = 0
LOCAL_UINTS: Final[int] = 0

# Global state keys
GS_KEY_MANAGER_ADDRESS: Final[bytes] = b"manager_address"
GS_KEY_XGOV_REGISTRY_APP: Final[bytes] = b"xgov_registry_app"
GS_KEY_VOTE_FEES: Final[bytes] = b"vote_fees"
GS_KEY_REPRESENTATIVE_FEE: Final[bytes] = b"representative_fee"
GS_KEY_VOTE_TRIGGER_AWARD: Final[bytes] = b"vote_trigger_award"
GS_KEY_PAUSED_REGISTRY: Final[bytes] = b"paused_registry"
GS_KEY_VOTES_LEFT: Final[bytes] = b"votes_left"
GS_KEY_TRIGGER_FUND: Final[bytes] = b"trigger_fund"

# Box keys
VOTERS_MAP_PREFIX: Final[bytes] = b"v"
REPRESENTATIVE_MAP_PREFIX: Final[bytes] = b"r"
CONTRACT_VOTER_BOX: Final[bytes] = b"sc_vot"
CONTRACT_REPRESENTATIVE_BOX: Final[bytes] = b"sc_rep"

# Parameters
ALGO_TO_MICROALGO = 10**6
WEEKS_TO_SECONDS = 7 * 24 * 3_600

## Amounts
FEE_VOTE_XGOV: Final[int] = 1 * ALGO_TO_MICROALGO  # 1 ALGO
FEE_VOTE_OTHER: Final[int] = 10 * ALGO_TO_MICROALGO  # 10 ALGO
FEE_REPRESENTATIVE: Final[int] = 50 * ALGO_TO_MICROALGO  # 50 ALGO
VOTE_TRIGGER_AWARD: Final[int] = 500_000  # 0.5 ALGO
