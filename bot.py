import json
import time
import re
import random
import signal
import sys
from web3 import Web3, HTTPProvider
from web3.exceptions import ContractLogicError, ABIFunctionNotFound
from requests.exceptions import ConnectionError as RequestsConnectionError
from http.client import RemoteDisconnected
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

# ====================================================================================
# KONFIGURASI
# ====================================================================================
RPC_URL = 'https://rpc.kasplextest.xyz/'
PRIVATE_KEY_FILE = 'private_key.txt'
ROUTER_ADDRESS = '0xaE821200c01E532E5A252FfCaA8546cbdca342DF'

TOKENS = {
    "WKAS": "0xf40178040278E16c8813dB20a84119A605812FB3",
    "TZEAL": "0xD6411bc52c8CbD192477233F2DB211cB96bc3504",
    "XZEAL": "0xfEc49b2F52B01d36C40D164A09831Ce69E596b2B",
    "TNACHO": "0xfa458995688c73fc48E7D833483a7206Bed75C27",
    "XNACHO": "0xa2B36605ca53B003a1f1DEb84Fa2D66382ecdba8",
    "TKANGO": "0x46B4B1A6c462609957D17D5d8eEA12037E44ef3F",
    "TKASPER": "0x521023CA380929046365FcE28f6096263E7f8B8f",
    "TKASPY": "0x58CE5acc313B3fDC38adf3Ad670122556A44B009"
}

ABI_ERC20 = json.loads('[{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}, {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}, {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256"}],"type":"function"}]')
ABI_ROUTER = json.loads('[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"}]')
ABI_WKAS = json.loads('[{"name":"deposit","outputs":[],"inputs":[],"stateMutability":"payable","type":"function","payable":true}, {"name":"withdraw","inputs":[{"name":"wad","type":"uint256"}],"outputs":[],"stateMutability":"nonpayable","type":"function"}]')

def load_private_key(console):
    try:
        with open(PRIVATE_KEY_FILE, 'r') as f:
            private_keys = [line.strip() for line in f if line.strip()]
        if not private_keys:
            console.print(f"[bold red]❌ FATAL ERROR: File '{PRIVATE_KEY_FILE}' kosong atau hanya berisi spasi/baris kosong.[/bold red]")
            console.print("[yellow]Please ensure 'private_key.txt' contains one valid 64-character hexadecimal private key per line (with or without '0x' prefix).[/yellow]")
            return []
        
        valid_keys = []
        for idx, private_key in enumerate(private_keys, 1):
            private_key = private_key.replace('0x', '').strip()
            if not re.match(r'^[0-9a-fA-F]{64}$', private_key):
                if len(private_key) != 64:
                    console.print(f"[bold red]❌ Private key {idx} invalid: Length {len(private_key)} characters, expected 64.[/bold red]")
                else:
                    console.print(f"[bold red]❌ Private key {idx} invalid: Contains non-hexadecimal characters: {private_key[:10]}...{private_key[-10:]}[/bold red]")
                console.print("[yellow]Skipping invalid key. Ensure each key is a 64-character hexadecimal string (with or without '0x').[/yellow]")
                continue
            valid_keys.append('0x' + private_key)
        
        if not valid_keys:
            console.print(f"[bold red]❌ FATAL ERROR: No valid private keys found in '{PRIVATE_KEY_FILE}'.[/bold red]")
            return []
        
        console.print(f"[green]✅ Loaded {len(valid_keys)} valid private key(s) from '{PRIVATE_KEY_FILE}'.[/green]")
        return valid_keys
    except FileNotFoundError:
        console.print(f"[bold red]❌ FATAL ERROR: File '{PRIVATE_KEY_FILE}' tidak ditemukan.[/bold red]")
        console.print("[yellow]Please create a file named 'private_key.txt' with one valid private key per line.[/yellow]")
        return []
    except Exception as e:
        console.print(f"[bold red]❌ FATAL ERROR: Error reading private key file: {e}[/bold red]")
        return []

def wait_for_pending_tx(console, w3, account, max_wait=300):
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            pending_nonce = w3.eth.get_transaction_count(account.address, 'pending')
            latest_nonce = w3.eth.get_transaction_count(account.address, 'latest')
            if pending_nonce == latest_nonce:
                console.print("[cyan]✅ Mempool clear, no pending transactions.[/cyan]")
                return latest_nonce
            console.print("[yellow]⏳ Pending transactions detected, waiting...[/yellow]")
            time.sleep(5)
        except (RequestsConnectionError, RemoteDisconnected) as e:
            console.print(f"[bold red]❌ Connection error while checking nonce: {e}[/bold red]")
            raise
    console.print("[bold red]❌ Timeout waiting for mempool to clear.[/bold red]")
    return None

