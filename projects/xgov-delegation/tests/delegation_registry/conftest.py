import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AppClientCompilationParams,
    CommonAppCallParams,
    PaymentParams,
    SigningAccount,
)
from algokit_utils.config import config
from common.helpers import (
    get_sc_representative_mbr,
    get_sc_voter_mbr,
    get_sc_voter_unassigned_mbr,
    get_vote_mbr,
    load_sc_data_size_per_transaction,
)

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    AddVotesArgs,
    ConfigDelegationRegistryArgs,
    CreateArgs,
    DelegationRegistryClient,
    DelegationRegistryFactory,
    Fees,
    InitContractArgs,
    LoadContractArgs,
    PrepareVoterArgs,
    RegisterRepresentativeArgs,
    RegisterVoterArgs,
)
from smart_contracts.artifacts.proposal_mock.proposal_mock_client import (
    ProposalMockClient,
    SetStatusArgs,
    SetVoteOpenTsArgs,
    SetVoterBoxArgs,
    SetVotingDurationArgs,
)
from smart_contracts.artifacts.representative.representative_client import (
    PublishVoteArgs,
    RepresentativeClient,
    RepresentativeFactory,
    Vote,
)
from smart_contracts.artifacts.voter.voter_client import (
    SetRepresentativeArgs,
    SetWindowArgs,
    VoterClient,
    VoterFactory,
)
from smart_contracts.artifacts.xgov_registry_mock.xgov_registry_mock_client import (
    SetVotingAccountArgs,
    SetXgovBoxArgs,
    XGovBoxValue,
    XgovRegistryMockClient,
    XgovRegistryMockFactory,
)
from smart_contracts.common import constants as const
from smart_contracts.delegation_registry import config as regcfg
from smart_contracts.voter import config as voter_cfg
from tests.common import (
    DEFAULT_PROPOSAL_STATUS,
    DEFAULT_PROPOSAL_VOTE_OPEN_TS,
    DEFAULT_VOTING_DURATION,
    INITIAL_FUNDS,
)
from tests.delegation_registry.common import get_available_voter


@pytest.fixture(scope="session")
def xgov_registry_mock_client(
    algorand_client: AlgorandClient,
    deployer: SigningAccount,
) -> XgovRegistryMockClient:
    config.configure(
        debug=False,
        populate_app_call_resources=True,
    )

    factory = algorand_client.client.get_typed_app_factory(
        typed_factory=XgovRegistryMockFactory,
        default_sender=deployer.address,
    )
    client, _ = factory.send.create.bare()  # type: ignore
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=client.app_address,
        min_spending_balance=AlgoAmount(micro_algo=int(INITIAL_FUNDS.micro_algo) * 100),
    )

    return client


@pytest.fixture(scope="function")
def proposal_mock_client(
    algorand_client: AlgorandClient,
    xgov_registry_mock_client: XgovRegistryMockClient,
    deployer: SigningAccount,
) -> ProposalMockClient:

    result = xgov_registry_mock_client.send.create_proposal(
        params=CommonAppCallParams(
            extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
        ),
    )
    proposal_id = result.abi_return

    client = xgov_registry_mock_client.algorand.client.get_typed_app_client_by_id(
        typed_client=ProposalMockClient,
        app_id=proposal_id,
        default_sender=deployer.address,
    )

    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=client.app_address,
        min_spending_balance=INITIAL_FUNDS,
    )

    client.send.set_status(args=SetStatusArgs(status=DEFAULT_PROPOSAL_STATUS))
    client.send.set_voting_duration(
        args=SetVotingDurationArgs(voting_duration=DEFAULT_VOTING_DURATION)
    )
    client.send.set_vote_open_ts(
        args=SetVoteOpenTsArgs(vote_open_ts=DEFAULT_PROPOSAL_VOTE_OPEN_TS),
    )

    return client


@pytest.fixture(scope="function")
def delegation_registry_client_uninitialized(
    algorand_client: AlgorandClient,
    xgov_registry_mock_client: XgovRegistryMockClient,
    deployer: SigningAccount,
) -> DelegationRegistryClient:
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=deployer,
        min_spending_balance=INITIAL_FUNDS,
    )

    factory = algorand_client.client.get_typed_app_factory(
        typed_factory=DelegationRegistryFactory,
        default_sender=deployer.address,
        compilation_params=AppClientCompilationParams(
            deploy_time_params={"entropy": b""}
        ),
    )
    client, _ = factory.send.create.create(
        args=CreateArgs(xgov_registry_id=xgov_registry_mock_client.app_id)
    )
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=client.app_address,
        min_spending_balance=INITIAL_FUNDS,
    )

    return client


