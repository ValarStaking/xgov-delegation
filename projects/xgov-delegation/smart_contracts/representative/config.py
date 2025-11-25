from typing import Final

# State Schema
GLOBAL_BYTES: Final[int] = 32
GLOBAL_UINTS: Final[int] = 32
LOCAL_BYTES: Final[int] = 9
LOCAL_UINTS: Final[int] = 7

# Global state keys
GS_KEY_REPRESENTATIVE_ADDRESS: Final[bytes] = b"representative_address"
GS_KEY_REGISTRY_APP: Final[bytes] = b"registry_app"
GS_KEY_PAUSED: Final[bytes] = b"paused"

# Box keys
PROPOSALS_VOTE_MAP_PREFIX: Final[bytes] = b"pv"