def retry_transaction(console, w3, account, transaction, tx_type, max_retries=5, delay=10):
    attempt = 1
    while attempt <= max_retries:
        try:
            console.print(f"[cyan]Estimating gas for {tx_type}...[/cyan]")
            gas_estimate = w3.eth.estimate_gas(transaction)
            transaction['gas'] = int(gas_estimate * 1.3)
            console.print(f"  [cyan]-> Attempt {attempt}/{max_retries} - Estimated gas for {tx_type}: {gas_estimate}, using {transaction['gas']} with 30% buffer[/cyan]")
            signed_tx = w3.eth.account.sign_transaction(transaction, account.key)
            console.print(f"[cyan]Sending transaction for {tx_type}...[/cyan]")
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            console.print(f"  [cyan]-> Attempt {attempt}/{max_retries} - Transaksi dikirim. Hash: [bold blue]{tx_hash.hex()}[/bold blue][/cyan]")
            with console.status(f"[bold yellow]Menunggu konfirmasi '{tx_type}' (Attempt {attempt})...", spinner="dots12"):
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                if receipt['status'] == 0:
                    console.print(f"[bold red]❌ Attempt {attempt}/{max_retries} - {tx_type} gagal. Receipt: {receipt}[/bold red]")
                    if attempt == max_retries:
                        return False, receipt
                    console.print(f"[yellow]⏳ Retrying after {delay} seconds...[/yellow]")
                    time.sleep(delay)
                    attempt += 1
                    continue
            console.print(f"  [cyan]-> Gas used for {tx_type}: {receipt['gasUsed']}[/cyan]")
            return True, receipt
        except ContractLogicError as e:
            console.print(f"[bold red]❌ Attempt {attempt}/{max_retries} - {tx_type} revert: {e}[/bold red]")
            if attempt == max_retries:
                console.print(f"[yellow]Possible causes for {tx_type} failure: Insufficient balance, invalid contract, or insufficient liquidity.[/yellow]")
                return False, str(e)
            console.print(f"[yellow]⏳ Retrying after {delay} seconds...[/yellow]")
            time.sleep(delay)
            attempt += 1
        except ABIFunctionNotFound as e:
            console.print(f"[bold red]❌ Attempt {attempt}/{max_retries} - ABI error for {tx_type}: {e}[/bold red]")
            console.print(f"[yellow]Possible cause: The contract ABI is missing the required function (e.g., balanceOf, approve, or withdraw).[/yellow]")
            return False, str(e)
        except (RequestsConnectionError, RemoteDisconnected) as e:
            console.print(f"[bold red]❌ Attempt {attempt}/{max_retries} - Connection error for {tx_type}: {e}[/bold red]")
            console.print(f"[yellow]Possible cause: RPC node {RPC_URL} is down or unstable.[/yellow]")
            if attempt == max_retries:
                return False, str(e)
            console.print(f"[yellow]⏳ Retrying after {delay} seconds...[/yellow]")
            time.sleep(delay)
            attempt += 1
        except Exception as e:
            console.print(f"[bold red]❌ Attempt {attempt}/{max_retries} - Error saat {tx_type}: {e}[/bold red]")
            if attempt == max_retries:
                console.print(f"[yellow]Possible causes for {tx_type} failure: Network issues, gas estimation errors, or invalid transaction parameters.[/yellow]")
                return False, str(e)
            console.print(f"[yellow]⏳ Retrying after {delay} seconds...[/yellow]")
            time.sleep(delay)
            attempt += 1
    return False, None

def wrap_kas(console, w3, account, amount_in_kas, idx, total_wallets):
    console.print(Panel(f"📦 [bold]LANGKAH 1 dari 8[/bold]: WRAP {amount_in_kas} KAS -> WKAS", style="cyan"))
    wkas_contract = w3.eth.contract(address=Web3.to_checksum_address(TOKENS["WKAS"]), abi=ABI_WKAS)
    console.print(f"  [cyan]-> Using WKAS contract: {TOKENS['WKAS']} for deposit[/cyan]")
    amount_in_wei = w3.to_wei(amount_in_kas, 'ether')
    
    kas_balance = w3.eth.get_balance(account.address)
    console.print(f"  [cyan]-> Saldo KAS: {w3.from_wei(kas_balance, 'ether')} KAS[/cyan]")
    if kas_balance < amount_in_wei:
        console.print(f"[bold red]❌ Saldo KAS tidak cukup: {w3.from_wei(kas_balance, 'ether')} < {amount_in_kas}[/bold red]")
        return False, "Insufficient KAS balance"
    
    console.print("[cyan]Fetching nonce...[/cyan]")
    nonce = wait_for_pending_tx(console, w3, account)
    if nonce is None:
        return False, "Timeout waiting for mempool"
    
    tx_params = {
        'from': account.address,
        'nonce': nonce,
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id,
        'value': amount_in_wei
    }
    console.print("[cyan]Building transaction...[/cyan]")
    transaction = wkas_contract.functions.deposit().build_transaction(tx_params)
    console.print("[cyan]Sending transaction...[/cyan]")
    success, result = retry_transaction(console, w3, account, transaction, "wrap KAS")
    if success:
        console.print("  [bold green]✅ BERHASIL[/bold green]\n")
        console.print(f"[green]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Wrap KAS - Success[/green]")
        return True, None
    console.print(f"[bold red]❌ Wrap KAS gagal setelah 5 attempts. Error: {result}[/bold red]")
    console.print(f"[red]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Wrap KAS - Failed: {result}[/red]")
    return False, str(result)