@pytest.fixture(scope="function")
def delegation_registry_client(
    algorand_client: AlgorandClient,
    delegation_registry_client_uninitialized: DelegationRegistryClient,
    deployer: SigningAccount,
) -> DelegationRegistryClient:
    client = delegation_registry_client_uninitialized

    client.send.config_delegation_registry(
        args=ConfigDelegationRegistryArgs(
            vote_fees=Fees(
                xgov=regcfg.FEE_VOTE_XGOV,
                other=regcfg.FEE_VOTE_OTHER,
            ),
            representative_fee=regcfg.FEE_REPRESENTATIVE,
            vote_trigger_award=regcfg.VOTE_TRIGGER_AWARD,
        )
    )

    # Load Representative SC
    representative_factory = algorand_client.client.get_typed_app_factory(
        typed_factory=RepresentativeFactory,
    )

    compiled_sc = representative_factory.app_factory.compile()

    delegation_registry_client_uninitialized.send.init_contract(
        args=InitContractArgs(
            contract=regcfg.CONTRACT_REPRESENTATIVE_BOX,
            size=len(compiled_sc.approval_program),
        ),
    )

    data_size_per_transaction = load_sc_data_size_per_transaction()
    bulks = 1 + len(compiled_sc.approval_program) // data_size_per_transaction
    for i in range(bulks):
        chunk = compiled_sc.approval_program[
            i * data_size_per_transaction : (i + 1) * data_size_per_transaction
        ]
        delegation_registry_client_uninitialized.send.load_contract(
            args=LoadContractArgs(
                contract=regcfg.CONTRACT_REPRESENTATIVE_BOX,
                offset=i * data_size_per_transaction,
                data=chunk,
            ),
        )

    # Load Voter SC
    voter_factory = algorand_client.client.get_typed_app_factory(
        typed_factory=VoterFactory,
    )

    compiled_sc = voter_factory.app_factory.compile()

    delegation_registry_client_uninitialized.send.init_contract(
        args=InitContractArgs(
            contract=regcfg.CONTRACT_VOTER_BOX,
            size=len(compiled_sc.approval_program),
        ),
    )

    data_size_per_transaction = load_sc_data_size_per_transaction()
    bulks = 1 + len(compiled_sc.approval_program) // data_size_per_transaction
    for i in range(bulks):
        chunk = compiled_sc.approval_program[
            i * data_size_per_transaction : (i + 1) * data_size_per_transaction
        ]
        delegation_registry_client_uninitialized.send.load_contract(
            args=LoadContractArgs(
                contract=regcfg.CONTRACT_VOTER_BOX,
                offset=i * data_size_per_transaction,
                data=chunk,
            ),
        )

    # Prepare first voter
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=deployer.address,
            receiver=client.app_address,
            amount=AlgoAmount(micro_algo=get_sc_voter_unassigned_mbr()),
        )
    )
    client.send.prepare_voter(
        args=PrepareVoterArgs(payment=pay_txn),
        params=CommonAppCallParams(
            extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
        ),
    )

    # Resume registry
    client.send.resume_registry()

    return client


@pytest.fixture(scope="function")
def delegation_registry_client_paused(
    algorand_client: AlgorandClient,
    delegation_registry_client: DelegationRegistryClient,
    deployer: SigningAccount,
) -> DelegationRegistryClient:
    client = delegation_registry_client

    client.send.pause_registry()

    return client


@pytest.fixture(scope="function")
def xgov(
    algorand_client: AlgorandClient,
    xgov_registry_mock_client: XgovRegistryMockClient,
) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account,
        min_spending_balance=INITIAL_FUNDS,
    )

    xgov_registry_mock_client.send.set_xgov_box(
        args=SetXgovBoxArgs(
            xgov_address=account.address,
            xgov_box=XGovBoxValue(
                voting_address=account.address,
                voted_proposals=0,
                last_vote_timestamp=0,
                subscription_round=0,
            ),
        ),
    )

    return account


@pytest.fixture(scope="function")
def xgov_delegated(
    algorand_client: AlgorandClient,
    voting_account: SigningAccount,
    xgov_registry_mock_client: XgovRegistryMockClient,
) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account,
        min_spending_balance=INITIAL_FUNDS,
    )

    xgov_registry_mock_client.send.set_xgov_box(
        args=SetXgovBoxArgs(
            xgov_address=account.address,
            xgov_box=XGovBoxValue(
                voting_address=voting_account.address,
                voted_proposals=0,
                last_vote_timestamp=0,
                subscription_round=0,
            ),
        ),
    )

    return account


