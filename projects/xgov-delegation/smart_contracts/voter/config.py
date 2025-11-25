from typing import Final

# State Schema
GLOBAL_BYTES: Final[int] = 32
GLOBAL_UINTS: Final[int] = 32
LOCAL_BYTES: Final[int] = 8
LOCAL_UINTS: Final[int] = 8

# Global state keys
GS_KEY_XGOV_ADDRESS: Final[bytes] = b"xgov_address"
GS_KEY_MANAGER_ADDRESS: Final[bytes] = b"manager_address"
GS_KEY_REGISTRY_APP: Final[bytes] = b"registry_app"
GS_KEY_REPRESENTATIVE_APP: Final[bytes] = b"representative_app"
GS_KEY_WINDOW_TS: Final[bytes] = b"window_ts"
GS_KEY_VOTES_LEFT: Final[bytes] = b"votes_left"

# Parameters
## Amounts
DEFAULT_WINDOW_TS = 2 * 24 * 3_600  # 2 days in seconds
