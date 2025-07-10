import random
import json
import time
from web3 import Web3
from eth_account import Account
from colorama import init, Fore, Style

init(autoreset=True)

RPC_URL = "https://rpc.kasplextest.xyz/"
PRIVATE_KEY_FILE = "private_keys.txt"
ROUTER_ADDRESS = "0xaE821200c01E532E5A252FfCaA8546cbdca342DF"

TOKENS = {
    "WKAS": "0xf40178040278E16c8813dB20a84119A605812FB3",
    "TZEAL": "0xD6411bc52c8CbD192477233F2DB211cB96bc3504",
    "XZEAL": "0xfEc49b2F52B01d36C40D164A09831Ce69E596b2B",
    "TNACHO": "0xfa458995688c73fc48E7D833483a7206Bed75C27",
    "XNACHO": "0xa2B36605ca53B003a1f1DEb84Fa2D66382ecdba8",
    "TKANGO": "0x46B4B1A6c462609957D17D5d8eEA12037E44ef3F",
    "TKASPER": "0x521023CA380929046365FcE28f6096263E7f8B8f",
    "TKASPY": "0x58CE5acc313B3fDC38adf3Ad670122556A44B009",
    "TBURT": "0x0b1793776E43D71Cc892E58849A0D2465FF36f10",
    "TKROAK": "0x34FaB1A1c8c64c6Fe9C860fe11601a3348aa5ab8",
    "TGHOAD": "0xd97D0AEc9CB23C3Ed3bBae393e85b542Db3226BF",
    "TKREX": "0x3Cfaf44e511f08D2Ad1049a79E6d5701272D707F",
    "TDOGK": "0xe8aCEFB936BEb37Bc3cdAB83E54b4941AFC2c85a"
}

TOKEN_ORDER = [
    "TZEAL", "XZEAL", "TNACHO", "XNACHO", "TKANGO", "TKASPER",
    "TKASPY", "TBURT", "TKROAK", "TGHOAD", "TKREX", "TDOGK"
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))

with open("uniswap_router_abi.json", "r") as f:
    ROUTER_ABI = json.load(f)

ERC20_ABI = json.loads('[{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}]')

WKAS_ABI = json.loads('[{"constant":false,"inputs":[],"name":"deposit","outputs":[],"payable":true,"stateMutability":"payable","type":"function"},{"constant":false,"inputs":[{"name":"wad","type":"uint256"}],"name":"withdraw","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"}]')

def load_wallets(path):
    wallets = []
    with open(path, "r") as f:
        for line in f:
            key = line.strip()
            if not key:
                continue
            if not key.startswith("0x"):
                key = "0x" + key
            try:
                acct = Account.from_key(key)
                wallets.append({"private_key": key, "address": acct.address})
            except Exception as e:
                print(f"{Fore.RED}❌ Invalid key: {key[:10]}... → {e}")
    return wallets

def get_balance(wallet, token_address):
    data = '0x70a08231' + wallet["address"][2:].zfill(64)
    result = w3.eth.call({'to': token_address, 'data': data})
    return int(result.hex(), 16)

def send_tx(wallet, tx):
    for attempt in range(3):
        try:
            gas_price = int(w3.eth.gas_price * 0.95)
            tx['gasPrice'] = gas_price
            tx['nonce'] = w3.eth.get_transaction_count(wallet['address'])
            signed = w3.eth.account.sign_transaction(tx, wallet['private_key'])
            print(f"  🔏 Signing TX...")
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  🚀 Sending TX...")
            w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"  ✅ TX Success: {tx_hash.hex()}")
            return True
        except Exception as e:
            print(f"  ❌ Attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return False

def wrap_kas(wallet, amount_eth):
    print(f"{Fore.YELLOW}💰 Wrap     : {w3.from_wei(amount_eth, 'ether')} KAS → WKAS")
    wkas = w3.eth.contract(address=Web3.to_checksum_address(TOKENS["WKAS"]), abi=WKAS_ABI)
    tx = wkas.functions.deposit().build_transaction({
        'from': wallet["address"],
        'value': amount_eth,
        'gas': 46000
    })
    send_tx(wallet, tx)
def wrap_kas(wallet, amount_eth):
    wkas = w3.eth.contract(address=Web3.to_checksum_address(TOKENS["WKAS"]), abi=WKAS_ABI)
    tx = wkas.functions.deposit().build_transaction({
        'from': wallet["address"],
        'value': amount_eth,
        'nonce': w3.eth.get_transaction_count(wallet["address"]),
        'gas': 100000,
        'gasPrice': w3.eth.gas_price
    })
    signed = w3.eth.account.sign_transaction(tx, wallet["private_key"])
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"{Fore.YELLOW}💰 Wrap     : {w3.from_wei(amount_eth, 'ether')} KAS → WKAS")

def unwrap_wkas(wallet, amount):
    wkas = w3.eth.contract(address=Web3.to_checksum_address(TOKENS["WKAS"]), abi=WKAS_ABI)
    tx = wkas.functions.withdraw(amount).build_transaction({
        'from': wallet["address"],
        'nonce': w3.eth.get_transaction_count(wallet["address"]),
        'gas': 100000,
        'gasPrice': w3.eth.gas_price
    })
    signed = w3.eth.account.sign_transaction(tx, wallet["private_key"])
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"{Fore.CYAN}↩️ Unwrap   : {w3.from_wei(amount, 'ether')} WKAS → KAS")
    return tx_hash.hex()   

def run_swap_cycle(wallet):
    print(f"{Fore.MAGENTA}📍 Wallet   : {wallet['address']}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    amount = w3.to_wei(random.randint(1, 5), "ether")
    wrap_kas(wallet, amount)
    current = TOKENS["WKAS"]
    for symbol in TOKEN_ORDER:
        next_token = TOKENS[symbol]
        balance = get_balance(wallet, current)
        if balance == 0:
            break
        swap(wallet, current, next_token, balance)
        current = next_token
    final_token = TOKENS["TDOGK"]
    final_balance = get_balance(wallet, final_token)
    if final_balance > 0:
        swap(wallet, final_token, TOKENS["WKAS"], final_balance)
    wrap_balance = get_balance(wallet, TOKENS["WKAS"])
    if wrap_balance > 0:
        unwrap_wkas(wallet, wrap_balance)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

if __name__ == "__main__":
    wallets = load_wallets(PRIVATE_KEY_FILE)
    for wallet in wallets:
        try:
            run_swap_cycle(wallet)
            delay = random.randint(60, 120)
            print(f"⏳ Delay {delay}s sebelum lanjut wallet berikutnya\n")
            time.sleep(delay)
        except Exception as e:
            print(f"{Fore.RED}❌ Error pada {wallet['address']}: {e}\n")
