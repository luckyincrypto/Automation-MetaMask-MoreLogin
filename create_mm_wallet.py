# Сторонние библиотеки
from hdwallet import HDWallet
from hdwallet.mnemonics import (
    BIP39Mnemonic,
    BIP39_MNEMONIC_LANGUAGES,
    BIP39_MNEMONIC_WORDS,
)
from hdwallet.cryptocurrencies import Ethereum as Cryptocurrency
from hdwallet.hds import BIP44HD
from hdwallet.derivations import BIP44Derivation, CHANGES

# Локальные модули
from config import logger


def create_wallet():
    hdwallet: HDWallet = (
        HDWallet(
            cryptocurrency=Cryptocurrency,
            hd=BIP44HD,
            network=Cryptocurrency.NETWORKS.MAINNET,
            passphrase=None,  # "talonlab"
        )
        .from_mnemonic(  # Get Ethereum HDWallet from mnemonic phrase
            mnemonic=BIP39Mnemonic(
                mnemonic=BIP39Mnemonic.from_words(
                    words=BIP39_MNEMONIC_WORDS.TWELVE,
                    language=BIP39_MNEMONIC_LANGUAGES.ENGLISH,
                )
            )
        )
        .from_derivation(  # Drive from BIP44 derivation
            derivation=BIP44Derivation(
                coin_type=Cryptocurrency.COIN_TYPE,
                account=0,
                change=CHANGES.EXTERNAL_CHAIN,
                address=("0"),  # or "0-10"
            )
        )
    )
    mnemonic = hdwallet.mnemonic()
    address = hdwallet.dumps(exclude={"root", "indexes"})[0]["address"]
    private_key = "0x" + hdwallet.dumps(exclude={"root", "indexes"})[0]["private_key"]
    logger.update(f" (create_wallet), Created wallet: {address}")
    return mnemonic, address, private_key
