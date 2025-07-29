import json
import time
import re
import random
import signal
import sys
from web3 import Web3, HTTPProvider
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# Configuration
RPC_URL = 'https://rpc.kasplextest.xyz/'
PRIVATE_KEY_FILE = 'private_key.txt'
ROUTER_ADDRESS = '0xaE821200c01E532E5A252FfCaA8546cbdca342DF'

TOKENS = {
    "WKAS": "0xf40178040278E16c8813dB20a84119A605812FB3",
    "TZEAL": "0xD6411bc52c8CbD192477233F2DB211cB96bc3504",
    "TNACHO": "0xfa458995688c73fc48E7D833483a7206Bed75C27",
    "TKANGO": "0x46B4B1A6c462609957D17D5d8eEA12037E44ef3F"
}

STAKING_ADDRESSES = {
    "TZEAL": "0x86264b694c3c3Bc1907ace84DbcF823758E9b948",
    "TNACHO": "0xC5f458f60C3D44256dD7c6290e981C01cd0BBb52"
}

FARM_ADDRESS = "0x65b0552Be5c62d60EC4a3daCC72894c8F96C619a"

# Pair addresses untuk mendapatkan reserves yang akurat
PAIR_ADDRESSES = {
    "TZEAL_WKAS": "0xd2f622db6b6d67EFac968758905a0649dBA4ce3D",
    "WKAS_TNACHO": "0xC4278FE8b7009a7DCc445024Cb864f26c1F81073", 
    "TKANGO_WKAS": "0xD9737e464Df3625e08a7F3Df61aABFBf523DBCfC"
}

LP_TOKENS = {
    "TZEAL_WKAS": "0xd2f622db6b6d67EFac968758905a0649dBA4ce3D",
    "WKAS_TNACHO": "0xC4278FE8b7009a7DCc445024Cb864f26c1F81073",
    "TKANGO_WKAS": "0xD9737e464Df3625e08a7F3Df61aABFBf523DBCfC"
}

# ABI untuk Uniswap V2 Pair contract
ABI_PAIR = json.loads('[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]')

ABI_ERC20 = json.loads('[{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}, {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}, {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256"}],"type":"function"}, {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]')

ABI_ROUTER = json.loads('[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"}, {"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"amountADesired","type":"uint256"},{"internalType":"uint256","name":"amountBDesired","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}, {"inputs":[{"internalType":"uint256","name":"amountADesired","type":"uint256"},{"internalType":"uint256","name":"amountBDesired","type":"uint256"},{"internalType":"uint256","name":"reserveA","type":"uint256"},{"internalType":"uint256","name":"reserveB","type":"uint256"}],"name":"quote","outputs":[{"internalType":"uint256","name":"amountB","type":"uint256"}],"stateMutability":"pure","type":"function"}]')

ABI_WKAS = json.loads('[{"name":"deposit","outputs":[],"inputs":[],"stateMutability":"payable","type":"function","payable":true}, {"name":"withdraw","inputs":[{"name":"wad","type":"uint256"}],"outputs":[],"stateMutability":"nonpayable","type":"function"}]')

ABI_STAKING = json.loads('[{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"stake","outputs":[],"stateMutability":"nonpayable","type":"function"}, {"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"unstake","outputs":[],"stateMutability":"nonpayable","type":"function"}, {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]')

ABI_FARM = json.loads('[{"inputs":[{"internalType":"uint256","name":"pid","type":"uint256"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"deposit","outputs":[],"stateMutability":"nonpayable","type":"function"}, {"inputs":[{"internalType":"uint256","name":"pid","type":"uint256"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"withdraw","outputs":[],"stateMutability":"nonpayable","type":"function"}, {"inputs":[{"internalType":"uint256","name":"pid","type":"uint256"},{"internalType":"address","name":"user","type":"address"}],"name":"userInfo","outputs":[{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"uint256","name":"rewardDebt","type":"uint256"}],"stateMutability":"view","type":"function"}, {"inputs":[{"internalType":"uint256","name":"pid","type":"uint256"}],"name":"harvest","outputs":[],"stateMutability":"nonpayable","type":"function"}]')

def load_private_keys(console):
    try:
        with open(PRIVATE_KEY_FILE, 'r') as f:
            keys = [line.strip() for line in f if line.strip()]
        valid_keys = []
        for i, key in enumerate(keys, 1):
            key = key.replace('0x', '').strip()
            if re.match(r'^[0-9a-fA-F]{64}$', key):
                valid_keys.append('0x' + key)
            else:
                console.print(f"[red]❌ Invalid key {i}: {key[:10]}...[/red]")
        console.print(f"[green]✅ Loaded {len(valid_keys)} valid key(s)[/green]")
        return valid_keys
    except FileNotFoundError:
        console.print(f"[red]❌ File {PRIVATE_KEY_FILE} not found[/red]")
        return []

def get_nonce(w3, address):
    return w3.eth.get_transaction_count(address)

