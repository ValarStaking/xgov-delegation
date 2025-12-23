from abc import ABC, abstractmethod

from algopy import (
    ARC4Contract,
    arc4,
)


class IProposal(
    ARC4Contract,
    ABC,
):
    @abstractmethod
    @arc4.abimethod(readonly=True)
    def get_voter_box(self, *, voter_address: arc4.Address) -> tuple[arc4.UInt64, bool]:
        """
        Returns the Voter box for the given address.

        Args:
            voter_address (arc4.Address): The address of the Voter

        Returns:
            votes: The voter's votes
            bool: `True` if voter's box exists, else `False`
        """
        pass
