# pyright: reportMissingModuleSource=false


from algopy import (
    Application,
    ARC4Contract,
    Box,
    BoxMap,
    Bytes,
    Global,
    GlobalState,
    StateTotals,
    TemplateVar,
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
from smart_contracts.representative import config as representative_cfg
from smart_contracts.representative import contract as representative_contract
from smart_contracts.voter import config as voter_cfg
from smart_contracts.voter import contract as voter_contract
from smart_contracts.xgov_registry.interface import IXGovRegistry

from . import config as cfg


class DelegationRegistry(
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
        self.manager_address = GlobalState(
            arc4.Address(),
            key=cfg.GS_KEY_MANAGER_ADDRESS,
        )
        self.xgov_registry_app = GlobalState(
            Application(),
            key=cfg.GS_KEY_XGOV_REGISTRY_APP,
        )
        self.vote_fees = GlobalState(
            typ.Fees,
            key=cfg.GS_KEY_VOTE_FEES,
        )
        self.representative_fee = GlobalState(
            UInt64(),
            key=cfg.GS_KEY_REPRESENTATIVE_FEE,
        )
        self.vote_trigger_award = GlobalState(
            UInt64(),
            key=cfg.GS_KEY_VOTE_TRIGGER_AWARD,
        )
        self.paused_registry = GlobalState(UInt64(), key=cfg.GS_KEY_PAUSED_REGISTRY)
        self.votes_left = GlobalState(UInt64(), key=cfg.GS_KEY_VOTES_LEFT)
        self.trigger_fund = GlobalState(UInt64(), key=cfg.GS_KEY_TRIGGER_FUND)

        # Boxes
        self.voters_box = BoxMap(
            arc4.Address,
            Application,
            key_prefix=cfg.VOTERS_MAP_PREFIX,
        )
        self.representatives_box = BoxMap(
            arc4.Address,
            Application,
            key_prefix=cfg.REPRESENTATIVE_MAP_PREFIX,
        )

        self.voter_approval_program = Box(Bytes, key=cfg.CONTRACT_VOTER_BOX)
        self.representative_approval_program = Box(
            Bytes, key=cfg.CONTRACT_REPRESENTATIVE_BOX
        )

    # ---------------------------------
    # ---------- Management  ----------
    # ---------------------------------
    @arc4.abimethod(create="require")
    def create(
        self,
        xgov_registry_id: arc4.UInt64,
    ) -> None:
        """
        Create a new Delegation Registry.
        The registry is created as paused.

        Args:
            xgov_registry_id (arc4.UInt64): ID of xGov Registry app this Delegation Registry uses.
        """
        self.manager_address.value = arc4.Address(Txn.sender)
        self.xgov_registry_app.value = Application(xgov_registry_id.as_uint64())
        self.paused_registry.value = UInt64(1)
        assert self.entropy() == TemplateVar[Bytes]("entropy")

        return

    @arc4.abimethod()
    def set_manager(self, manager: arc4.Address) -> None:
        """
        Sets the DelegationRegistry Manager.

        Args:
            manager (arc4.Address): Address of the new DelegationRegistry Manager.

        Raises:
            err.UNAUTHORIZED: If the sender is not the current DelegationRegistry Manager.
        """

        assert self.is_manager(), err.UNAUTHORIZED
        self.manager_address.value = manager

    @arc4.abimethod()
    def config_delegation_registry(
        self,
        vote_fees: typ.Fees,
        representative_fee: arc4.UInt64,
        vote_trigger_award: arc4.UInt64,
    ) -> None:
        """
        Set the configuration of the Delegation Registry.

        Args:
            vote_fees (typ.Fees): Fees to pay for a vote.
            representative_fee (arc4.UInt64): Fee to become a representative.
            vote_trigger_award (arc4.UInt64): Fee received as a reward for triggering a vote casting.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Delegation Registry manager.
            err.TRIGGER_FUND_INSUFFICIENT: If trigger fund would become insufficient with the change in trigger award.
            err.INCONSISTENT_VOTE_FEES: If vote fee for xGov were higher than for others.
            err.INCONSISTENT_TRIGGER_REWARD: If trigger award were higher than min vote fee charged.
        """
        assert self.is_manager(), err.UNAUTHORIZED

        self.vote_fees.value = vote_fees.copy()
        self.representative_fee.value = representative_fee.as_uint64()
        self.vote_trigger_award.value = vote_trigger_award.as_uint64()

        # Recalculate needed trigger fund
        self.update_trigger_fund()

        # Validate config
        assert (
            self.trigger_fund.value
            <= Global.current_application_address.balance
            - Global.current_application_address.min_balance
        ), err.TRIGGER_FUND_INSUFFICIENT

        assert (
            self.vote_fees.value.xgov <= self.vote_fees.value.other
        ), err.INCONSISTENT_VOTE_FEES

        assert (
            self.vote_trigger_award.value <= self.vote_fees.value.xgov
        ), err.INCONSISTENT_TRIGGER_AWARD

        return

    @arc4.abimethod()
    def withdraw_balance(self) -> None:
        """
        Withdraw outstanding Algos, excluding MBR and trigger award funds, from the Delegation Registry.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Registry Manager.
            err.INSUFFICIENT_FUNDS: If there are no funds to withdraw.
        """

        assert self.is_manager(), err.UNAUTHORIZED

        # Calculate the amount to withdraw
        amount = (
            Global.current_application_address.balance
            - Global.current_application_address.min_balance
            - self.trigger_fund.value
        )

        assert amount > 0, err.INSUFFICIENT_FUNDS
        itxn.Payment(
            receiver=self.manager_address.value.native,
            amount=amount,
        ).submit()

        return

    @arc4.abimethod()
    def pause_registry(self) -> None:
        """
        Pause the Delegation Registry.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Delegation Registry manager.
        """

        assert self.is_manager(), err.UNAUTHORIZED
        self.paused_registry.value = UInt64(1)

        return

    @arc4.abimethod()
    def resume_registry(self) -> None:
        """
        Resume the Delegation Registry.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Delegation Registry manager.
        """

        assert self.is_manager(), err.UNAUTHORIZED
        self.paused_registry.value = UInt64(0)

        return

    @arc4.abimethod()
    def init_contract(
        self,
        contract: typ.ContractName,
        size: arc4.UInt64,
    ) -> None:
        """
        Initialize loading of approval program for a contract.

        Args:
            contract (typ.ContractName): Contract name for which to load the approval program.
            size (arc4.UInt64): The size of the approval program of a contract.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Delegation Registry manager.
        """

        assert self.is_manager(), err.UNAUTHORIZED

        box = Box(Bytes, key=contract.bytes)
        contents, exists = box.maybe()
        if exists:
            box.resize(size.as_uint64())
        else:
            # Initialize the approval program
            box.create(size=size.as_uint64())

        return

    @arc4.abimethod()
    def load_contract(
        self,
        contract: typ.ContractName,
        offset: arc4.UInt64,
        data: Bytes,
    ) -> None:
        """
        Load the approval program for a contract.

        Args:
            contract (typ.ContractName): Contract name for which to load the approval program.
            offset (arc4.UInt64): The offset in the approval program.
            data (Bytes): The data to load into the approval program.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Delegation Registry manager.
        """

        assert self.is_manager(), err.UNAUTHORIZED

        box = Box(Bytes, key=contract.bytes)

        # Load the approval program
        box.replace(start_index=offset.as_uint64(), value=data)

        return

    @arc4.abimethod()
    def key_reg_registry(
        self,
        payment: gtxn.PaymentTransaction,
        key_reg_info: typ.KeyRegTxnInfo,
    ) -> None:
        """
        Issues a key (de)registration transaction for the Delegation Registry.

        Args:
            payment (gtxn.PaymentTransaction): Payment transaction to cover costs for the key (de)registration fee.
            key_reg_info (typ.KeyRegTxnInfo): Key registration information to send.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Delegation Registry manager.
        """

        assert self.is_manager(), err.UNAUTHORIZED

        # Check if payment for covering the key reg fee was made to this contract
        assert (
            payment.receiver == Global.current_application_address
        ), err.WRONG_RECEIVER
        key_reg_txn_fee = payment.amount

        # Issue the key registration transaction
        itxn.KeyRegistration(
            vote_key=key_reg_info.vote_pk.bytes,
            selection_key=key_reg_info.selection_pk.bytes,
            vote_first=key_reg_info.vote_first.as_uint64(),
            vote_last=key_reg_info.vote_last.as_uint64(),
            vote_key_dilution=key_reg_info.vote_key_dilution.as_uint64(),
            state_proof_key=key_reg_info.state_proof_pk.bytes,
            fee=key_reg_txn_fee,
        ).submit()

        return

    @arc4.abimethod(allow_actions=["UpdateApplication"])
    def update_registry(self) -> None:
        """
        Updates the Delegation Registry contract.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Delegation Registry manager.
        """

        assert self.is_manager(), err.UNAUTHORIZED

        return

    @arc4.abimethod()
    def update_voter(
        self,
        xgov_address: arc4.Address,
    ) -> None:
        """
        Update an existing Voter contract.

        Args:
            xgov_address (arc4.Address): Address of the xGov.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Delegation Registry manager.
            err.NOT_VOTER: If xGov has not registered a Voter.
        """
        assert self.is_manager(), err.UNAUTHORIZED

        assert xgov_address in self.voters_box, err.NOT_VOTER

        box = Box(Bytes, key=Bytes(cfg.CONTRACT_VOTER_BOX))
        # Assume program size is < const.MAX_STACK
        approval_program = box.extract(0, box.length)

        arc4.abi_call(
            voter_contract.Voter.update,
            app_id=self.voters_box[xgov_address],
            approval_program=approval_program,
            clear_state_program=const.MIN_PROGRAM,
        )

        return

    @arc4.abimethod()
    def update_representative(
        self,
        representative_address: arc4.Address,
    ) -> None:
        """
        Update an existing representative contract.

        Args:
            representative_address (arc4.Address): Address of the representative.

        Raises:
            err.UNAUTHORIZED: If the sender is not the Delegation Registry manager.
            err.NOT_REPRESENTATIVE: If representative does not exist.
        """
        assert self.is_manager(), err.UNAUTHORIZED

        assert (
            representative_address in self.representatives_box
        ), err.NOT_REPRESENTATIVE

        box = Box(Bytes, key=Bytes(cfg.CONTRACT_REPRESENTATIVE_BOX))
        # Assume program size is < const.MAX_STACK
        approval_program = box.extract(0, box.length)

        arc4.abi_call(
            representative_contract.Representative.update,
            app_id=self.representatives_box[representative_address],
            approval_program=approval_program,
            clear_state_program=const.MIN_PROGRAM,
        )

        return

    @arc4.abimethod()
    def prepare_voter(
        self,
        payment: gtxn.PaymentTransaction,
    ) -> None:
        """
        Creates an unassigned Voter application that can be consumed by any Voter who registers.
        Can be called by anyone.

        Args:
            payment (gtxn.PaymentTransaction): Payment transaction to cover the MBR.

        Raises:
            err.WRONG_RECEIVER: If payment receiver is not this contract.
            err.WRONG_PAYMENT_AMOUNT: If payment amount doesn't cover MBR.
        """
        mbr_before = Global.current_application_address.min_balance

        # Create a new Voter application
        box = Box(Bytes, key=Bytes(cfg.CONTRACT_VOTER_BOX))
        # Assume program size is < const.MAX_STACK
        approval_program = box.extract(0, box.length)

        txn = arc4.abi_call(
            voter_contract.Voter.create,
            approval_program=approval_program,
            clear_state_program=const.MIN_PROGRAM,
            global_num_uint=voter_cfg.GLOBAL_UINTS,
            global_num_bytes=voter_cfg.GLOBAL_BYTES,
            local_num_uint=voter_cfg.LOCAL_UINTS,
            local_num_bytes=voter_cfg.LOCAL_BYTES,
            extra_program_pages=const.MAX_EXTRA_PAGES_PER_APP,
        )

        # Fund the created app with MBR
        itxn.Payment(
            receiver=txn.created_app.address,
            amount=Global.min_balance,
        ).submit()

        mbr_after = Global.current_application_address.min_balance
        mbr_fee = mbr_after - mbr_before

        # Check payment
        assert (
            payment.receiver == Global.current_application_address
        ), err.WRONG_RECEIVER
        assert payment.amount == mbr_fee + Global.min_balance, err.WRONG_PAYMENT_AMOUNT

        return

    # ---------------------------------
    # ----------    Voter    ----------
    # ---------------------------------
    @arc4.abimethod()
    def register_voter(
        self,
        payment: gtxn.PaymentTransaction,
        xgov_address: arc4.Address,
        available_voter_id: UInt64,
    ) -> UInt64:
        """
        Create a Voter for an xGov at Delegation Registry.

        Args:
            payment (gtxn.PaymentTransaction): Payment transaction to cover the MBR.
            xgov_address (arc4.Address): Address of the xGov.
            available_voter_id: App ID of an unassigned Voter app.

        Returns:
            UInt64: ID of assigned Voter.

        Raises:
            err.PAUSED_REGISTRY: If the Delegation Registry is paused.
            err.ALREADY_VOTER: If Voter has already been registered for the xGov.
            err.NOT_XGOV: If given xgov_address is actually not an xGov.
            err.UNAUTHORIZED: If sender is neither xGov or its voting_address, i.e. manager.
            err.WRONG_RECEIVER: If payment receiver is not this contract.
            err.WRONG_PAYMENT_AMOUNT: If payment amount doesn't cover MBR.
        """
        mbr_before = Global.current_application_address.min_balance

        assert not self.paused_registry.value, err.PAUSED_REGISTRY
        assert xgov_address not in self.voters_box, err.ALREADY_VOTER

        # Get xgov_address box
        [xgov_box, exists], txn = arc4.abi_call(
            IXGovRegistry.get_xgov_box,
            xgov_address,
            app_id=self.xgov_registry_app.value,
        )
        assert exists, err.NOT_XGOV

        manager_address = xgov_box.voting_address
        is_manager = arc4.Address(Txn.sender) == manager_address
        is_xgov = arc4.Address(Txn.sender) == xgov_address
        assert is_xgov or is_manager, err.UNAUTHORIZED

        # Create a new Voter application
        box = Box(Bytes, key=Bytes(cfg.CONTRACT_VOTER_BOX))
        # Assume program size is < const.MAX_STACK
        approval_program = box.extract(0, box.length)

        txn = arc4.abi_call(
            voter_contract.Voter.create,
            approval_program=approval_program,
            clear_state_program=const.MIN_PROGRAM,
            global_num_uint=voter_cfg.GLOBAL_UINTS,
            global_num_bytes=voter_cfg.GLOBAL_BYTES,
            local_num_uint=voter_cfg.LOCAL_UINTS,
            local_num_bytes=voter_cfg.LOCAL_BYTES,
            extra_program_pages=const.MAX_EXTRA_PAGES_PER_APP,
        )

        # Fund the created app with MBR
        itxn.Payment(
            receiver=txn.created_app.address,
            amount=Global.min_balance,
        ).submit()

        # Check if selected Voter is unassigned
        voter_app = Application(available_voter_id)

        xgov_address_bytes, exists = op.AppGlobal.get_ex_bytes(
            voter_app,
            voter_cfg.GS_KEY_XGOV_ADDRESS,
        )
        assert (
            arc4.Address(xgov_address_bytes) == Global.zero_address
        ), err.VOTER_ASSIGNED

        # Assign available Voter to the xGov
        arc4.abi_call(
            voter_contract.Voter.assign_xgov,
            xgov_address,
            arc4.Address(Txn.sender),
            app_id=voter_app,
        )
        self.voters_box[xgov_address] = voter_app

        mbr_after = Global.current_application_address.min_balance
        mbr_fee = mbr_after - mbr_before

        # Check payment
        assert (
            payment.receiver == Global.current_application_address
        ), err.WRONG_RECEIVER
        assert payment.amount == mbr_fee + Global.min_balance, err.WRONG_PAYMENT_AMOUNT

        return voter_app.id

    @arc4.abimethod()
    def add_votes(
        self,
        payment: gtxn.PaymentTransaction,
        xgov_address: arc4.Address,
        add_votes: arc4.UInt64,
    ) -> None:
        """
        Pays for the votes of an xGov.
        Can be called only by xgov_address, voting_address or voter's manager_address.
        If xGov is calling it, the fee is lower.

        Args:
            payment (gtxn.PaymentTransaction): Payment for the votes.
            xgov_address (arc4.Address): Address of the xGov.
            add_votes (arc4.UInt64): Number of votes to add.

        Raises:
            err.PAUSED_REGISTRY: If the Delegation Registry is paused.
            err.NOT_VOTER: If xGov has not registered a Voter.
            err.NOT_XGOV: If given xgov_address is actually not an xGov.
            err.UNAUTHORIZED: If sender is neither xgov_address, voting_address nor voter's manager_address.
            err.WRONG_RECEIVER: If payment receiver is not this contract.
            err.WRONG_PAYMENT_AMOUNT: If payment amount doesn't cover the fee for the requested votes.
        """
        assert not self.paused_registry.value, err.PAUSED_REGISTRY
        assert xgov_address in self.voters_box, err.NOT_VOTER

        voter_app = self.voters_box[xgov_address]

        sender = arc4.Address(Txn.sender)
        if sender == xgov_address:
            vote_fee = self.vote_fees.value.xgov.as_uint64()
        else:
            vote_fee = self.vote_fees.value.other.as_uint64()

            # Get xgov_address box
            [xgov_box, exists], txn = arc4.abi_call(
                IXGovRegistry.get_xgov_box,
                xgov_address,
                app_id=self.xgov_registry_app.value,
            )
            assert exists, err.NOT_XGOV

            manager_address_bytes, exists = op.AppGlobal.get_ex_bytes(
                voter_app,
                voter_cfg.GS_KEY_MANAGER_ADDRESS,
            )
            manager_address = arc4.Address(manager_address_bytes)

            assert (
                sender == xgov_box.voting_address or sender == manager_address
            ), err.UNAUTHORIZED

        arc4.abi_call(
            voter_contract.Voter.add_votes,
            add_votes,
            app_id=voter_app,
        )

        self.votes_left.value += add_votes.as_uint64()
        self.update_trigger_fund()

        # Check payment
        fee = vote_fee * add_votes.as_uint64()
        assert (
            payment.receiver == Global.current_application_address
        ), err.WRONG_RECEIVER
        assert payment.amount == fee, err.WRONG_PAYMENT_AMOUNT

        return

    @arc4.abimethod()
    def trigger_vote(
        self,
        xgov_address: arc4.Address,
        proposal_id: arc4.UInt64,
    ) -> None:
        """
        Trigger vote for xGov on a proposal.
        Can be called by anyone.

        Args:
            xgov_address (arc4.Address): Address of the xGov.
            proposal_id (arc4.UInt64): App ID of proposal on which to trigger vote.

        Raises:
            err.PAUSED_REGISTRY: If the Delegation Registry is paused.
            err.NOT_VOTER: If xGov has not registered a Voter.
        """
        assert not self.paused_registry.value, err.PAUSED_REGISTRY
        assert xgov_address in self.voters_box, err.NOT_VOTER

        arc4.abi_call(
            voter_contract.Voter.vote_representative,
            proposal_id,
            app_id=self.voters_box[xgov_address],
        )

        self.votes_left.value -= 1
        self.update_trigger_fund()

        # Send trigger award to sender
        itxn.Payment(
            receiver=Txn.sender,
            amount=self.vote_trigger_award.value,
        ).submit()

        return

    @arc4.abimethod()
    def unregister_voter(
        self,
        xgov_address: arc4.Address,
    ) -> None:
        """
        Unregister Voter of an xGov from Delegation Registry.

        Args:
            xgov_address (arc4.Address): Address of the xGov.

        Raises:
            err.PAUSED_REGISTRY: If the Delegation Registry is paused.
            err.NOT_VOTER: If xGov has not registered a Voter.
            err.UNAUTHORIZED: If the sender is not the xGov or its manager.
        """
        mbr_before = Global.current_application_address.min_balance

        assert not self.paused_registry.value, err.PAUSED_REGISTRY
        assert xgov_address in self.voters_box, err.NOT_VOTER
        voter_app = self.voters_box[xgov_address]

        manager_address_bytes, exists = op.AppGlobal.get_ex_bytes(
            voter_app, voter_cfg.GS_KEY_MANAGER_ADDRESS
        )
        manager_address = arc4.Address.from_bytes(manager_address_bytes)

        # Get xgov_address box
        [xgov_box, exists], txn = arc4.abi_call(
            IXGovRegistry.get_xgov_box,
            xgov_address,
            app_id=self.xgov_registry_app.value,
        )
        # If xGov has unsubscribed from the xGov program, anyone can unregister it from DelegationRegistry.
        # Otherwise, only xgov_address or manager_address can unregister it.
        if exists:
            assert (
                Txn.sender == xgov_address or Txn.sender == manager_address
            ), err.UNAUTHORIZED

            # Set voting_address to the manager_address if it isn't yet set to xgov_address or manager_address
            # before deleting the xGov from DelegationRegistry.
            if not (
                xgov_box.voting_address == manager_address
                or xgov_box.voting_address == xgov_address
            ):
                arc4.abi_call(
                    voter_contract.Voter.yield_voting_rights,
                    manager_address,
                    app_id=voter_app,
                )

        # Reduce paid votes
        votes_left, exists = op.AppGlobal.get_ex_uint64(
            voter_app, voter_cfg.GS_KEY_VOTES_LEFT
        )
        self.votes_left.value -= votes_left
        self.update_trigger_fund()

        arc4.abi_call(
            voter_contract.Voter.delete,
            app_id=voter_app,
        )

        # Delete Voter box
        del self.voters_box[xgov_address]

        mbr_after = Global.current_application_address.min_balance
        mbr_fee = mbr_before - mbr_after

        itxn.Payment(
            receiver=xgov_address.native,
            amount=mbr_fee,
        ).submit()

        return

    # ---------------------------------
    # -------- Representative ---------
    # ---------------------------------
    @arc4.abimethod()
    def register_representative(
        self,
        payment: gtxn.PaymentTransaction,
    ) -> UInt64:
        """
        Create a new representative.

        Args:
            payment (gtxn.PaymentTransaction): Payment to cover representative registration fee and MBR.

        Returns:
            UInt64: ID of created representative.

        Raises:
            err.PAUSED_REGISTRY: If the Delegation Registry is paused.
            err.ALREADY_REPRESENTATIVE: If this representative already exists.
            err.WRONG_RECEIVER: If payment receiver is not this contract.
            err.WRONG_PAYMENT_AMOUNT: If payment amount doesn't cover representative registration fee and MRB.
        """
        mbr_before = Global.current_application_address.min_balance

        assert not self.paused_registry.value, err.PAUSED_REGISTRY

        representative_address = arc4.Address(Txn.sender)
        assert (
            representative_address not in self.representatives_box
        ), err.ALREADY_REPRESENTATIVE

        box = Box(Bytes, key=Bytes(cfg.CONTRACT_REPRESENTATIVE_BOX))
        # Assume program size is < const.MAX_STACK
        approval_program = box.extract(0, box.length)

        txn = arc4.abi_call(
            representative_contract.Representative.create,
            representative_address,
            approval_program=approval_program,
            clear_state_program=const.MIN_PROGRAM,
            global_num_uint=representative_cfg.GLOBAL_UINTS,
            global_num_bytes=representative_cfg.GLOBAL_BYTES,
            local_num_uint=representative_cfg.LOCAL_UINTS,
            local_num_bytes=representative_cfg.LOCAL_BYTES,
            extra_program_pages=const.MAX_EXTRA_PAGES_PER_APP,
        )

        # Fund the created app with MBR
        itxn.Payment(
            receiver=txn.created_app.address,
            amount=Global.min_balance,
        ).submit()

        # Store representative
        representative_id = txn.created_app.id
        self.representatives_box[representative_address] = Application(
            representative_id
        )

        mbr_after = Global.current_application_address.min_balance
        mbr_fee = mbr_after - mbr_before

        # Check payment
        assert (
            payment.receiver == Global.current_application_address
        ), err.WRONG_RECEIVER
        assert payment.amount == (
            mbr_fee + self.representative_fee.value + Global.min_balance
        ), err.WRONG_PAYMENT_AMOUNT

        return representative_id

    @arc4.abimethod()
    def unregister_representative(
        self,
    ) -> None:
        """
        Unregister yourself as representative from the Delegation Registry.

        Raises:
            err.PAUSED_REGISTRY: If the Delegation Registry is paused.
            err.NOT_REPRESENTATIVE: If sender is not a representative.
        """
        mbr_before = Global.current_application_address.min_balance

        assert not self.paused_registry.value, err.PAUSED_REGISTRY

        representative = arc4.Address(Txn.sender)
        assert representative in self.representatives_box, err.NOT_REPRESENTATIVE

        arc4.abi_call(
            representative_contract.Representative.delete,
            app_id=self.representatives_box[representative],
        )

        # Delete representative box
        del self.representatives_box[representative]

        mbr_after = Global.current_application_address.min_balance
        mbr_fee = mbr_before - mbr_after

        itxn.Payment(
            receiver=representative.native,
            amount=mbr_fee,
        ).submit()

        return

    # ---------------------------------
    # -------- Getter methods ---------
    # ---------------------------------
    @arc4.abimethod(readonly=True)
    def get_voter_app_id(
        self,
        xgov_address: arc4.Address,
    ) -> tuple[UInt64, bool]:
        """
        Get Voter app ID for an xGov.

        Args:
            xgov_address (arc4.Address): xGov address.

        Returns:
            UInt64: Voter app ID.
            bool: `True` if Voter app exists, else `False`.
        """
        exists = xgov_address in self.voters_box
        if exists:
            val = self.voters_box[xgov_address].id
        else:
            val = UInt64(0)

        return val, exists

    @arc4.abimethod(readonly=True)
    def get_representative_app_id(
        self,
        representative_address: arc4.Address,
    ) -> tuple[UInt64, bool]:
        """
        Get the app ID of xGov.

        Args:
            representative_address (arc4.Address): Representative address.

        Returns:
            UInt64: App ID of representative.
            bool: `True` if Representative app exists, else `False`.
        """
        exists = representative_address in self.representatives_box
        if exists:
            val = self.representatives_box[representative_address].id
        else:
            val = UInt64(0)

        return val, exists

    # ---------------------------------
    # ---------- Subroutines ----------
    # ---------------------------------
    @subroutine
    def entropy(self) -> Bytes:
        return TemplateVar[Bytes]("entropy")  # trick to allow fresh deployment

    @subroutine
    def is_creator(self) -> bool:
        return Txn.sender == Global.creator_address

    @subroutine
    def is_manager(self) -> bool:
        return Txn.sender == self.manager_address.value.native

    @subroutine
    def update_trigger_fund(self) -> None:
        self.trigger_fund.value = self.vote_trigger_award.value * self.votes_left.value