def send_transaction_with_retry(console, w3, account, transaction, tx_type, max_retries=3):
    """Enhanced transaction sending with retry logic"""
    for attempt in range(1, max_retries + 1):
        try:
            # Update nonce for each attempt
            transaction['nonce'] = get_nonce(w3, account.address)
            
            # Try to estimate gas first
            try:
                gas_estimate = w3.eth.estimate_gas(transaction)
                transaction['gas'] = int(gas_estimate * 1.3)  # 30% buffer
            except Exception as gas_error:
                console.print(f"[yellow]⚠️ Gas estimation failed, using fixed gas limit: {str(gas_error)[:50]}...[/yellow]")
                transaction['gas'] = 500000  # Fixed high gas limit
            
            # Increase gas price for retries
            if attempt > 1:
                transaction['gasPrice'] = int(w3.eth.gas_price * (1 + 0.2 * attempt))
            
            signed_tx = w3.eth.account.sign_transaction(transaction, account.key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            console.print(f"[cyan]📤 {tx_type} sent (attempt {attempt}): {tx_hash.hex()[:10]}...[/cyan]")
            
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)  # Increased timeout
            
            if receipt['status'] == 1:
                console.print(f"[green]✅ {tx_type} successful[/green]")
                # Add random delay after successful transaction
                delay_seconds = random.uniform(5, 10)
                console.print(f"[yellow]⏳ Random delay {delay_seconds:.2f} seconds after transaction[/yellow]")
                time.sleep(delay_seconds)
                return True, receipt
            else:
                console.print(f"[red]❌ {tx_type} failed - attempt {attempt}[/red]")
                
        except Exception as e:
            error_msg = str(e)
            if "nonce too low" in error_msg.lower():
                console.print(f"[yellow]⚠️ Nonce too low, updating... (attempt {attempt})[/yellow]")
                time.sleep(2)  # Wait a bit for nonce to update
            elif "gas required exceeds" in error_msg.lower():
                console.print(f"[red]❌ Gas limit exceeded (attempt {attempt}): {error_msg[:50]}...[/red]")
                if attempt == max_retries:
                    # Add random delay after final failure
                    delay_seconds = random.uniform(5, 10)
                    console.print(f"[yellow]⏳ Random delay {delay_seconds:.2f} seconds after transaction[/yellow]")
                    time.sleep(delay_seconds)
                    return False, None
            else:
                console.print(f"[red]❌ {tx_type} error (attempt {attempt}): {error_msg[:50]}...[/red]")
        
        if attempt < max_retries:
            console.print(f"[yellow]⏳ Retrying in 3 seconds...[/yellow]")
            time.sleep(3)
    
    # Add random delay after all retries failed
    delay_seconds = random.uniform(5, 10)
    console.print(f"[yellow]⏳ Random delay {delay_seconds:.2f} seconds after transaction[/yellow]")
    time.sleep(delay_seconds)
    
    return False, None

def send_transaction(console, w3, account, transaction, tx_type, max_retries=3):
    return send_transaction_with_retry(console, w3, account, transaction, tx_type, max_retries)

def get_token_balance(w3, address, token_key):
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(TOKENS[token_key]), 
            abi=ABI_ERC20
        )
        return contract.functions.balanceOf(address).call()
    except:
        return 0

def get_lp_balance(w3, address, lp_token_address):
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(lp_token_address), 
            abi=ABI_ERC20
        )
        return contract.functions.balanceOf(address).call()
    except:
        return 0

def get_staked_balance(w3, address, staking_address):
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(staking_address),
            abi=ABI_STAKING
        )
        return contract.functions.balanceOf(address).call()
    except:
        return 0

def get_farmed_balance(w3, address, farm_address, pid):
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(farm_address),
            abi=ABI_FARM
        )
        user_info = contract.functions.userInfo(pid, address).call()
        return user_info[0]
    except:
        return 0

def get_pair_reserves_and_tokens(console, w3, pair_address):
    """Mendapatkan reserves dan token order dari pair contract"""
    try:
        pair_contract = w3.eth.contract(
            address=Web3.to_checksum_address(pair_address), 
            abi=ABI_PAIR
        )
        
        # Dapatkan reserves
        reserves = pair_contract.functions.getReserves().call()
        reserve0, reserve1, timestamp = reserves
        
        # Dapatkan token addresses
        token0 = pair_contract.functions.token0().call()
        token1 = pair_contract.functions.token1().call()
        
        console.print(f"[cyan]📊 Pair Reserves: Reserve0={Web3.from_wei(reserve0, 'ether'):.6f}, Reserve1={Web3.from_wei(reserve1, 'ether'):.6f}[/cyan]")
        console.print(f"[cyan]🔍 Token0: {token0}, Token1: {token1}[/cyan]")
        
        return reserve0, reserve1, token0.lower(), token1.lower()
    except Exception as e:
        console.print(f"[red]❌ Error getting pair info: {str(e)}[/red]")
        return None, None, None, None

