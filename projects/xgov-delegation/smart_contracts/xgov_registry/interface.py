from abc import ABC, abstractmethod

from algopy import (
    ARC4Contract,
    arc4,
)

import smart_contracts.common.abi_types as typ


class IXGovRegistry(
    ARC4Contract,
    ABC,
):
    @abstractmethod
    @arc4.abimethod(readonly=True)
    def get_xgov_box(
        self, *, xgov_address: arc4.Address
    ) -> tuple[typ.XGovBoxValue, bool]:
        """
        Returns the xGov box for the given address.

        Args:
            xgov_address (arc4.Address): The address of the xGov

        Returns:
            typ.XGovBoxValue: The xGov box value
            bool: `True` if xGov box exists, else `False`
        """
        pass

    @abstractmethod
    @arc4.abimethod()
    def vote_proposal(
        self,
        *,
        proposal_id: arc4.UInt64,
        xgov_address: arc4.Address,
        approval_votes: arc4.UInt64,
        rejection_votes: arc4.UInt64,
    ) -> None:
        """
        Votes on a Proposal.

        Args:
            proposal_id (arc4.UInt64): The application ID of the Proposal app being voted on
            xgov_address: (arc4.Address): The address of the xGov being voted on behalf of
            approval_votes: (arc4.UInt64): The number of approvals votes allocated
            rejection_votes: (arc4.UInt64): The number of rejections votes allocated

        Raises:
            err.INVALID_PROPOSAL: If the Proposal ID is not a Proposal contract
            err.PROPOSAL_IS_NOT_VOTING: If the Proposal is not in a voting session
            err.UNAUTHORIZED: If the xGov_address is not an xGov
            err.MUST_BE_VOTING_ADDRESS: If the sender is not the voting_address
            err.PAUSED_REGISTRY: If the xGov Registry is paused
            err.WRONG_PROPOSAL_STATUS: If the Proposal is not in the voting state
            err.MISSING_CONFIG: If one of the required configuration values is missing
            err.VOTER_NOT_FOUND: If the xGov is not found in the Proposal's voting registry
            err.VOTER_ALREADY_VOTED: If the xGov has already voted on this Proposal
            err.VOTES_EXCEEDED: If the total votes exceed the maximum allowed
            err.VOTING_PERIOD_EXPIRED: If the voting period for the Proposal has expired
        """

        pass

    @arc4.abimethod()
    def set_voting_account(
        self, *, xgov_address: arc4.Address, voting_address: arc4.Address
    ) -> None:
        """
        Sets the Voting Address for the xGov.

        Args:
            xgov_address (arc4.Address): The xGov address delegating voting power.
            voting_address (arc4.Address): The voting account address to delegate voting power to.

        Raises:
            err.UNAUTHORIZED: If the sender is not currently an xGov.
            err.VOTING_ADDRESS_MUST_BE_DIFFERENT: If the new voting account is the same as currently set.
        """

    pass
