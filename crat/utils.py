from dataclasses import dataclass, field
from typing import List, Optional
from web3 import Web3, HTTPProvider, contract
from web3.types import ChecksumAddress
from web3.middleware import geth_poa_middleware


@dataclass
class Token:
    address: str
    symbol: str
    decimals: int


@dataclass
class Config:
    django_secret_key: str
    django_static_url: str
    django_allowed_hosts: List[str]
    crowdsale_contract_address: str
    crowdsale_contract_abi: str
    token_decimals: int
    private_key: str
    cryptocompare_api_url: str
    node: str
    signature_expiration_timeout_minutes: int
    rates_update_timeout_minutes: int
    tokens: List[Token]
    prices: List[float]
    debug: Optional[bool] = False
    crowdsale_contract: contract = field(init=False, default=None)
    w3: Web3 = field(init=False, default=None)

    def __post_init__(self):
        self.w3 = Web3(HTTPProvider(self.node))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        crowdsale_address_checksum = Web3.toChecksumAddress(self.crowdsale_contract_address)
        self.crowdsale_contract = self.w3.eth.contract(
            address=crowdsale_address_checksum,
            abi=self.crowdsale_contract_abi,
        )

    def get_token_by_address(self, address: ChecksumAddress):
        try:
            return [token for token in self.tokens if token.address == address][0]
        except IndexError:
            raise ValueError(f'Cannot find token with address {address}')