def calculate_optimal_amounts(console, amount_a_desired, amount_b_desired, reserve_a, reserve_b):
    """Menghitung jumlah optimal berdasarkan reserves seperti di DEX"""
    if reserve_a == 0 or reserve_b == 0:
        return amount_a_desired, amount_b_desired
    
    # Hitung amount B yang dibutuhkan berdasarkan amount A
    amount_b_optimal = (amount_a_desired * reserve_b) // reserve_a
    
    if amount_b_optimal <= amount_b_desired:
        console.print(f"[green]✅ Optimal amounts: A={Web3.from_wei(amount_a_desired, 'ether'):.6f}, B={Web3.from_wei(amount_b_optimal, 'ether'):.6f}[/green]")
        return amount_a_desired, amount_b_optimal
    else:
        # Jika B optimal > B yang tersedia, hitung ulang berdasarkan B
        amount_a_optimal = (amount_b_desired * reserve_a) // reserve_b
        console.print(f"[green]✅ Optimal amounts: A={Web3.from_wei(amount_a_optimal, 'ether'):.6f}, B={Web3.from_wei(amount_b_desired, 'ether'):.6f}[/green]")
        return amount_a_optimal, amount_b_desired

def approve_token(console, w3, account, token_address, spender_address, amount):
    token_contract = w3.eth.contract(address=token_address, abi=ABI_ERC20)
    
    # Get token decimals for display
    try:
        decimals = token_contract.functions.decimals().call()
        readable_amount = amount / (10 ** decimals)
    except:
        decimals = 18
        readable_amount = Web3.from_wei(amount, 'ether')
    
    # Check existing allowance
    current_allowance = token_contract.functions.allowance(account.address, spender_address).call()
    
    # Display approval information
    console.print(f"[cyan]🔍 Current allowance: {Web3.from_wei(current_allowance, 'ether'):.6f}[/cyan]")
    console.print(f"[cyan]🔐 Approving {readable_amount:.6f} tokens to {spender_address[:8]}...[/cyan]")
    
    # If current allowance is sufficient, no need to approve
    if current_allowance >= amount:
        console.print(f"[green]✅ Already approved: {Web3.from_wei(current_allowance, 'ether'):.6f} >= {readable_amount:.6f}[/green]")
        return True

    # Attempt approval with the exact amount needed
    retry_attempts = 0
    while retry_attempts < 3:
        try:
            approve_tx = token_contract.functions.approve(spender_address, amount).build_transaction({
                'from': account.address,
                'nonce': get_nonce(w3, account.address),
                'gasPrice': w3.eth.gas_price,
                'chainId': w3.eth.chain_id
            })
            
            success, _ = send_transaction(console, w3, account, approve_tx, f"Token Approval")
            if success:
                console.print(f"[green]✅ Approved {readable_amount:.6f} tokens successfully![/green]")
                return True
            else:
                console.print(f"[red]❌ Approval transaction failed on attempt {retry_attempts + 1}[/red]")
        except Exception as e:
            console.print(f"[red]❌ Approval error (attempt {retry_attempts + 1}): {str(e)}[/red]")
        
        retry_attempts += 1
        time.sleep(2)
    
    console.print(f"[red]❌ Token approval failed after 3 attempts for {readable_amount:.6f} tokens[/red]")
    return False

def wrap_kas(console, w3, account, amount_kas):
    console.print(f"[cyan]📦 Wrapping {amount_kas} KAS...[/cyan]")
    amount_wei = w3.to_wei(amount_kas, 'ether')
    kas_balance = w3.eth.get_balance(account.address)
    if kas_balance < amount_wei:
        console.print(f"[red]❌ Insufficient KAS: {w3.from_wei(kas_balance, 'ether'):.6f}[/red]")
        return False
    wkas_contract = w3.eth.contract(
        address=Web3.to_checksum_address(TOKENS["WKAS"]), 
        abi=ABI_WKAS
    )
    transaction = wkas_contract.functions.deposit().build_transaction({
        'from': account.address,
        'nonce': get_nonce(w3, account.address),
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id,
        'value': amount_wei
    })
    success, _ = send_transaction(console, w3, account, transaction, "Wrap KAS")
    return success

def swap_kas_to_token(console, w3, account, to_token, amount_kas):
    console.print(f"[cyan]🔄 Swapping {amount_kas} KAS -> {to_token}...[/cyan]")
    if not wrap_kas(console, w3, account, amount_kas):
        return False
    amount_wei = w3.to_wei(amount_kas, 'ether')
    wkas_addr = Web3.to_checksum_address(TOKENS["WKAS"])
    to_addr = Web3.to_checksum_address(TOKENS[to_token])
    router_addr = Web3.to_checksum_address(ROUTER_ADDRESS)
    
    # Show approval details
    console.print(f"[cyan]🔐 Need approval for {Web3.from_wei(amount_wei, 'ether'):.6f} WKAS[/cyan]")
    if not approve_token(console, w3, account, wkas_addr, router_addr, amount_wei):
        return False
    
    router_contract = w3.eth.contract(address=router_addr, abi=ABI_ROUTER)
    try:
        swap_tx = router_contract.functions.swapExactTokensForTokens(
            amount_wei, 
            0, 
            [wkas_addr, to_addr], 
            account.address, 
            int(time.time()) + 600
        ).build_transaction({
            'from': account.address,
            'nonce': get_nonce(w3, account.address),
            'gasPrice': w3.eth.gas_price,
            'chainId': w3.eth.chain_id
        })
        success, _ = send_transaction(console, w3, account, swap_tx, f"Swap KAS->{to_token}")
        return success
    except Exception as e:
        console.print(f"[red]❌ Swap error: {e}[/red]")
        return False

