# pyright: reportMissingModuleSource=false

from algopy import (
    Account,
    Application,
    ARC4Contract,
    Global,
    GlobalState,
    StateTotals,
    Txn,
    UInt64,
    arc4,
    itxn,
    op,
    subroutine,
)

import smart_contracts.errors.std_errors as err
from smart_contracts.common import abi_types as typ
from smart_contracts.common import constants as const
from smart_contracts.delegation_registry import config as reg_cfg
from smart_contracts.proposal import utils as utils_prop
from smart_contracts.proposal.interface import IProposal
from smart_contracts.representative import contract as representative_contract
from smart_contracts.xgov_registry.interface import IXGovRegistry

from . import config as cfg


class Voter(
    ARC4Contract,
    avm_version=10,
    state_totals=StateTotals(
        global_bytes=cfg.GLOBAL_BYTES,
        global_uints=cfg.GLOBAL_UINTS,
        local_bytes=cfg.LOCAL_BYTES,
        local_uints=cfg.LOCAL_UINTS,
    ),
):
    def __init__(self) -> None:
        # Preconditions
        assert Txn.global_num_byte_slice == cfg.GLOBAL_BYTES, err.WRONG_GLOBAL_BYTES
        assert Txn.global_num_uint == cfg.GLOBAL_UINTS, err.WRONG_GLOBAL_UINTS
        assert Txn.local_num_byte_slice == cfg.LOCAL_BYTES, err.WRONG_LOCAL_BYTES
        assert Txn.local_num_uint == cfg.LOCAL_UINTS, err.WRONG_LOCAL_UINTS

        # Global Variables
        self.xgov_address = GlobalState(
            Account(),
            key=cfg.GS_KEY_XGOV_ADDRESS,
        )
        self.registry_app = GlobalState(
            Application(),
            key=cfg.GS_KEY_REGISTRY_APP,
        )
        self.representative_app = GlobalState(
            Application(),
            key=cfg.GS_KEY_REPRESENTATIVE_APP,
        )
        self.window_ts = GlobalState(
            UInt64(),
            key=cfg.GS_KEY_WINDOW_TS,
        )
        self.votes_left = GlobalState(
            UInt64(),
            key=cfg.GS_KEY_VOTES_LEFT,
        )
        self.manager_address = GlobalState(
            Account(),
            key=cfg.GS_KEY_MANAGER_ADDRESS,
        )

    @arc4.abimethod(create="require")
    def create(
        self,
        xgov_address: arc4.Address,
        manager_address: arc4.Address,
        representative_id: arc4.UInt64,
        window_ts: arc4.UInt64,
    ) -> None:
        """
        Create a new Voter.
        MUST BE CALLED BY THE REGISTRY CONTRACT.

        Args:
            xgov_address (arc4.Address): Address of the xGov.
            manager_address (arc4.Address): Address of the xGov manager, i.e. its voting_address.
            representative_id (arc4.UInt64): The application ID of the representative.
            window_ts (arc4.UInt64): The new time window in seconds before proposal voting period
                ends that representative can cast the vote. Set to 0 to not have any delay.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Delegation Registry.
            err.UNRELATED_APP: If any app was not created by the Delegation Registry.
        """
        assert (
            Global.caller_application_id != 0
        ), err.UNAUTHORIZED  # Only callable by another contract

        self.registry_app.value = Application(Global.caller_application_id)
        self.xgov_address.value = xgov_address.native
        self.manager_address.value = manager_address.native
        self.representative_app.value = Application(representative_id.as_uint64())
        self.window_ts.value = window_ts.as_uint64()

        self.votes_left.value = UInt64(0)

        self.verify_new_app(self.representative_app.value)

        return

    @arc4.abimethod(allow_actions=["UpdateApplication"])
    def update(self) -> None:
        """
        Update the contract.
        MUST BE CALLED BY THE REGISTRY CONTRACT.

        Raises:
            err.NOT_CREATOR: If the sender is not the Delegation Registry.
        """
        assert self.is_creator(), err.NOT_CREATOR

        return

    @arc4.abimethod()
    def set_manager(
        self,
        manager_address: arc4.Address,
    ) -> None:
        """
        Set a new manager.

        Args:
            manager_address (arc4.Address): Address of the new manager.

        Raises:
            err.UNAUTHORIZED: If the sender is not the xGov or the current manager.
        """
        assert self.is_xgov_or_manager(), err.UNAUTHORIZED

        self.manager_address.value = manager_address.native

        return

    @arc4.abimethod()
    def set_representative(
        self,
        representative_id: arc4.UInt64,
    ) -> None:
        """
        Set a new representative.

        Args:
            representative_id (arc4.UInt64): The application ID of the new representative.

        Raises:
            err.UNAUTHORIZED: If the sender is not the xGov or its manager.
            err.UNRELATED_APP: If representative app was not created by the Delegation Registry.
        """
        assert self.is_xgov_or_manager(), err.UNAUTHORIZED

        self.representative_app.value = Application(representative_id.as_uint64())

        self.verify_new_app(self.representative_app.value)

        return

    @arc4.abimethod()
    def set_window(
        self,
        window_ts: arc4.UInt64,
    ) -> None:
        """
        Set a new window when vote can be cast as representative.

        Args:
            window_ts (arc4.UInt64): The new time window in seconds before proposal voting period
                ends that representative can cast the vote. Set to 0 to not have any delay.

        Raises:
            err.UNAUTHORIZED: If the sender is not the xGov or its manager.
        """
        assert self.is_xgov_or_manager(), err.UNAUTHORIZED

        self.window_ts.value = window_ts.as_uint64()

        return

    @arc4.abimethod()
    def vote_representative(
        self,
        proposal_id: arc4.UInt64,
    ) -> None:
        """
        Vote on a proposal according to vote of representative if time is within window.
        MUST BE CALLED BY THE REGISTRY CONTRACT.

        Args:
            proposal_id (arc4.UInt64): App ID of proposal to vote on.

        Raises:
            err.NOT_CREATOR: If the sender is not the Delegation Registry.
            err.INVALID_PROPOSAL: If the proposal was not created by the xGov Registry,
                which is defined at the Delegation Registry.
            err.NO_VOTES_LEFT: If no paid votes left.
            err.TOO_SOON_TO_VOTE: If time is not yet within set window before proposal voting ends.
            err.REPRESENTATIVE_NONEXISTENT: If representative has unregistered.
            err.VOTE_INVALID: If representative did not submit a vote or has paused its activity.
            err.NO_VOTES: If xGov does not have any votes to cast on this proposal.
        """
        assert self.is_creator(), err.NOT_CREATOR
        assert self.is_valid_proposal(proposal_id), err.INVALID_PROPOSAL

        assert self.votes_left.value > 0, err.NO_VOTES_LEFT
        self.votes_left.value -= 1

        # Check if allowed to vote according to representative
        if self.window_ts.value:
            vote_close_ts = utils_prop.get_proposal_vote_close_ts(
                proposal_id.as_uint64()
            )
            assert (
                Global.latest_timestamp > vote_close_ts - self.window_ts.value
            ), err.TOO_SOON_TO_VOTE

        # Get vote from representative
        creator, exists = op.AppParamsGet.app_creator(self.representative_app.value)
        assert exists, err.REPRESENTATIVE_NONEXISTENT

        [vote, is_valid], txn = arc4.abi_call(
            representative_contract.Representative.get_vote,
            proposal_id,
            app_id=self.representative_app.value,
        )
        assert is_valid, err.VOTE_INVALID

        # Get voter's box
        [votes, exists], txn = arc4.abi_call(
            IProposal.get_voter_box,
            arc4.Address(self.xgov_address.value),
            app_id=proposal_id.as_uint64(),
        )
        assert exists, err.NO_VOTES

        # Calculate votes
        approvals = (votes.as_uint64() * vote.approval.as_uint64()) // const.BPS
        rejections = (votes.as_uint64() * vote.rejection.as_uint64()) // const.BPS

        # Vote
        arc4.abi_call(
            IXGovRegistry.vote_proposal,
            proposal_id,
            arc4.Address(self.xgov_address.value),
            approvals,
            rejections,
            app_id=self.get_xgov_registry_id(),
        )

        return

    @arc4.abimethod()
    def vote_direct(
        self,
        proposal_id: arc4.UInt64,
        vote: typ.VoteRaw,
    ) -> None:
        """
        Vote directly on a proposal.

        Args:
            proposal_id (arc4.UInt64): App ID of proposal to vote on.
            vote (VoteRaw): xGov's vote for the proposal. Expressed in number of approvals and rejections.

        Raises:
            err.UNAUTHORIZED: If the sender is not the xGov or its manager.
            err.INVALID_PROPOSAL: If the proposal was not created by the xGov Registry,
                which is defined at the Delegation Registry.
        """
        assert self.is_xgov_or_manager(), err.UNAUTHORIZED
        assert self.is_valid_proposal(proposal_id), err.INVALID_PROPOSAL

        # Vote
        arc4.abi_call(
            IXGovRegistry.vote_proposal,
            proposal_id,
            arc4.Address(self.xgov_address.value),
            vote.approvals.as_uint64(),
            vote.rejections.as_uint64(),
            app_id=self.get_xgov_registry_id(),
        )

        return

    @arc4.abimethod()
    def yield_voting_rights(
        self,
        voting_address: arc4.Address,
    ) -> None:
        """
        Yield voting rights to another account.

        Args:
            voting_address (arc4.Address): The voting account address to delegate voting power to.

        Raises:
            err.UNAUTHORIZED: If the sender is not the xGov or its manager.
        """
        assert self.is_xgov_or_manager(), err.UNAUTHORIZED

        arc4.abi_call(
            IXGovRegistry.set_voting_account,
            arc4.Address(self.xgov_address.value),
            voting_address,
            app_id=self.get_xgov_registry_id(),
        )

        return

    @arc4.abimethod()
    def add_votes(
        self,
        add_votes: arc4.UInt64,
    ) -> None:
        """
        Increase votes left.
        MUST BE CALLED BY THE REGISTRY CONTRACT.

        Args:
            add_votes (arc4.UInt64): Number of approved votes to add.

        Raises:
            err.NOT_CREATOR: If the sender is not the Delegation Registry.
        """
        assert self.is_creator(), err.NOT_CREATOR

        self.votes_left.value += add_votes.as_uint64()

        return

    @arc4.abimethod(allow_actions=("DeleteApplication",))
    def delete(self) -> None:
        """
        Delete the Voter.
        MUST BE CALLED BY THE REGISTRY CONTRACT.

        Raises:
            err.NOT_CREATOR: If the sender is not the Delegation Registry.
        """
        assert self.is_creator(), err.NOT_CREATOR

        itxn.Payment(
            receiver=Global.creator_address,
            amount=UInt64(0),
            close_remainder_to=Global.creator_address,
        ).submit()

        return

    # ---------------------------------
    # ---------- Subroutines ----------
    # ---------------------------------
    @subroutine
    def verify_new_app(self, app: Application) -> None:
        assert app.creator == Global.creator_address, err.UNRELATED_APP

    @subroutine
    def is_creator(self) -> bool:
        return Txn.sender == Global.creator_address

    @subroutine
    def is_xgov_or_manager(self) -> bool:
        return (
            Txn.sender == self.xgov_address.value
            or Txn.sender == self.manager_address.value
        )

    @subroutine
    def get_xgov_registry_id(self) -> UInt64:
        xgov_registry_id, exists = op.AppGlobal.get_ex_uint64(
            self.registry_app.value,
            reg_cfg.GS_KEY_XGOV_REGISTRY_APP,
        )
        return xgov_registry_id

    @subroutine
    def is_valid_proposal(self, proposal_id: arc4.UInt64) -> bool:
        proposal_creator = Application(proposal_id.as_uint64()).creator
        xgov_registry_id = self.get_xgov_registry_id()
        xgov_registry_address = Application(xgov_registry_id).address
        return proposal_creator == xgov_registry_address
