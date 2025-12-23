import typing as t

from algopy import arc4

Error = arc4.String


class Vote(arc4.Struct):
    approval: arc4.UInt64  # in PPM
    rejection: arc4.UInt64  # in PPM


class VoteRaw(arc4.Struct):
    approvals: arc4.UInt64  # count of votes
    rejections: arc4.UInt64  # count of votes


class Fees(arc4.Struct):
    xgov: arc4.UInt64
    other: arc4.UInt64


class XGovBoxValue(arc4.Struct):
    voting_address: arc4.Address
    voted_proposals: arc4.UInt64
    last_vote_timestamp: arc4.UInt64
    subscription_round: arc4.UInt64


ContractName: t.TypeAlias = arc4.StaticArray[arc4.Byte, t.Literal[6]]
"""
ContractName : arc4.StaticArray[arc4.Byte, t.Literal[3]]
    Name of smart contract.
"""

SelPk: t.TypeAlias = arc4.StaticArray[arc4.Byte, t.Literal[32]]
"""
SelPk : arc4.StaticArray[arc4.Byte, t.Literal[32]]
    Selection public key of a participation key.
"""

VotePk: t.TypeAlias = arc4.StaticArray[arc4.Byte, t.Literal[32]]
"""
VotePk : arc4.StaticArray[arc4.Byte, t.Literal[32]]
    Vote public key of a participation key.
"""

StateProofPk: t.TypeAlias = arc4.StaticArray[arc4.Byte, t.Literal[64]]
"""
StateProofPk : arc4.StaticArray[arc4.Byte, t.Literal[64]]
    State proof public key of a participation key.
"""


class KeyRegTxnInfo(arc4.Struct):
    """
    All relevant parameters of a key registration transaction.

    Fields
    ------
    vote_first : arc4.UInt64
        First round of validity of a participation key.
    vote_last : arc4.UInt64
        Last round of validity of a participation key.
    vote_key_dilution : arc4.UInt64
        Vote key dilution parameter of a participation key.
    vote_pk : VotePk
        Vote public key of a participation key.
    selection_pk : SelPk
        Selection public key of a participation key.
    state_proof_pk : StateProofPk
        State proof public key of a participation key.
    """

    vote_first: arc4.UInt64
    vote_last: arc4.UInt64
    vote_key_dilution: arc4.UInt64
    vote_pk: VotePk
    selection_pk: SelPk
    state_proof_pk: StateProofPk