def wrap_and_swap_preset(console, w3, account):
    """New function for preset wrap and swap operations"""
    console.print(f"[bold yellow]🎯 Starting preset wrap and swap for wallet {account.address[:8]}...[/bold yellow]")
    
    # Check KAS balance
    kas_balance = w3.eth.get_balance(account.address)
    required_kas = w3.to_wei(8, 'ether')  # 3 + 2 + 2 + 1 = 8 KAS
    
    if kas_balance < required_kas:
        console.print(f"[red]❌ Insufficient KAS: required 8, have {w3.from_wei(kas_balance, 'ether'):.6f}[/red]")
        return False
    
    success_count = 0
    
    # Retry each operation up to 3 times
    def retry_operation(operation, description):
        for attempt in range(1, 4):
            console.print(f"[yellow]🔁 Attempt {attempt}/3 for {description}[/yellow]")
            if operation():
                return True
            time.sleep(2)
        return False
    
    # 1. Wrap 3 KAS to WKAS
    console.print("[cyan]Step 1: Wrapping 3 KAS to WKAS[/cyan]")
    if retry_operation(lambda: wrap_kas(console, w3, account, 3), "Wrap KAS"):
        success_count += 1
        time.sleep(2)
    
    # 2. Swap 2 KAS to TZEAL
    console.print("[cyan]Step 2: Swapping 2 KAS to TZEAL[/cyan]")
    if retry_operation(lambda: swap_kas_to_token(console, w3, account, "TZEAL", 2), "Swap to TZEAL"):
        success_count += 1
        time.sleep(2)
    
    # 3. Swap 2 KAS to TNACHO
    console.print("[cyan]Step 3: Swapping 2 KAS to TNACHO[/cyan]")
    if retry_operation(lambda: swap_kas_to_token(console, w3, account, "TNACHO", 2), "Swap to TNACHO"):
        success_count += 1
        time.sleep(2)
    
    # 4. Swap 1 KAS to TKANGO
    console.print("[cyan]Step 4: Swapping 1 KAS to TKANGO[/cyan]")
    if retry_operation(lambda: swap_kas_to_token(console, w3, account, "TKANGO", 1), "Swap to TKANGO"):
        success_count += 1
    
    console.print(f"[green]✅ Wrap and swap completed: {success_count}/4 operations successful[/green]")
    return success_count == 4

