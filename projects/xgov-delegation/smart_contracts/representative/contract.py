# pyright: reportMissingModuleSource=false

from algopy import (
    Account,
    Application,
    ARC4Contract,
    BoxMap,
    Global,
    GlobalState,
    StateTotals,
    Txn,
    UInt64,
    arc4,
    gtxn,
    itxn,
    op,
    subroutine,
)

import smart_contracts.errors.std_errors as err
from smart_contracts.common import abi_types as typ
from smart_contracts.common import constants as const
from smart_contracts.delegation_registry import config as reg_cfg
from smart_contracts.proposal import utils as utils_prop

from . import config as cfg


class Representative(
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
        self.representative_address = GlobalState(
            Account(),
            key=cfg.GS_KEY_REPRESENTATIVE_ADDRESS,
        )
        self.registry_app = GlobalState(
            Application(),
            key=cfg.GS_KEY_REGISTRY_APP,
        )

        self.paused = GlobalState(
            UInt64(),
            key=cfg.GS_KEY_PAUSED,
        )

        # Boxes
        self.proposals_vote_box = BoxMap(
            Application,
            typ.Vote,
            key_prefix=cfg.PROPOSALS_VOTE_MAP_PREFIX,
        )

    @arc4.abimethod(create="require")
    def create(
        self,
        representative_address: arc4.Address,
    ) -> None:
        """
        Create a new representative.
        MUST BE CALLED BY THE REGISTRY CONTRACT.

        Args:
            representative_address (arc4.Address): Address of the representative.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Delegation Registry.
        """
        assert (
            Global.caller_application_id != 0
        ), err.UNAUTHORIZED  # Only callable by another contract

        self.registry_app.value = Application(Global.caller_application_id)
        self.representative_address.value = representative_address.native

        self.paused.value = UInt64(0)

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
    def pause(self) -> None:
        """
        Pause the representation.

        Raises:
            err.UNAUTHORIZED: If the sender is not the representative.
        """
        assert self.is_representative(), err.UNAUTHORIZED
        self.paused.value = UInt64(1)

        return

    @arc4.abimethod()
    def resume(self) -> None:
        """
        Resume the representation.

        Raises:
            err.UNAUTHORIZED: If the sender is not the representative.
        """
        assert self.is_representative(), err.UNAUTHORIZED
        self.paused.value = UInt64(0)

        return

    @arc4.abimethod()
    def publish_vote(
        self,
        payment: gtxn.PaymentTransaction,
        proposal_id: arc4.UInt64,
        vote: typ.Vote,
    ) -> None:
        """
        Publish representative's vote.

        Args:
            payment (gtxn.PaymentTransaction): Payment to cover MBR.
            proposal_id (arc4.UInt64): App ID of proposal to vote on.
            vote (Vote): Representative's vote for the proposal.

        Raises:
            err.UNAUTHORIZED: If the sender is not representative.
            err.INVALID_PROPOSAL: If the proposal was not created by the xGov Registry,
                which is defined at the Delegation Registry.
            err.PAUSED: If representative has paused its actions.
            err.VOTE_ALREADY_PUBLISHED: If representative already published the vote for the proposal.
            err.VOTE_NOT_BPS: If vote does not add up less than or equal to 1, i.e. is not in BPS, thus invalid.
            err.WRONG_RECEIVER: If payment receiver is not this contract.
            err.WRONG_PAYMENT_AMOUNT: If payment amount doesn't cover MBR.
        """
        mbr_before = Global.current_application_address.min_balance

        assert self.is_representative(), err.UNAUTHORIZED

        assert self.is_valid_proposal(proposal_id), err.INVALID_PROPOSAL

        assert not self.paused.value, err.PAUSED

        proposal_app = Application(proposal_id.as_uint64())
        assert proposal_app not in self.proposals_vote_box, err.VOTE_ALREADY_PUBLISHED

        assert (
            vote.approval.as_uint64() + vote.rejection.as_uint64() <= const.BPS
        ), err.VOTE_NOT_BPS

        self.proposals_vote_box[proposal_app] = vote.copy()

        mbr_after = Global.current_application_address.min_balance
        mbr_fee = mbr_after - mbr_before

        # Check payment
        assert (
            payment.receiver == Global.current_application_address
        ), err.WRONG_RECEIVER
        assert payment.amount == mbr_fee, err.WRONG_PAYMENT_AMOUNT

        return

    @arc4.abimethod()
    def delete_vote(
        self,
        proposal_id: arc4.UInt64,
    ) -> None:
        """
        Delete a representative's vote.
        Cannot delete vote during voting stage of a proposal.

        Args:
            proposal_id (arc4.UInt64): App ID of proposal which vote to delete.

        Raises:
            err.UNAUTHORIZED: If the sender is not representative.
            err.PROPOSAL_VOTING: If proposal is in voting stage.
        """
        mbr_before = Global.current_application_address.min_balance

        assert self.is_representative(), err.UNAUTHORIZED

        assert not utils_prop.is_proposal_voting(
            proposal_id.as_uint64()
        ), err.PROPOSAL_VOTING

        proposal_app = Application(proposal_id.as_uint64())
        del self.proposals_vote_box[proposal_app]

        mbr_after = Global.current_application_address.min_balance

        # Send freed MBR to creator
        mbr_freed = mbr_before - mbr_after
        itxn.Payment(
            receiver=Global.creator_address,
            amount=mbr_freed,
        ).submit()

        return

    @arc4.abimethod(allow_actions=("DeleteApplication",))
    def delete(
        self,
    ) -> None:
        """
        Delete the representative.
        MUST BE CALLED BY THE REGISTRY CONTRACT.

        Raises:
            err.NOT_CREATOR: If the sender is not the Delegation Registry.
            err.UNDELETED_BOXES: If not all boxes were deleted.
        """
        assert self.is_creator(), err.NOT_CREATOR

        assert (
            Global.current_application_address.min_balance == Global.min_balance
        ), err.UNDELETED_BOXES

        itxn.Payment(
            receiver=Global.creator_address,
            amount=UInt64(0),
            close_remainder_to=Global.creator_address,
        ).submit()

        return

    # ---------------------------------
    # -------- Getter methods ---------
    # ---------------------------------
    @arc4.abimethod(readonly=True)
    def get_vote_box(
        self,
        proposal_id: arc4.UInt64,
    ) -> tuple[typ.Vote, bool]:
        """
        Get the representative's vote on a proposal.

        Args:
            proposal_id (arc4.UInt64): App ID of the proposal.

        Returns:
            typ.Vote: Representative's vote.
            bool: `True` if representative's vote exists, else `False`.
        """
        proposal_app = Application(proposal_id.as_uint64())

        exists = proposal_app in self.proposals_vote_box
        if exists:
            val = self.proposals_vote_box[proposal_app].copy()
        else:
            val = typ.Vote(approval=arc4.UInt64(0), rejection=arc4.UInt64(0))

        return val.copy(), exists

    @arc4.abimethod(readonly=True)
    def get_vote(
        self,
        proposal_id: arc4.UInt64,
    ) -> tuple[typ.Vote, bool]:
        """
        Get the representative's vote on a proposal.

        Args:
            proposal_id (arc4.UInt64): App ID of the proposal.

        Returns:
            typ.Vote: Representative's vote.
            bool: True if representative's vote exists and representative isn't paused.
        """
        [val, exists] = self.get_vote_box(proposal_id)

        is_valid = exists and self.paused.value == UInt64(0)

        return val.copy(), is_valid

    # ---------------------------------
    # ---------- Subroutines ----------
    # ---------------------------------
    @subroutine
    def is_creator(self) -> bool:
        return Txn.sender == Global.creator_address

    @subroutine
    def is_representative(self) -> bool:
        return Txn.sender == self.representative_address.value

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
