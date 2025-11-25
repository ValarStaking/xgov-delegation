# pyright: reportMissingModuleSource=false

from algopy import (
    Account,
    ARC4Contract,
    BoxMap,
    Global,
    UInt64,
    arc4,
    itxn,
)

from smart_contracts.proposal_mock.contract import ProposalMock

from ..common import abi_types as typ
from ..xgov_registry import config as reg_cfg


class XgovRegistryMock(ARC4Contract, avm_version=10):
    def __init__(self) -> None:
        self.xgov_box = BoxMap(
            Account,
            typ.XGovBoxValue,
            key_prefix=reg_cfg.XGOV_BOX_MAP_PREFIX,
        )

    @arc4.abimethod()
    def create_proposal(
        self,
    ) -> UInt64:
        """
        Create an empty proposal.

        Returns:
            UInt64: The ID of the created proposal.

        """
        res = arc4.arc4_create(
            ProposalMock,
        )

        itxn.Payment(
            receiver=res.created_app.address,
            amount=Global.min_balance,
        ).submit()

        return res.created_app.id

    @arc4.abimethod()
    def vote_proposal(
        self,
        proposal_id: arc4.UInt64,
        xgov_address: arc4.Address,
        approval_votes: arc4.UInt64,
        rejection_votes: arc4.UInt64,
    ) -> None:
        """
        Vote on a proposal

        Args:
            proposal_id (arc4.UInt64): The application ID of the Proposal app being voted on
            xgov_address: (arc4.Address): The address of the xGov being voted on behalf of
            approval_votes: (arc4.UInt64): The number of approvals votes allocated
            rejection_votes: (arc4.UInt64): The number of rejections votes allocated
        """
        arc4.abi_call(
            ProposalMock.vote,
            xgov_address,
            approval_votes,
            rejection_votes,
            app_id=proposal_id.as_uint64(),
        )

    @arc4.abimethod()
    def set_voting_account(
        self, xgov_address: arc4.Address, voting_address: arc4.Address
    ) -> None:
        """
        Sets the Voting Address for the xGov.

        Args:
            xgov_address (arc4.Address): The xGov address delegating voting power
            voting_address (arc4.Address): The voting account address to delegate voting power to
        """
        self.xgov_box[xgov_address.native].voting_address = voting_address

        return

    @arc4.abimethod(readonly=True)
    def get_xgov_box(self, xgov_address: arc4.Address) -> tuple[typ.XGovBoxValue, bool]:
        """
        Returns the xGov box for the given address.

        Args:
            xgov_address (arc4.Address): The address of the xGov

        Returns:
            typ.XGovBoxValue: The xGov box value
            bool: `True` if xGov box exists, else `False`
        """
        exists = xgov_address.native in self.xgov_box
        if exists:
            val = self.xgov_box[xgov_address.native].copy()
        else:
            val = typ.XGovBoxValue(
                voting_address=arc4.Address(),
                voted_proposals=arc4.UInt64(0),
                last_vote_timestamp=arc4.UInt64(0),
                subscription_round=arc4.UInt64(0),
            )

        return val.copy(), exists

    @arc4.abimethod()
    def set_xgov_box(
        self,
        xgov_address: arc4.Address,
        xgov_box: typ.XGovBoxValue,
    ) -> None:
        """
        Sets the xGov box for the given address.

        Args:
            xgov_address (arc4.Address): The address of the xGov.
            xgov_box (typ.XGovBoxValue): The xgov box content.
        """
        self.xgov_box[xgov_address.native] = xgov_box.copy()

        return

    @arc4.abimethod()
    def del_xgov_box(
        self,
        xgov_address: arc4.Address,
    ) -> None:
        """
        Deletes the xGov box for the given address.

        Args:
            xgov_address (arc4.Address): The address of the xGov.
        """
        del self.xgov_box[xgov_address.native]

        return
