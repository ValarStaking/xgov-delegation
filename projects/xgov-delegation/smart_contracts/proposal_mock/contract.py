# pyright: reportMissingModuleSource=false

from algopy import (
    Account,
    ARC4Contract,
    BoxMap,
    Global,
    GlobalState,
    UInt64,
    arc4,
)

from ..proposal import config as prop_cfg
from ..proposal import enums as enm


class ProposalMock(ARC4Contract, avm_version=10):
    def __init__(self) -> None:
        self.registry_app_id = GlobalState(
            UInt64(),
            key=prop_cfg.GS_KEY_REGISTRY_APP_ID,
        )
        self.status = GlobalState(
            UInt64(enm.STATUS_EMPTY),
            key=prop_cfg.GS_KEY_STATUS,
        )
        self.vote_open_ts = GlobalState(
            UInt64(),
            key=prop_cfg.GS_KEY_VOTE_OPEN_TS,
        )
        self.voting_duration = GlobalState(
            UInt64(),
            key=prop_cfg.GS_KEY_VOTING_DURATION,
        )

        # Boxes
        self.voters = BoxMap(
            Account,
            UInt64,  # The specs define votes as UInt32 for box-size efficiency
            key_prefix=prop_cfg.VOTER_BOX_KEY_PREFIX,
        )

        return

    @arc4.abimethod(create="require")
    def create(self) -> None:
        self.registry_app_id.value = Global.caller_application_id

    @arc4.abimethod()
    def set_status(self, status: UInt64) -> None:
        self.status.value = status

    @arc4.abimethod()
    def set_vote_open_ts(self, vote_open_ts: UInt64) -> None:
        self.vote_open_ts.value = vote_open_ts

    @arc4.abimethod()
    def set_voting_duration(self, voting_duration: UInt64) -> None:
        self.voting_duration.value = voting_duration

    @arc4.abimethod()
    def vote(
        self,
        voter: arc4.Address,
        approvals: arc4.UInt64,
        rejections: arc4.UInt64,
    ) -> None:
        return

    @arc4.abimethod()
    def set_voter_box(
        self,
        voter_address: arc4.Address,
        votes: arc4.UInt64,
    ) -> None:
        """
        Set the Voter box for the given address.

        Args:
            voter_address (arc4.Address): The address of the Voter
            votes (arc4.UInt64): The voter's votes
        """
        self.voters[voter_address.native] = votes.as_uint64()

        return

    @arc4.abimethod()
    def del_voter_box(
        self,
        voter_address: arc4.Address,
    ) -> None:
        """
        Delete the Voter box for the given address.

        Args:
            voter_address (arc4.Address): The address of the Voter
        """
        del self.voters[voter_address.native]

        return

    @arc4.abimethod(readonly=True)
    def get_voter_box(self, voter_address: arc4.Address) -> tuple[arc4.UInt64, bool]:
        """
        Returns the Voter box for the given address.

        Args:
            voter_address (arc4.Address): The address of the Voter

        Returns:
            votes: The voter's votes
            bool: `True` if voter's box exists, else `False`
        """
        exists = voter_address.native in self.voters
        if exists:
            votes = self.voters[voter_address.native]
        else:
            votes = UInt64(0)

        return arc4.UInt64(votes), exists
