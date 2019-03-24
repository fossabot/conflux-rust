import os
import eth_utils
import rlp

from .config import default_config
from .transactions import Transaction
from .utils import privtoaddr, sha3_256

import sys
sys.path.append("..")

from test_framework.util import (
    assert_greater_than, 
    assert_greater_than_or_equal, 
    assert_is_hash_string, 
    wait_until, checktx
)

class RpcClient:
    def __init__(self, node=None):
        self.node = node

        # epoch definitions
        self.EPOCH_EARLIEST = "earliest"
        self.EPOCH_LATEST_MINED = "latest_mined"
        self.EPOCH_LATEST_STATE = "latest_state"

        # hash/address definitions
        self.GENESIS_ADDR = eth_utils.encode_hex(privtoaddr(default_config["GENESIS_PRI_KEY"]))
        self.COINBASE_ADDR = eth_utils.encode_hex(default_config["GENESIS_COINBASE"])
        self.GENESIS_ORIGIN_COIN = default_config["TOTAL_COIN"]
        self.ZERO_HASH = eth_utils.encode_hex(b'\x00' * 32)

        # default tx values
        self.DEFAULT_TX_GAS_PRICE = 1
        self.DEFAULT_TX_GAS = 21000
        self.DEFAULT_TX_FEE = self.DEFAULT_TX_GAS_PRICE * self.DEFAULT_TX_GAS
    
    def EPOCH_NUM(self, num: int) -> str:
        return hex(num)

    def rand_addr(self) -> str:
        (addr, _) = self.rand_account()
        return addr

    def rand_account(self) -> (str, bytes):
        priv_key = eth_utils.encode_hex(os.urandom(32))
        addr = eth_utils.encode_hex(privtoaddr(priv_key))
        return (addr, priv_key)

    def rand_hash(self, seed: bytes = None) -> str:
        if seed is None:
            seed = os.urandom(32)
        
        return eth_utils.encode_hex(sha3_256(seed))

    def generate_block(self, num_txs: int = 0) -> str:
        assert_greater_than_or_equal(num_txs, 0)
        block_hash = self.node.generateoneblock(num_txs)
        assert_is_hash_string(block_hash)
        return block_hash

    def generate_blocks(self, num_blocks: int, num_txs: int = 0) -> list:
        assert_greater_than(num_blocks, 0)
        assert_greater_than_or_equal(num_txs, 0)

        blocks = []
        for _ in range(0, num_blocks):
            block_hash = self.generate_block(num_txs)
            blocks.append(block_hash)

        return blocks

    def generate_blocks_to_state(self, num_blocks: int = 5, num_txs: int = 1) -> list:
        return self.generate_blocks(num_blocks, num_txs)
    
    def generate_block_with_parent(self, parent_hash: str, referee: list, num_txs: int = 0) -> str:
        assert_is_hash_string(parent_hash)

        for r in referee:
            assert_is_hash_string(r)

        assert_greater_than_or_equal(num_txs, 0)

        block_hash = self.node.generatefixedblock(parent_hash, referee, num_txs)
        assert_is_hash_string(block_hash)
        return block_hash

    def generate_custom_block(self, parent_hash: str, referee: list, txs: list) -> str:
        assert_is_hash_string(parent_hash)

        for r in referee:
            assert_is_hash_string(r)

        encoded_txs = eth_utils.encode_hex(rlp.encode(txs))

        block_hash = self.node.test_generatecustomblock(parent_hash, referee, encoded_txs)
        assert_is_hash_string(block_hash)
        return block_hash
    
    def gas_price(self) -> int:
        return int(self.node.cfx_gasPrice(), 0)

    def epoch_number(self, epoch: str = None) -> int:
        if epoch is None:
            return int(self.node.cfx_epochNumber(), 0)
        else:
            return int(self.node.cfx_epochNumber(epoch), 0)

    def get_balance(self, addr: str, epoch: str = None) -> int:
        if epoch is None:
            return int(self.node.cfx_getBalance(addr), 0)
        else:
            return int(self.node.cfx_getBalance(addr, epoch), 0)

    def get_nonce(self, addr: str, epoch: str = None) -> int:
        if epoch is None:
            return int(self.node.cfx_getTransactionCount(addr), 0)
        else:
            return int(self.node.cfx_getTransactionCount(addr, epoch), 0)

    def send_raw_tx(self, raw_tx: str) -> str:
        tx_hash = self.node.cfx_sendRawTransaction(raw_tx)
        assert_is_hash_string(tx_hash)
        return tx_hash

    def send_tx(self, tx: Transaction, wait_for_receipt=False) -> str:
        encoded = eth_utils.encode_hex(rlp.encode(tx))
        tx_hash = self.send_raw_tx(encoded)
        
        if wait_for_receipt:
            self.wait_for_receipt(tx_hash)
        
        return tx_hash

    def wait_for_receipt(self, tx_hash: str, num_txs=1, timeout=10, state_before_wait=True):
        if state_before_wait:
            self.generate_blocks_to_state(num_txs=num_txs)
        
        def check_tx():
            self.node.generateoneblock(num_txs)
            return checktx(self.node, tx_hash)
        wait_until(check_tx, timeout=timeout)

    def block_by_hash(self, block_hash: str, include_txs: bool = False) -> dict:
        return self.node.cfx_getBlockByHash(block_hash, include_txs)

    def block_by_epoch(self, epoch: str, include_txs: bool = False) -> dict:
        return self.node.cfx_getBlockByEpochNumber(epoch, include_txs)

    def best_block_hash(self) -> str:
        return self.node.cfx_getBestBlockHash()

    def get_tx(self, tx_hash: str) -> dict:
        return self.node.cfx_getTransactionByHash(tx_hash)

    def new_tx(self, sender = None, receiver = None, nonce = None, gas_price=1, gas=21000, value=100, data=b'', sign=True, priv_key=None):
        if sender is None:
            sender = self.GENESIS_ADDR
            if priv_key is None:
                priv_key = default_config["GENESIS_PRI_KEY"]

        if receiver is None:
            receiver = self.COINBASE_ADDR
        
        if nonce is None:
            nonce = self.get_nonce(sender)

        action = eth_utils.decode_hex(receiver)
        tx = Transaction(nonce, gas_price, gas, action, value, data)
        
        if sign:
            return tx.sign(priv_key)
        else:
            return tx

    def block_hashes_by_epoch(self, epoch: str) -> list:
        blocks = self.node.cfx_getBlocksByEpoch(epoch)
        for b in blocks:
            assert_is_hash_string(b)
        return blocks

    def get_peers(self) -> list:
        return self.node.getpeerinfo()

    def chain(self) -> list:
        return self.node.cfx_getChain()

    def get_receipt(self, tx_hash: str) -> dict:
        return self.node.gettransactionreceipt(tx_hash)

    def txpool_status(self) -> (int, int):
        status = self.node.txpool_status()
        return (status["pending"], status["ready"])