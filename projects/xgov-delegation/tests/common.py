from typing import Final

from algokit_utils import AlgoAmount

INITIAL_FUNDS: Final[AlgoAmount] = AlgoAmount(algo=1_000)
DEFAULT_VOTING_DURATION: Final[int] = 1

DEFAULT_PROPOSAL_STATUS: Final[int] = 1
DEFAULT_PROPOSAL_VOTE_OPEN_TS: Final[int] = 1
