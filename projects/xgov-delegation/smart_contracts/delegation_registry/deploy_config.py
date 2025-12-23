import logging
import os
import random

from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AppClientCompilationParams,
    CommonAppCallCreateParams,
    CommonAppCallParams,
    OnSchemaBreak,
    OnUpdate,
    PaymentParams,
)

from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
    PrepareVoterArgs,
)
from smart_contracts.common.constants import MIN_FEE
from smart_contracts.common.helpers import (
    get_sc_voter_unassigned_mbr,
    load_sc_data_size_per_transaction,
)

logger = logging.getLogger(__name__)

deployer_min_spending = AlgoAmount.from_algo(3)
registry_min_spending = AlgoAmount.from_algo(10)  # min balance for proposal box storage


def _deploy_delegation_registry(algorand_client: AlgorandClient) -> None:
    from smart_contracts.artifacts.delegation_registry.delegation_registry_client import (
        ConfigDelegationRegistryArgs,
        CreateArgs,
        DelegationRegistryFactory,
        DelegationRegistryFactoryCreateParams,
        DelegationRegistryMethodCallCreateParams,
        DelegationRegistryMethodCallUpdateParams,
        Fees,
        InitContractArgs,
        LoadContractArgs,
    )
    from smart_contracts.artifacts.representative.representative_client import (
        RepresentativeFactory,
    )
    from smart_contracts.artifacts.voter.voter_client import VoterFactory
    from smart_contracts.delegation_registry import config as regcfg

    deployer = algorand_client.account.from_environment("DEPLOYER")

    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=deployer.address, min_spending_balance=deployer_min_spending
    )

    template_values = {"entropy": b""}

    fresh_deploy = os.environ.get("DEL_REG_FRESH_DEPLOY", "false").lower() == "true"
    if fresh_deploy:
        logger.info("Fresh deployment requested")
        template_values = {
            "entropy": random.randbytes(16),  # trick to ensure a fresh deployment
        }

    version = os.environ.get("DEL_REGISTRY_VERSION", None)
    xgov_registry_id = int(os.environ.get("DEL_XGOV_REGISTRY_ID", 0))

    factory = algorand_client.client.get_typed_app_factory(
        typed_factory=DelegationRegistryFactory,
        default_sender=deployer.address,
        default_signer=deployer.signer,
        compilation_params=AppClientCompilationParams(
            deploy_time_params=template_values
        ),
        version=version,
    )

    create_args = CreateArgs(xgov_registry_id=xgov_registry_id)
    create_params = DelegationRegistryFactoryCreateParams(factory.app_factory).create(
        args=create_args,
        params=CommonAppCallCreateParams(
            extra_program_pages=3,
        ),
        compilation_params=AppClientCompilationParams(
            deploy_time_params=template_values,
        ),
    )

    update_params = DelegationRegistryFactoryCreateParams(
        factory.app_factory
    ).update_registry(
        compilation_params=AppClientCompilationParams(
            deploy_time_params=template_values,
        ),
    )

    existing_deployments = (
        algorand_client.app_deployer.get_creator_apps_by_name(
            creator_address=deployer.address,
        )
        if deployer
        else None
    )

    app_client, _ = factory.deploy(
        on_schema_break=OnSchemaBreak.AppendApp,
        on_update=(OnUpdate.UpdateApp if not fresh_deploy else OnUpdate.AppendApp),
        create_params=DelegationRegistryMethodCallCreateParams(
            extra_program_pages=create_params.extra_program_pages,
            method=create_params.method.name,
            args=create_args,
        ),
        update_params=DelegationRegistryMethodCallUpdateParams(
            method=update_params.method.name,
            sender=deployer.address,
            signer=deployer.signer,
        ),
        existing_deployments=existing_deployments,
    )

    logger.info("Funding delegation registry")

    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=app_client.app_address,
        min_spending_balance=registry_min_spending,
    )

    logger.info("Uploading representative approval program to box")

    representative_factory = algorand_client.client.get_typed_app_factory(
        typed_factory=RepresentativeFactory,
    )

    compiled_sc = representative_factory.app_factory.compile()
    app_client.send.init_contract(
        args=InitContractArgs(
            contract=regcfg.CONTRACT_REPRESENTATIVE_BOX,
            size=len(compiled_sc.approval_program),
        ),
        params=CommonAppCallParams(
            sender=deployer.address,
            signer=deployer.signer,
        ),
    )

    data_size_per_transaction = load_sc_data_size_per_transaction()
    bulks = 1 + len(compiled_sc.approval_program) // data_size_per_transaction
    for i in range(bulks):
        chunk = compiled_sc.approval_program[
            i * data_size_per_transaction : (i + 1) * data_size_per_transaction
        ]
        app_client.send.load_contract(
            args=LoadContractArgs(
                contract=regcfg.CONTRACT_REPRESENTATIVE_BOX,
                offset=i * data_size_per_transaction,
                data=chunk,
            ),
            params=CommonAppCallParams(
                sender=deployer.address,
                signer=deployer.signer,
            ),
        )

    logger.info("Uploading voter approval program to box")

    voter_factory = algorand_client.client.get_typed_app_factory(
        typed_factory=VoterFactory,
    )

    compiled_sc = voter_factory.app_factory.compile()

    app_client.send.init_contract(
        args=InitContractArgs(
            contract=regcfg.CONTRACT_VOTER_BOX,
            size=len(compiled_sc.approval_program),
        ),
        params=CommonAppCallParams(
            sender=deployer.address,
            signer=deployer.signer,
        ),
    )

    data_size_per_transaction = load_sc_data_size_per_transaction()
    bulks = 1 + len(compiled_sc.approval_program) // data_size_per_transaction
    for i in range(bulks):
        chunk = compiled_sc.approval_program[
            i * data_size_per_transaction : (i + 1) * data_size_per_transaction
        ]
        app_client.send.load_contract(
            args=LoadContractArgs(
                contract=regcfg.CONTRACT_VOTER_BOX,
                offset=i * data_size_per_transaction,
                data=chunk,
            ),
            params=CommonAppCallParams(
                sender=deployer.address,
                signer=deployer.signer,
            ),
        )

    logger.info("Resuming registry")

    pay_txn = algorand_client.create_transaction.payment(
        PaymentParams(
            sender=deployer.address,
            receiver=app_client.app_address,
            amount=AlgoAmount(micro_algo=get_sc_voter_unassigned_mbr()),
        )
    )
    app_client.send.prepare_voter(
        args=PrepareVoterArgs(payment=pay_txn),
        params=CommonAppCallParams(
            extra_fee=AlgoAmount(micro_algo=2 * MIN_FEE),
        ),
    )
    app_client.send.resume_registry()

    should_configure = os.environ.get("DEL_REG_CONFIGURE", "false").lower() == "true"
    if should_configure:
        logger.info("Configuring delegation registry")

        vote_fees_xgov = int(os.environ["DEL_CFG_FEE_VOTE_XGOV"])
        vote_fees_other = int(os.environ["DEL_CFG_FEE_VOTE_OTHER"])
        representative_fee = int(os.environ["DEL_CFG_FEE_REPRESENTATIVE"])
        vote_trigger_award = int(os.environ["DEL_CFG_VOTE_TRIGGER_AWARD"])

        app_client.send.config_delegation_registry(
            args=ConfigDelegationRegistryArgs(
                vote_fees=Fees(
                    xgov=vote_fees_xgov,
                    other=vote_fees_other,
                ),
                representative_fee=representative_fee,
                vote_trigger_award=vote_trigger_award,
            ),
            params=CommonAppCallParams(
                sender=deployer.address,
                signer=deployer.signer,
            ),
        )

    else:
        logger.info("Skipping delegation registry configuration as requested")


def deploy() -> None:
    algorand_client = AlgorandClient.from_environment()
    algorand_client.set_default_validity_window(100)

    _deploy_delegation_registry(algorand_client)