@pytest.fixture(scope="function")
def voter(
    algorand_client: AlgorandClient,
    xgov_delegated: SigningAccount,
    representative: RepresentativeClient,
    delegation_registry_client: DelegationRegistryClient,
    xgov_registry_mock_client: XgovRegistryMockClient,
) -> VoterClient:
    representative_id = representative.app_id
    xgov_address = xgov_delegated.address
    sender = xgov_registry_mock_client.state.box.xgov_box.get_value(
        xgov_address
    ).voting_address

    available_voter = get_available_voter(
        algorand_client=algorand_client,
        delegation_registry_client=delegation_registry_client,
    )

    pay_amount = get_sc_voter_mbr()
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    result = delegation_registry_client.send.register_voter(
        args=RegisterVoterArgs(
            payment=pay_txn,
            xgov_address=xgov_address,
            available_voter_id=available_voter.id,
        ),
        params=CommonAppCallParams(
            sender=sender,
            extra_fee=AlgoAmount(micro_algo=4 * const.MIN_FEE),
        ),
    )

    client = algorand_client.client.get_typed_app_client_by_id(
        typed_client=VoterClient, app_id=result.abi_return
    )

    # Set voter representative and window
    client.send.set_representative(
        args=SetRepresentativeArgs(
            representative_id=representative_id,
        ),
        params=CommonAppCallParams(
            sender=xgov_address,
        ),
    )
    client.send.set_window(
        args=SetWindowArgs(
            window_ts=voter_cfg.DEFAULT_WINDOW_TS,
        ),
        params=CommonAppCallParams(
            sender=xgov_address,
        ),
    )

    # Get voter a vote to be triggered
    add_votes = 1
    sender = xgov_address
    pay_amount = (
        delegation_registry_client.state.global_state.vote_fees.xgov * add_votes
    )
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    delegation_registry_client.send.add_votes(
        args=AddVotesArgs(
            payment=pay_txn,
            xgov_address=xgov_address,
            add_votes=add_votes,
        ),
        params=CommonAppCallParams(
            sender=xgov_address,
            extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
        ),
    )

    # Give the created Voter the rights to vote in xGov program
    xgov_registry_mock_client.send.set_voting_account(
        args=SetVotingAccountArgs(
            xgov_address=xgov_address,
            voting_address=client.app_address,
        )
    )

    return client


@pytest.fixture(scope="function")
def representative(
    algorand_client: AlgorandClient,
    delegation_registry_client: DelegationRegistryClient,
) -> RepresentativeClient:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    representative_address = account.address

    pay_amount = (
        get_sc_representative_mbr()
        + delegation_registry_client.state.global_state.representative_fee
    )
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=representative_address,
            receiver=delegation_registry_client.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    result = delegation_registry_client.send.register_representative(
        args=RegisterRepresentativeArgs(
            payment=pay_txn,
        ),
        params=CommonAppCallParams(
            sender=representative_address,
            extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
        ),
    )

    client = algorand_client.client.get_typed_app_client_by_id(
        typed_client=RepresentativeClient, app_id=result.abi_return
    )

    return client


@pytest.fixture(scope="session")
def xgov_registry_fake_client(
    algorand_client: AlgorandClient,
    deployer: SigningAccount,
) -> XgovRegistryMockClient:
    config.configure(
        debug=False,
        populate_app_call_resources=True,
    )

    factory = algorand_client.client.get_typed_app_factory(
        typed_factory=XgovRegistryMockFactory,
        default_sender=deployer.address,
    )
    client, _ = factory.send.create.bare()  # type: ignore
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=client.app_address,
        min_spending_balance=AlgoAmount(micro_algo=int(INITIAL_FUNDS.micro_algo) * 100),
    )

    return client


@pytest.fixture(scope="session")
def proposal_fake_client(
    algorand_client: AlgorandClient,
    xgov_registry_fake_client: XgovRegistryMockClient,
    deployer: SigningAccount,
) -> ProposalMockClient:

    result = xgov_registry_fake_client.send.create_proposal(
        params=CommonAppCallParams(
            extra_fee=AlgoAmount(micro_algo=2 * const.MIN_FEE),
        ),
    )
    proposal_id = result.abi_return

    client = xgov_registry_fake_client.algorand.client.get_typed_app_client_by_id(
        typed_client=ProposalMockClient,
        app_id=proposal_id,
        default_sender=deployer.address,
    )

    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=client.app_address,
        min_spending_balance=INITIAL_FUNDS,
    )

    client.send.set_status(args=SetStatusArgs(status=DEFAULT_PROPOSAL_STATUS))
    client.send.set_voting_duration(
        args=SetVotingDurationArgs(voting_duration=DEFAULT_VOTING_DURATION)
    )
    client.send.set_vote_open_ts(
        args=SetVoteOpenTsArgs(vote_open_ts=DEFAULT_PROPOSAL_VOTE_OPEN_TS),
    )

    return client


@pytest.fixture(scope="function")
def proposal_voter(
    algorand_client: AlgorandClient,
    proposal_mock_client: ProposalMockClient,
    representative: RepresentativeClient,
    voter: VoterClient,
) -> ProposalMockClient:

    sender = representative.state.global_state.representative_address
    proposal_id = proposal_mock_client.app_id
    vote = Vote(approval=const.PPM, rejection=0)
    pay_amount = get_vote_mbr()
    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=sender,
            receiver=representative.app_address,
            amount=AlgoAmount(micro_algo=pay_amount),
        )
    )

    representative.send.publish_vote(
        args=PublishVoteArgs(
            payment=pay_txn,
            proposal_id=proposal_id,
            vote=vote,
        ),
        params=CommonAppCallParams(
            sender=sender,
        ),
    )

    xgov_address = voter.state.global_state.xgov_address
    proposal_mock_client.send.set_voter_box(
        args=SetVoterBoxArgs(
            voter_address=xgov_address,
            votes=1,
        )
    )

    # Enable voting right away
    voter.send.set_window(
        args=SetWindowArgs(window_ts=0),
        params=CommonAppCallParams(
            sender=voter.state.global_state.xgov_address,
        ),
    )

    return proposal_mock_client
