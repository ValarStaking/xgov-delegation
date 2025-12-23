from algopy import UInt64, op, subroutine

from smart_contracts.proposal import config as prop_cfg

from . import enums as enm


@subroutine
def is_proposal_voting(proposal_id: UInt64) -> bool:

    status, exists = op.AppGlobal.get_ex_uint64(
        proposal_id,
        prop_cfg.GS_KEY_STATUS,
    )

    return exists and status == enm.STATUS_VOTING


@subroutine
def get_proposal_vote_close_ts(proposal_id: UInt64) -> UInt64:

    vote_open_ts, exists = op.AppGlobal.get_ex_uint64(
        proposal_id,
        prop_cfg.GS_KEY_VOTE_OPEN_TS,
    )

    voting_duration, exists = op.AppGlobal.get_ex_uint64(
        proposal_id,
        prop_cfg.GS_KEY_VOTING_DURATION,
    )

    return vote_open_ts + voting_duration