def add_liquidity_pair_improved(console, w3, account, token_a, token_b, amount_a):
    """Versi improved dari add liquidity dengan kalkulasi yang lebih akurat"""
    console.print(f"[bold yellow]🌊 Adding Liquidity: {token_a}/{token_b}[/bold yellow]")
    
    # Tentukan pair name dan address
    pair_name = f"{token_a}_{token_b}" if f"{token_a}_{token_b}" in LP_TOKENS else f"{token_b}_{token_a}"
    pair_address = PAIR_ADDRESSES.get(pair_name)
    
    if not pair_address:
        console.print(f"[red]❌ Pair address untuk {token_a}/{token_b} tidak ditemukan[/red]")
        return False

    # Setup addresses
    token_a_addr = Web3.to_checksum_address(TOKENS[token_a])
    token_b_addr = Web3.to_checksum_address(TOKENS[token_b])
    router_addr = Web3.to_checksum_address(ROUTER_ADDRESS)
    
    # Cek balance
    balance_a = get_token_balance(w3, account.address, token_a)
    balance_b = get_token_balance(w3, account.address, token_b)
    
    amount_a_wei = w3.to_wei(amount_a, 'ether')
    
    console.print(f"[cyan]💰 Balance {token_a}: {Web3.from_wei(balance_a, 'ether'):.6f}[/cyan]")
    console.print(f"[cyan]💰 Balance {token_b}: {Web3.from_wei(balance_b, 'ether'):.6f[/cyan]}")
    
    if balance_a < amount_a_wei:
        console.print(f"[red]❌ Insufficient {token_a}: required {amount_a}, have {Web3.from_wei(balance_a, 'ether'):.6f}[/red]")
        return False
    
    if balance_b == 0:
        console.print(f"[red]❌ No {token_b} balance[/red]")
        return False

    # Dapatkan reserves dari pair contract
    reserve0, reserve1, token0, token1 = get_pair_reserves_and_tokens(console, w3, pair_address)
    
    if reserve0 is None:
        console.print("[red]❌ Gagal mendapatkan informasi pair[/red]")
        return False
    
    # Tentukan order token dan reserves
    token_a_lower = token_a_addr.lower()
    token_b_lower = token_b_addr.lower()
    
    if token_a_lower == token0:
        reserve_a, reserve_b = reserve0, reserve1
        console.print(f"[green]✅ Token order: {token_a} (token0), {token_b} (token1)[/green]")
    elif token_a_lower == token1:
        reserve_a, reserve_b = reserve1, reserve0
        console.print(f"[green]✅ Token order: {token_a} (token1), {token_b} (token0)[/green]")
    else:
        console.print(f"[red]❌ Token {token_a} tidak ditemukan di pair[/red]")
        return False
    
    # Hitung jumlah optimal
    amount_a_optimal, amount_b_optimal = calculate_optimal_amounts(
        console, amount_a_wei, balance_b, reserve_a, reserve_b
    )
    
    # Validasi balance
    if amount_b_optimal > balance_b:
        console.print(f"[red]❌ Insufficient {token_b}: required {Web3.from_wei(amount_b_optimal, 'ether'):.6f}, have {Web3.from_wei(balance_b, 'ether'):.6f}[/red]")
        return False
    
    # Hitung slippage protection (1% tolerance)
    slippage = 0.01
    amount_a_min = int(amount_a_optimal * (1 - slippage))
    amount_b_min = int(amount_b_optimal * (1 - slippage))
    
    console.print(f"[yellow]⚠️ Slippage protection: A_min={Web3.from_wei(amount_a_min, 'ether'):.6f}, B_min={Web3.from_wei(amount_b_min, 'ether'):.6f}[/yellow]")
    
    # Approve tokens with exact amounts
    console.print(f"[cyan]🔐 Approving {token_a} tokens for liquidity add...[/cyan]")
    if not approve_token(console, w3, account, token_a_addr, router_addr, amount_a_optimal):
        return False
    
    console.print(f"[cyan]🔐 Approving {token_b} tokens for liquidity add...[/cyan]")
    if not approve_token(console, w3, account, token_b_addr, router_addr, amount_b_optimal):
        return False
    
    # Execute add liquidity with retry
    for attempt in range(1, 4):
        console.print(f"[yellow]🔁 Attempt {attempt}/3 for Add Liquidity {token_a}/{token_b}[/yellow]")
        try:
            router_contract = w3.eth.contract(address=router_addr, abi=ABI_ROUTER)
            
            liquidity_tx = router_contract.functions.addLiquidity(
                token_a_addr,
                token_b_addr,
                amount_a_optimal,
                amount_b_optimal,
                amount_a_min,
                amount_b_min,
                account.address,
                int(time.time()) + 600  # 10 minutes deadline
            ).build_transaction({
                'from': account.address,
                'nonce': get_nonce(w3, account.address),
                'gasPrice': w3.eth.gas_price,
                'chainId': w3.eth.chain_id
            })
            
            success, receipt = send_transaction(console, w3, account, liquidity_tx, f"Add Liquidity {token_a}/{token_b}")
            
            if success:
                console.print(f"[green]✅ Add Liquidity {token_a}/{token_b} successful![/green]")
                if receipt and receipt['logs']:
                    console.print(f"[cyan]📊 Transaction used {receipt['gasUsed']} gas[/cyan]")
                return True
            else:
                console.print(f"[red]❌ Add Liquidity failed on attempt {attempt}[/red]")
                
        except Exception as e:
            console.print(f"[red]❌ Add Liquidity error (attempt {attempt}): {str(e)}[/red]")
        
        if attempt < 3:
            time.sleep(2)
    
    console.print(f"[red]❌ Add Liquidity failed after 3 attempts[/red]")
    return False

def stake_token(console, w3, account, token_key):
    console.print(f"[cyan]🥩 Staking {token_key}...[/cyan]")
    if token_key not in STAKING_ADDRESSES:
        console.print(f"[red]❌ No staking address for {token_key}[/red]")
        return False
    balance = get_token_balance(w3, account.address, token_key)
    if balance == 0:
        console.print(f"[yellow]⚠️ No {token_key} to stake[/yellow]")
        return True
    
    # Retry up to 3 times
    for attempt in range(1, 4):
        console.print(f"[yellow]🔁 Attempt {attempt}/3 for Stake {token_key}[/yellow]")
        
        token_addr = Web3.to_checksum_address(TOKENS[token_key])
        staking_addr = Web3.to_checksum_address(STAKING_ADDRESSES[token_key])
        
        console.print(f"[cyan]🔐 Approving {token_key} for staking...[/cyan]")
        if not approve_token(console, w3, account, token_addr, staking_addr, balance):
            continue
        
        try:
            staking_contract = w3.eth.contract(address=staking_addr, abi=ABI_STAKING)
            stake_tx = staking_contract.functions.stake(balance).build_transaction({
                'from': account.address,
                'nonce': get_nonce(w3, account.address),
                'gasPrice': w3.eth.gas_price,
                'chainId': w3.eth.chain_id
            })
            success, _ = send_transaction(console, w3, account, stake_tx, f"Stake {token_key}")
            if success:
                return True
        except Exception as e:
            console.print(f"[red]❌ Stake error (attempt {attempt}): {str(e)}[/red]")
        
        if attempt < 3:
            time.sleep(2)
    
    console.print(f"[red]❌ Stake operation failed after 3 attempts[/red]")
    return False

