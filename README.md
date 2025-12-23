# xGov Delegation

This project facilitates delegation in [Algorand xGov program](https://xgov.algorand.co/) by creating a registry of representatives to whom xGovs can delegate their voting power.
The delegation process is permissionless and fully on-chain, integrated with the [xGov smart contracts](https://github.com/algorandfoundation/xgov-beta-sc).

Any entity may register as a Representative by paying a corresponding registration fee.
The Representative may publish its vote for each xGov Proposal.
The xGovs that choose to be represented by the Representative automatically vote on each Proposal according to the published vote.

An xGov that wants to delegate its voting power to the Representative must first create a Voter smart contract, which is used to process the delegation.
The xGov must then set the xGov voting address to the created contract.
The xGov must also prepay for processing the automatic voting on proposals.

There can be only one Voter per xGov.
The Voter is tied to the xGov address.
The Voter may be managed by the xGov address or a defined manager address.
The Voter may be created by the xGov or its voting address.
The Voter may change its Representative at any time.
The Voter may define a delay before automatically voting according to the Representative.
This way, the xGov has the time to vote on its own and only if it does not vote by the specified time, will it automatically vote according to the Representative.
Only the xGov, its voting or voter manager address may prepay for the votes of a Voter.
There may be a discount if the payment comes from the xGov.
If the xGov deregisters from the xGov program, its Voter contract is also deleted.

The Representative may pause or deregister its representation at any time.
This blocks the representation.
It is up to the xGov delegators to switch to another Representative in such a case if desired.
The Representative may not switch its vote for a Proposal that is in voting stage.
Representative's vote is expressed in PPM.
The Representative may explicitly boycott a proposal by casting a vote whose sum exceeds PPM_MAX.

Anyone may trigger the casting of a delegated vote.
The account that triggered the vote is rewarded for the action.

Mainnet deployment: 3378436620

Copyright (C) 2025 Valar Solutions GmbH