def swap_token(console, w3, account, from_token_key, to_token_key, amount_in_wei, step, idx, total_wallets):
    console.print(Panel(f"🔁 [bold]LANGKAH {step} dari 8[/bold]: SWAP {from_token_key} -> {to_token_key}", style="cyan"))
    if amount_in_wei == 0:
        console.print("  [yellow]⚠️  Saldo 0, melewati swap.[/yellow]")
        console.print(f"[green]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Swap {from_token_key} -> {to_token_key} - Success[/green]")
        return True, None
    from_token_addr = Web3.to_checksum_address(TOKENS[from_token_key])
    to_token_addr = Web3.to_checksum_address(TOKENS[to_token_key])
    router_addr = Web3.to_checksum_address(ROUTER_ADDRESS)
    my_address = account.address
    from_token_contract = w3.eth.contract(address=from_token_addr, abi=ABI_ERC20)
    router_contract = w3.eth.contract(address=router_addr, abi=ABI_ROUTER)
    console.print(f"  [cyan]-> Using router: {ROUTER_ADDRESS} for swap {from_token_key} -> {to_token_key}[/cyan]")
    
    try:
        balance = from_token_contract.functions.balanceOf(my_address).call()
        balance_text = Text.assemble(("  -> Saldo ", "white"), (f"{w3.from_wei(balance, 'ether')}", "bold magenta"), (f" {from_token_key} yang akan di-swap", "white"))
        console.print(balance_text)
        if balance < amount_in_wei:
            console.print(f"[bold red]❌ Saldo {from_token_key} tidak cukup: {w3.from_wei(balance, 'ether')} < {w3.from_wei(amount_in_wei, 'ether')}[/bold red]")
            console.print(f"[red]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Swap {from_token_key} -> {to_token_key} - Failed: Insufficient {from_token_key} balance[/red]")
            return False, f"Insufficient {from_token_key} balance"
    except ABIFunctionNotFound as e:
        console.print(f"[bold red]❌ Error: Function 'balanceOf' not found in {from_token_key} contract ABI at {from_token_addr}.[/bold red]")
        console.print("[yellow]Possible cause: The contract is not ERC20-compliant or the address is incorrect.[/yellow]")
        console.print(f"[red]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Swap {from_token_key} -> {to_token_key} - Failed: {e}[/red]")
        return False, str(e)
    
    nonce = wait_for_pending_tx(console, w3, account)
    if nonce is None:
        console.print(f"[red]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Swap {from_token_key} -> {to_token_key} - Failed: Timeout waiting for mempool[/red]")
        return False, "Timeout waiting for mempool"
    
    try:
        allowance = from_token_contract.functions.allowance(my_address, router_addr).call()
        console.print(f"  [cyan]-> Current allowance for {from_token_key}: {w3.from_wei(allowance, 'ether')} {from_token_key}[/cyan]")
        if allowance < amount_in_wei:
            console.print("  [magenta]-> Menyetujui (Approve) token...[/magenta]")
            approve_txn = from_token_contract.functions.approve(router_addr, amount_in_wei).build_transaction({
                'from': my_address,
                'nonce': nonce,
                'gasPrice': w3.eth.gas_price,
                'chainId': w3.eth.chain_id
            })
            success, result = retry_transaction(console, w3, account, approve_txn, "approve token")
            if not success:
                console.print(f"[bold red]❌ Approval gagal setelah 5 attempts. Error: {result}[/bold red]")
                console.print(f"[yellow]Possible causes: Invalid token contract, insufficient balance, or contract issue.[/yellow]")
                console.print(f"[red]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Approve {from_token_key} - Failed: {result}[/red]")
                return False, str(result)
            nonce += 1
    except ABIFunctionNotFound as e:
        console.print(f"[bold red]❌ Error: Function 'allowance' not found in {from_token_key} contract ABI at {from_token_addr}.[/bold red]")
        console.print(f"[yellow]Possible cause: The contract is not ERC20-compliant or the address is incorrect.[/yellow]")
        console.print(f"[red]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Approve {from_token_key} - Failed: {e}[/red]")
        return False, str(e)
    
    console.print("  [magenta]-> Melakukan Swap...[/magenta]")
    swap_txn = router_contract.functions.swapExactTokensForTokens(
        amount_in_wei, 0, [from_token_addr, to_token_addr], my_address, int(time.time()) + 600
    ).build_transaction({
        'from': my_address,
        'nonce': nonce,
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id
    })
    success, result = retry_transaction(console, w3, account, swap_txn, f"swap {from_token_key} -> {to_token_key}")
    if success:
        console.print("  [bold green]✅ BERHASIL[/bold green]\n")
        console.print(f"[green]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Swap {from_token_key} -> {to_token_key} - Success[/green]")
        return True, None
    console.print(f"[bold red]❌ Swap gagal setelah 5 attempts. Error: {result}[/bold red]")
    console.print(f"[yellow]Possible causes: Insufficient liquidity, invalid swap path ({from_token_key} -> {to_token_key}), or contract issue.[/yellow]")
    console.print(f"[red]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Swap {from_token_key} -> {to_token_key} - Failed: {result}[/red]")
    return False, str(result)