def claim_farm_rewards(console, w3, account, pid):
    """Claim TZEAL rewards from farm before depositing"""
    console.print(f"[cyan]🎁 Attempting to claim farm rewards for PID {pid}...[/cyan]")
    farm_addr = Web3.to_checksum_address(FARM_ADDRESS)
    farm_contract = w3.eth.contract(address=farm_addr, abi=ABI_FARM)
    
    try:
        # Check if user has any farmed tokens first
        user_info = farm_contract.functions.userInfo(pid, account.address).call()
        farmed_amount = user_info[0]
        
        if farmed_amount == 0:
            console.print(f"[yellow]⚠️ No farmed tokens to claim for PID {pid}[/yellow]")
            return True
        
        # Try to claim rewards with better gas estimation
        harvest_tx = farm_contract.functions.harvest(pid).build_transaction({
            'from': account.address,
            'nonce': get_nonce(w3, account.address),
            'gasPrice': int(w3.eth.gas_price * 1.2),  # Increase gas price by 20%
            'chainId': w3.eth.chain_id
        })
        
        # Try to estimate gas, if it fails, skip claiming
        try:
            gas_estimate = w3.eth.estimate_gas(harvest_tx)
            harvest_tx['gas'] = int(gas_estimate * 1.5)  # Add more gas buffer
        except Exception as gas_error:
            console.print(f"[yellow]⚠️ Cannot estimate gas for harvest, skipping claim: {str(gas_error)[:50]}...[/yellow]")
            return True  # Continue without claiming
        
        success, _ = send_transaction(console, w3, account, harvest_tx, f"Claim Rewards PID {pid}", max_retries=1)
        return True  # Always return True to continue with farming
        
    except Exception as e:
        console.print(f"[yellow]⚠️ Claim rewards not available for PID {pid}: {str(e)[:50]}...[/yellow]")
        return True  # Continue without claiming

def farm_lp_token(console, w3, account, lp_pair, pid):
    console.print(f"[cyan]🚜 Farming {lp_pair}...[/cyan]")
    if lp_pair not in LP_TOKENS or not LP_TOKENS[lp_pair]:
        console.print(f"[red]❌ No LP token address for {lp_pair}[/red]")
        return False
    
    # Try to claim rewards first (but don't fail if it doesn't work)
    claim_farm_rewards(console, w3, account, pid)
    time.sleep(2)
    
    lp_addr = Web3.to_checksum_address(LP_TOKENS[lp_pair])
    farm_addr = Web3.to_checksum_address(FARM_ADDRESS)
    lp_balance = get_lp_balance(w3, account.address, LP_TOKENS[lp_pair])
    farmed_balance_before = get_farmed_balance(w3, account.address, FARM_ADDRESS, pid)
    
    console.print(f"[bold yellow]LP balance for {lp_pair}: {Web3.from_wei(lp_balance, 'ether'):.6f} | Farmed before: {Web3.from_wei(farmed_balance_before, 'ether'):.6f}[/bold yellow]")
    
    if lp_balance == 0:
        console.print(f"[yellow]⚠️ No {lp_pair} LP tokens to farm[/yellow]")
        return True
    
    # Check if we already have enough farmed tokens to avoid underflow
    total_after_deposit = farmed_balance_before + lp_balance
    if total_after_deposit <= farmed_balance_before:
        console.print(f"[yellow]⚠️ Potential underflow detected, skipping farm for {lp_pair}[/yellow]")
        return True
    
    # Approve exact LP token amount
    console.print(f"[cyan]🔐 Approving {lp_pair} LP tokens for farming...[/cyan]")
    if not approve_token(console, w3, account, lp_addr, farm_addr, lp_balance):
        return False
    
    # Retry farming up to 3 times
    for attempt in range(1, 4):
        console.print(f"[yellow]🔁 Attempt {attempt}/3 for Farm {lp_pair}[/yellow]")
        
        try:
            farm_contract = w3.eth.contract(address=farm_addr, abi=ABI_FARM)
            
            farm_tx = farm_contract.functions.deposit(pid, lp_balance).build_transaction({
                'from': account.address,
                'nonce': get_nonce(w3, account.address),
                'gasPrice': int(w3.eth.gas_price * 1.2),  # Increase gas price by 20%
                'chainId': w3.eth.chain_id
            })
            
            # Better gas estimation with more buffer
            try:
                gas_estimate = w3.eth.estimate_gas(farm_tx)
                farm_tx['gas'] = int(gas_estimate * 1.5)  # 50% gas buffer
            except Exception as gas_error:
                console.print(f"[red]❌ Gas estimation failed for {lp_pair}: {str(gas_error)[:100]}...[/red]")
                # Try with a fixed high gas limit
                farm_tx['gas'] = 500000
            
            success, _ = send_transaction(console, w3, account, farm_tx, f"Farm {lp_pair}")
            
            if success:
                farmed_balance_after = get_farmed_balance(w3, account.address, FARM_ADDRESS, pid)
                console.print(f"[bold green]Farmed after: {Web3.from_wei(farmed_balance_after, 'ether'):.6f}[/bold green]")
                return True
            else:
                console.print(f"[red]❌ Farm failed on attempt {attempt}[/red]")
                
        except Exception as e:
            error_msg = str(e)
            if "ds-math-sub-underflow" in error_msg:
                console.print(f"[red]❌ Farm underflow error for {lp_pair} - contract arithmetic issue[/red]")
            elif "gas required exceeds" in error_msg:
                console.print(f"[red]❌ Gas limit exceeded for {lp_pair} - transaction too complex[/red]")
            else:
                console.print(f"[red]❌ Farm error for {lp_pair} (attempt {attempt}): {error_msg[:100]}...[/red]")
        
        if attempt < 3:
            time.sleep(2)
    
    console.print(f"[red]❌ Farm operation failed after 3 attempts[/red]")
    return False

