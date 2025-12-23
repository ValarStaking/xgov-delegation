ARC_65_PREFIX = "ERR:"
# Errors
WRONG_GLOBAL_BYTES = "Wrong Global Bytes allocation"
WRONG_GLOBAL_UINTS = "Wrong Global UInts allocation"
WRONG_LOCAL_BYTES = "Wrong Local Bytes allocation"
WRONG_LOCAL_UINTS = "Wrong Local UInts allocation"

UNAUTHORIZED = "Unauthorized"

WRONG_RECEIVER = "Wrong Receiver"

MISSING_CONFIG = "Missing Config"

PENDING_PROPOSALS = "Pending proposals"
WRONG_PAYMENT_AMOUNT = "Wrong payment amount"
INSUFFICIENT_FUNDS = "Insufficient funds"

PAUSED_REGISTRY = "Registry's non-admin methods are paused"
PAUSED = "Contract is paused"

COULD_NOT_VOTE = "Could not vote as neither primary nor backup representative"
TOO_SOON_TO_VOTE = "Too soon to vote"
INVALID_PROPOSAL = "Invalid proposal"
ALREADY_REPRESENTATIVE = "Already a representative"
ALREADY_VOTER = "Already a Voter"
NOT_VOTER = "Not Voter"
NOT_XGOV = "Not an xGov"
VOTER_ASSIGNED = "Voter is already assigned"
NOT_REPRESENTATIVE = "Not a representative"
UNRELATED_APP = "App was not created by registry"
NOT_CREATOR = "Sender is not app creator"
INVALID_PROPOSAL = "Proposal is not part of xGov Registry"
VALID_PROPOSAL = "Proposal is part of xGov Registry"
PROPOSAL_VOTING = "Proposal is in voting stage"
NO_VOTES_LEFT = "No paid votes left to cast"
VOTE_ALREADY_PUBLISHED = "Representative vote was already published"
UNDELETED_BOXES = "Not all boxes deleted"
VOTER_PREPARED = "Voter already prepared"

REPRESENTATIVE_NONEXISTENT = "Representative is nonexistent"
VOTE_INVALID = "Representative vote is invalid"
NO_VOTES = "xGov does not have any votes"
VOTE_NOT_PPM = "Vote not in PPM"


INCONSISTENT_VOTE_FEES = "xGov vote fees must not be larger than for others"

INCONSISTENT_TRIGGER_AWARD = "Trigger reward must not be larger than minimum vote fees"

TRIGGER_FUND_INSUFFICIENT = (
    "Trigger fund is insufficient. Fund the Registry or reduce award."
)