def swap_to_wkas(console, w3, account, from_token_key, amount_in_wei, idx, total_wallets):
    console.print(Panel(f"🔁 [bold]LANGKAH 8a dari 8[/bold]: SWAP {from_token_key} -> WKAS", style="cyan"))
    if amount_in_wei == 0:
        console.print("  [yellow]⚠️  Saldo 0, melewati swap ke WKAS.[/yellow]")
        console.print(f"[green]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Swap {from_token_key} -> WKAS - Success[/green]")
        return True, None
    from_token_addr = Web3.to_checksum_address(TOKENS[from_token_key])
    wkas_addr = Web3.to_checksum_address(TOKENS["WKAS"])
    router_addr = Web3.to_checksum_address(ROUTER_ADDRESS)
    my_address = account.address
    from_token_contract = w3.eth.contract(address=from_token_addr, abi=ABI_ERC20)
    router_contract = w3.eth.contract(address=router_addr, abi=ABI_ROUTER)
    console.print(f"  [cyan]-> Using router: {ROUTER_ADDRESS} for swap {from_token_key} -> WKAS[/cyan]")
    
    try:
        balance = from_token_contract.functions.balanceOf(my_address).call()
        balance_text = Text.assemble(("  -> Saldo ", "white"), (f"{w3.from_wei(balance, 'ether')}", "bold magenta"), (f" {from_token_key} yang akan di-swap ke WKAS", "white"))
        console.print(balance_text)
        if balance < amount_in_wei:
            console.print(f"[bold red]❌ Saldo {from_token_key} tidak cukup: {w3.from_wei(balance, 'ether')} < {w3.from_wei(amount_in_wei, 'ether')}[/bold red]")
            console.print(f"[red]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Swap {from_token_key} -> WKAS - Failed: Insufficient {from_token_key} balance[/red]")
            return False, f"Insufficient {from_token_key} balance"
    except ABIFunctionNotFound as e:
        console.print(f"[bold red]❌ Error: Function 'balanceOf' not found in {from_token_key} contract ABI at {from_token_addr}.[/bold red]")
        console.print("[yellow]Possible cause: The contract is not ERC20-compliant or the address is incorrect.[/yellow]")
        console.print(f"[red]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Swap {from_token_key} -> WKAS - Failed: {e}[/red]")
        return False, str(e)
    
    nonce = wait_for_pending_tx(console, w3, account)
    if nonce is None:
        console.print(f"[red]Wallet {idx}/{total_wallets}: {account.address[:8]}...{account.address[-8:]} - Swap {from_token_key} -> WKAS - Failed: Timeout waiting for mempool[/red]")
        return False, "Timeout waiting for mempool"
    
    try:
        allowance = from_token_contract.functions.allowance(my_address, router_addr).call()
        console.print(f"  [cyan]-> Current allowance for {from_token_key}: {w3.from_wei(allowance, 'ether')} {from_token_key}[/cyan]")
        if allowance < amount_in_wei:
            console.print("  [magenta]-> Menyetujui (Approve) token untuk swap ke WKAS...[/magenta]")
            approve_txn = from_token_contract.functions.approve(router_addr, amount_in_wei).build_transaction({
                'from': my_address,
                'nonce': nonce,
                'gasPrice': w3.eth.gas_price,
                'chainId': w3.eth.chain_id
            })
            success, result = retry_transaction(console, w3, account, approve_txn, "approve token for swap to WKAS")
    