def farm_all_lp(console, w3, account):
    """Farm all LP tokens with better error handling"""
    console.print(f"[bold yellow]🚜 Starting LP farming for all pairs...[/bold yellow]")
    
    success_count = 0
    total_pairs = len(LP_TOKENS)
    
    for lp_pair, lp_addr in LP_TOKENS.items():
        pid = list(LP_TOKENS.keys()).index(lp_pair)
        
        console.print(f"[cyan]📍 Processing {lp_pair} (PID: {pid})[/cyan]")
        
        try:
            if farm_lp_token(console, w3, account, lp_pair, pid):
                success_count += 1
                console.print(f"[green]✅ {lp_pair} farming completed successfully[/green]")
            else:
                console.print(f"[yellow]⚠️ {lp_pair} farming skipped or failed[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Critical error farming {lp_pair}: {str(e)}[/red]")
        
        # Delay between farming operations
        if lp_pair != list(LP_TOKENS.keys())[-1]:  # Not the last item
            delay = random.randint(3, 6)
            console.print(f"[yellow]⏳ Waiting {delay} seconds before next farm...[/yellow]")
            time.sleep(delay)
    
    console.print(f"[bold green]🎯 LP Farming Summary: {success_count}/{total_pairs} pairs completed successfully[/bold green]")
    return success_count > 0

def run_complete_cycle(console, w3, account):
    """Run complete cycle: wrap/swap -> add liquidity -> stake -> farm"""
    console.print(f"[bold magenta]🔄 Starting complete cycle for wallet {account.address[:8]}...[/bold magenta]")
    
    success_count = 0
    
    # Step 1: Wrap and Swap
    console.print("[bold cyan]Phase 1: Wrap and Swap[/bold cyan]")
    if wrap_and_swap_preset(console, w3, account):
        success_count += 1
        time.sleep(3)
    
    # Step 2: Add Liquidity (1 WKAS default for all pairs)
    console.print("[bold cyan]Phase 2: Add Liquidity[/bold cyan]")
    liquidity_pairs = [
        ("WKAS", "TZEAL"),
        ("WKAS", "TNACHO"), 
        ("WKAS", "TKANGO")
    ]
    
    for token_a, token_b in liquidity_pairs:
        if add_liquidity_pair_improved(console, w3, account, token_a, token_b, 1):
            success_count += 1
        time.sleep(random.randint(2, 4))
    
    # Step 3: Stake remaining tokens
    console.print("[bold cyan]Phase 3: Stake Remaining Tokens[/bold cyan]")
    for token in ["TZEAL", "TNACHO"]:
        if stake_token(console, w3, account, token):
            success_count += 1
        time.sleep(random.randint(2, 4))
    
    # Step 4: Farm LP tokens
    console.print("[bold cyan]Phase 4: Farm LP Tokens[/bold cyan]")
    farm_all_lp(console, w3, account)
    success_count += 1
    
    console.print(f"[bold green]✅ Complete cycle finished for wallet {account.address[:8]}... Success rate: {success_count}/6[/bold green]")
    return success_count

def show_balances(console, w3, accounts):
    console.print(Panel("[bold]📊 WALLET BALANCES[/bold]", style="green"))
    for i, account in enumerate(accounts, 1):
        console.print(f"[bold]Wallet {i}: {account.address[:8]}...{account.address[-6:]}[/bold]")
        kas_balance = w3.eth.get_balance(account.address)
        console.print(f"  💰 KAS: {Web3.from_wei(kas_balance, 'ether'):.6f}")
        for token in TOKENS:
            balance = get_token_balance(w3, account.address, token)
            if balance > 0:
                console.print(f"  🪙 {token}: {Web3.from_wei(balance, 'ether'):.6f}")
        for lp_pair, lp_addr in LP_TOKENS.items():
            balance = get_lp_balance(w3, account.address, lp_addr)
            if balance > 0:
                console.print(f"  🌊 LP-{lp_pair}: {Web3.from_wei(balance, 'ether'):.6f}")
        for token, staking_addr in STAKING_ADDRESSES.items():
            staked = get_staked_balance(w3, account.address, staking_addr)
            if staked > 0:
                console.print(f"  🥩 Staked {token}: {Web3.from_wei(staked, 'ether'):.6f}")
        # Tampilkan farmed LP balance
        for idx, lp_pair in enumerate(LP_TOKENS.keys()):
            farmed = get_farmed_balance(w3, account.address, FARM_ADDRESS, idx)
            if farmed > 0:
                console.print(f"  🚜 Farmed {lp_pair}: {Web3.from_wei(farmed, 'ether'):.6f}")

def run_all_wallets_with_delays(console, w3, accounts, operation_func, operation_name):
    """Run operation on all wallets with delays"""
    total_wallets = len(accounts)
    
    for i, account in enumerate(accounts, 1):
        console.print(f"[bold blue]🏃 Running {operation_name} for wallet {i}/{total_wallets}: {account.address[:8]}...[/bold blue]")
        
        try:
            operation_func(console, w3, account)
        except Exception as e:
            console.print(f"[red]❌ Error in {operation_name} for wallet {i}: {str(e)}[/red]")
        
        # Delay between wallets (60-120 seconds)
        if i < total_wallets:
            delay = random.randint(60, 120)
            console.print(f"[yellow]⏳ Waiting {delay} seconds before next wallet...[/yellow]")
            time.sleep(delay)

def run_complete_automation(console, w3, accounts):
    """Run complete automation with cycle delays"""
    console.print(Panel("[bold]🚀 STARTING COMPLETE AUTOMATION[/bold]", style="magenta"))
    
    cycle = 1
    while True:
        console.print(f"[bold magenta]🔄 Starting Cycle {cycle}[/bold magenta]")
        
        # Run complete cycle for all wallets
        run_all_wallets_with_delays(console, w3, accounts, run_complete_cycle, "Complete Cycle")
        
        console.print(f"[bold green]✅ Cycle {cycle} completed for all wallets[/bold green]")
        
        # Delay between cycles (5-10 minutes)
        cycle_delay = random.randint(300, 600)  # 5-10 minutes in seconds
        console.print(f"[yellow]⏳ Waiting {cycle_delay//60} minutes before next cycle...[/yellow]")
        time.sleep(cycle_delay)
        
        cycle += 1

def main_menu(console, w3, accounts):
    while True:
        console.print(Panel("[bold]🍜 KAS NACHO LIQUIDITY MANAGER[/bold]", style="blue"))
        console.print("1. Wrap & Swap Preset (3 WKAS, 2 TZEAL, 2 TNACHO, 1 TKANGO)")
        console.print("2. Add Liquidity")
        console.print("3. Stake Tokens")
        console.print("4. Farm LP Tokens")
        console.print("5. Run Complete Cycle (Wrap/Swap -> Liquidity -> Stake -> Farm)")
        console.print("6. Run Complete Automation (All cycles with delays)")
        console.print("7. Show Balances")
        console.print("8. Exit")
        
        choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5", "6", "7", "8"])
        
        if choice == "1":
            console.print("[bold yellow]Running Wrap & Swap Preset for all wallets...[/bold yellow]")
            run_all_wallets_with_delays(console, w3, accounts, wrap_and_swap_preset, "Wrap & Swap Preset")
        
        elif choice == "2":
            token_a = Prompt.ask("First token", choices=list(TOKENS.keys()), default="WKAS")
            token_b = Prompt.ask("Second token", choices=list(TOKENS.keys()), default="TNACHO")
            amount = float(Prompt.ask(f"Amount of {token_a} to use", default="1"))
            
            def add_liquidity_operation(console, w3, account):
                add_liquidity_pair_improved(console, w3, account, token_a, token_b, amount)
            
            run_all_wallets_with_delays(console, w3, accounts, add_liquidity_operation, f"Add Liquidity {token_a}/{token_b}")
        
        elif choice == "3":
            token = Prompt.ask("Token to stake", choices=list(STAKING_ADDRESSES.keys()))
            
            def stake_operation(console, w3, account):
                stake_token(console, w3, account, token)
            
            run_all_wallets_with_delays(console, w3, accounts, stake_operation, f"Stake {token}")
        
        elif choice == "4":
            def farm_operation(console, w3, account):
                farm_all_lp(console, w3, account)
            
            run_all_wallets_with_delays(console, w3, accounts, farm_operation, "Farm LP Tokens")
        
        elif choice == "5":
            console.print("[bold yellow]Running Complete Cycle for all wallets...[/bold yellow]")
            run_all_wallets_with_delays(console, w3, accounts, run_complete_cycle, "Complete Cycle")
        
        elif choice == "6":
            console.print("[bold red]⚠️ This will run continuous automation. Press Ctrl+C to stop.[/bold red]")
            confirm = Prompt.ask("Continue?", choices=["y", "n"], default="n")
            if confirm == "y":
                try:
                    run_complete_automation(console, w3, accounts)
                except KeyboardInterrupt:
                    console.print("\n[yellow]⏹️ Automation stopped by user[/yellow]")
        
        elif choice == "7":
            show_balances(console, w3, accounts)
        
        elif choice == "8":
            console.print("[green]👋 Goodbye![/green]")
            sys.exit(0)

def main():
    console = Console()
    w3 = Web3(HTTPProvider(RPC_URL))
    
    if not w3.is_connected():
        console.print("[red]❌ Failed to connect to KAS network[/red]")
        return
    
    console.print(f"[green]✅ Connected to KAS Network (Chain ID: {w3.eth.chain_id})[/green]")
    
    private_keys = load_private_keys(console)
    if not private_keys:
        return
    
    accounts = [w3.eth.account.from_key(key) for key in private_keys]
    console.print(f"[green]✅ Loaded {len(accounts)} wallet(s)[/green]")
    
    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        console.print("\n[yellow]⏹️ Gracefully shutting down...[/yellow]")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    main_menu(console, w3, accounts)

if __name__ == "__main__":
    main()