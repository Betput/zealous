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
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.table import Table

# Configuration
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
    "TKASPY": "0x58CE5acc313B3fDC38adf3Ad670122556A44B009",
    "TBURT": "0x0b1793776E43D71Cc892E58849A0D2465FF36f10",
    "TKROAK": "0x34FaB1A1c8c64c6Fe9C860fe11601a3348aa5ab8",
    "TGHOAD": "0xd97D0AEc9CB23C3Ed3bBae393e85b542Db3226BF",
    "TKREX": "0x3Cfaf44e511f08D2Ad1049a79E6d5701272D707F",
    "TDOGK": "0xe8aCEFB936BEb37Bc3cdAB83E54b4941AFC2c85a"
}

SWAP_SEQUENCE = [
    "TZEAL", "XZEAL", "TNACHO", "XNACHO", "TKANGO", 
    "TKASPER", "TKASPY", "TBURT", "TKROAK", "TGHOAD", "TKREX", "TDOGK"
]

# ABIs
ABI_ERC20 = json.loads('[{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}, {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}, {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256"}],"type":"function"}]')
ABI_ROUTER = json.loads('[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"}]')
ABI_WKAS = json.loads('[{"name":"deposit","outputs":[],"inputs":[],"stateMutability":"payable","type":"function","payable":true}, {"name":"withdraw","inputs":[{"name":"wad","type":"uint256"}],"outputs":[],"stateMutability":"nonpayable","type":"function"}]')

def load_private_keys(console):
    """Load and validate private keys from file"""
    try:
        with open(PRIVATE_KEY_FILE, 'r') as f:
            keys = [line.strip() for line in f if line.strip()]
        
        if not keys:
            console.print(f"[red]❌ No keys found in {PRIVATE_KEY_FILE}[/red]")
            return []
        
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
    """Get current nonce for address"""
    return w3.eth.get_transaction_count(address)

def send_transaction(console, w3, account, transaction, tx_type, max_retries=3):
    """Send transaction with retry logic"""
    for attempt in range(1, max_retries + 1):
        try:
            # Estimate gas
            gas_estimate = w3.eth.estimate_gas(transaction)
            transaction['gas'] = int(gas_estimate * 1.2)  # 20% buffer
            
            # Sign and send
            signed_tx = w3.eth.account.sign_transaction(transaction, account.key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            console.print(f"[cyan]📤 {tx_type} sent: {tx_hash.hex()[:10]}...[/cyan]")
            
            # Wait for receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt['status'] == 1:
                console.print(f"[green]✅ {tx_type} successful[/green]")
                return True, receipt
            else:
                console.print(f"[red]❌ {tx_type} failed - attempt {attempt}[/red]")
                
        except Exception as e:
            console.print(f"[red]❌ {tx_type} error (attempt {attempt}): {str(e)[:50]}...[/red]")
            
        if attempt < max_retries:
            time.sleep(2)
    
    return False, None

def get_token_balance(w3, address, token_key):
    """Get token balance for address"""
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(TOKENS[token_key]), 
            abi=ABI_ERC20
        )
        return contract.functions.balanceOf(address).call()
    except:
        return 0

def wrap_kas(console, w3, account, amount_kas):
    """Wrap KAS to WKAS"""
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

def unwrap_wkas(console, w3, account):
    """Unwrap WKAS to KAS"""
    console.print("[cyan]📦 Unwrapping WKAS...[/cyan]")
    
    wkas_balance = get_token_balance(w3, account.address, "WKAS")
    if wkas_balance == 0:
        console.print("[yellow]⚠️  No WKAS to unwrap[/yellow]")
        return True
    
    wkas_contract = w3.eth.contract(
        address=Web3.to_checksum_address(TOKENS["WKAS"]), 
        abi=ABI_WKAS
    )
    
    transaction = wkas_contract.functions.withdraw(wkas_balance).build_transaction({
        'from': account.address,
        'nonce': get_nonce(w3, account.address),
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id
    })
    
    success, _ = send_transaction(console, w3, account, transaction, "Unwrap WKAS")
    return success

def swap_tokens(console, w3, account, from_token, to_token, amount_wei=None):
    """Swap between two tokens"""
    if amount_wei is None:
        amount_wei = get_token_balance(w3, account.address, from_token)
    
    if amount_wei == 0:
        console.print(f"[yellow]⚠️  No {from_token} to swap[/yellow]")
        return True
    
    console.print(f"[cyan]🔄 Swapping {from_token} -> {to_token}...[/cyan]")
    
    from_addr = Web3.to_checksum_address(TOKENS[from_token])
    to_addr = Web3.to_checksum_address(TOKENS[to_token])
    router_addr = Web3.to_checksum_address(ROUTER_ADDRESS)
    
    from_contract = w3.eth.contract(address=from_addr, abi=ABI_ERC20)
    router_contract = w3.eth.contract(address=router_addr, abi=ABI_ROUTER)
    
    # Check and approve if needed
    allowance = from_contract.functions.allowance(account.address, router_addr).call()
    if allowance < amount_wei:
        console.print(f"[cyan]🔐 Approving {from_token}...[/cyan]")
        approve_tx = from_contract.functions.approve(router_addr, amount_wei).build_transaction({
            'from': account.address,
            'nonce': get_nonce(w3, account.address),
            'gasPrice': w3.eth.gas_price,
            'chainId': w3.eth.chain_id
        })
        
        success, _ = send_transaction(console, w3, account, approve_tx, f"Approve {from_token}")
        if not success:
            return False
    
    # Perform swap
    swap_tx = router_contract.functions.swapExactTokensForTokens(
        amount_wei, 
        0, 
        [from_addr, to_addr], 
        account.address, 
        int(time.time()) + 600
    ).build_transaction({
        'from': account.address,
        'nonce': get_nonce(w3, account.address),
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id
    })
    
    success, _ = send_transaction(console, w3, account, swap_tx, f"Swap {from_token}->{to_token}")
    return success

def show_balances(console, w3, accounts):
    """Display wallet balances"""
    console.print(Panel("[bold]📊 WALLET BALANCES[/bold]", style="green"))
    
    for i, account in enumerate(accounts, 1):
        console.print(f"\n[bold]Wallet {i}: {account.address[:8]}...{account.address[-6:]}[/bold]")
        
        # KAS balance
        kas_balance = w3.eth.get_balance(account.address)
        console.print(f"  KAS: {w3.from_wei(kas_balance, 'ether'):.6f}")
        
        # Token balances
        for token in TOKENS:
            balance = get_token_balance(w3, account.address, token)
            if balance > 0:
                console.print(f"  {token}: {w3.from_wei(balance, 'ether'):.6f}")

def process_wallet(console, w3, account, operation, amount=None, from_token=None, to_token=None):
    """Process single wallet operation"""
    if operation == "wrap":
        return wrap_kas(console, w3, account, amount)
    elif operation == "unwrap":
        return unwrap_wkas(console, w3, account)
    elif operation == "swap":
        return swap_tokens(console, w3, account, from_token, to_token)
    elif operation == "full_sequence":
        return run_full_sequence_single(console, w3, account, amount)
    return False

def run_full_sequence_single(console, w3, account, amount, max_retries=5):
    """Run full sequence for single wallet with retry logic"""
    for attempt in range(1, max_retries + 1):
        try:
            console.print(f"[blue]🚀 Starting full sequence for {account.address[:8]}... with {amount} KAS (Attempt {attempt}/{max_retries})[/blue]")
            
            # Step 1: Wrap KAS
            if not wrap_kas(console, w3, account, amount):
                if attempt < max_retries:
                    console.print(f"[yellow]⚠️ Wrap failed, retrying in 5 seconds... (Attempt {attempt}/{max_retries})[/yellow]")
                    time.sleep(5)
                    continue
                return False
            
            # Step 2: Swap through sequence
            current_token = "WKAS"
            failed_swap = False
            for target_token in SWAP_SEQUENCE:
                if not swap_tokens(console, w3, account, current_token, target_token):
                    console.print(f"[red]❌ Failed at {current_token} -> {target_token}[/red]")
                    failed_swap = True
                    break
                current_token = target_token
                time.sleep(1)  # Small delay between swaps
            
            if failed_swap and attempt < max_retries:
                console.print(f"[yellow]⚠️ Swap sequence failed, retrying in 5 seconds... (Attempt {attempt}/{max_retries})[/yellow]")
                time.sleep(5)
                continue
            
            # Step 3: Swap back to WKAS
            if current_token != "WKAS":
                swap_tokens(console, w3, account, current_token, "WKAS")
            
            # Step 4: Unwrap WKAS
            unwrap_wkas(console, w3, account)
            
            console.print(f"[green]✅ Full sequence completed for {account.address[:8]}...[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error in full sequence (Attempt {attempt}/{max_retries}): {str(e)[:50]}...[/red]")
            if attempt < max_retries:
                console.print(f"[yellow]⚠️ Retrying in 5 seconds...[/yellow]")
                time.sleep(5)
            else:
                console.print(f"[red]❌ Max retries reached for {account.address[:8]}...[/red]")
                return False
    
    return False

def run_full_sequence_all_wallets(console, w3, accounts):
    """Run full sequence for all wallets in auto mode with random delays"""
    console.print(Panel.fit(
        "[bold green]🚀 AUTO MODE STARTED[/bold green]\n"
        "[cyan]Press Ctrl+C to stop at any time[/cyan]",
        border_style="green"
    ))
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            console.print(f"\n[bold blue]🔄 Starting Cycle {cycle_count}[/bold blue]")
            
            # Process each wallet
            for i, account in enumerate(accounts, 1):
                try:
                    # Random KAS amount between 1-5
                    random_amount = round(random.uniform(1.0, 5.0), 2)
                    
                    console.print(f"\n[bold cyan]Processing Wallet {i}/{len(accounts)} - {account.address[:8]}...[/bold cyan]")
                    console.print(f"[yellow]Using {random_amount} KAS[/yellow]")
                    
                    # Run full sequence for this wallet
                    success = run_full_sequence_single(console, w3, account, random_amount)
                    
                    if success:
                        console.print(f"[green]✅ Wallet {i} completed successfully[/green]")
                    else:
                        console.print(f"[red]❌ Wallet {i} failed after all retries[/red]")
                    
                    # Random delay between wallets (30-60 seconds)
                    if i < len(accounts):  # Don't delay after last wallet
                        delay = random.randint(30, 60)
                        console.print(f"[yellow]⏱️ Waiting {delay}s before next wallet...[/yellow]")
                        time.sleep(delay)
                        
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    console.print(f"[red]❌ Error processing wallet {i}: {str(e)[:50]}...[/red]")
                    continue
            
            # Show cycle summary
            console.print(f"\n[bold green]✅ Cycle {cycle_count} completed for all wallets[/bold green]")
            
            # Random delay between cycles (5-10 minutes)
            cycle_delay = random.randint(300, 600)  # 5-10 minutes
            console.print(f"[yellow]⏱️ Waiting {cycle_delay//60}m {cycle_delay%60}s before next cycle...[/yellow]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            
            # Sleep with periodic status updates
            for remaining in range(cycle_delay, 0, -30):
                if remaining <= 30:
                    time.sleep(remaining)
                    break
                time.sleep(30)
                console.print(f"[dim]⏱️ {remaining//60}m {remaining%60}s remaining...[/dim]")
            
    except KeyboardInterrupt:
        console.print(f"\n[yellow]⏹️ Auto mode stopped by user after {cycle_count} cycles[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Auto mode error: {str(e)}[/red]")

def show_menu():
    """Show main menu"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Option", style="cyan", width=6)
    table.add_column("Description", style="white")
    
    table.add_row("1", "📦 Wrap KAS -> WKAS")
    table.add_row("2", "📦 Unwrap WKAS -> KAS")
    table.add_row("3", "🔄 Swap Tokens")
    table.add_row("4", "🚀 Full Sequence (Auto Mode)")
    table.add_row("5", "📊 Show Balances")
    table.add_row("6", "❌ Exit")
    
    return table

def main():
    console = Console()
    
    # Signal handler
    def signal_handler(sig, frame):
        console.print("\n[red]❌ Interrupted by user[/red]")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Load keys and initialize
    private_keys = load_private_keys(console)
    if not private_keys:
        return
    
    # Connect to Web3
    console.print(f"[cyan]🌐 Connecting to {RPC_URL}[/cyan]")
    try:
        w3 = Web3(HTTPProvider(RPC_URL))
        if not w3.is_connected():
            console.print("[red]❌ Connection failed[/red]")
            return
        console.print(f"[green]✅ Connected - Chain ID: {w3.eth.chain_id}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Connection error: {e}[/red]")
        return
    
    # Create accounts
    accounts = [w3.eth.account.from_key(key) for key in private_keys]
    console.print(f"[green]✅ Loaded {len(accounts)} account(s)[/green]")
    
    # Main loop
    while True:
        try:
            console.clear()
            console.print(Panel.fit(
                "[bold blue]🚀 ZEALOUS TRADING BOT[/bold blue]\n"
                "[cyan]Simplified Kaspa Testnet Swapper[/cyan]",
                border_style="blue"
            ))
            
            console.print(show_menu())
            choice = Prompt.ask("\n[yellow]Choose option", choices=["1", "2", "3", "4", "5", "6"])
            
            if choice == "1":  # Wrap
                amount = float(Prompt.ask("[yellow]KAS amount to wrap", default="0.01"))
                console.print(f"\n[green]🚀 Wrapping {amount} KAS for {len(accounts)} wallet(s)[/green]")
                
                for i, account in enumerate(accounts, 1):
                    console.print(f"\n[blue]Wallet {i}/{len(accounts)}[/blue]")
                    process_wallet(console, w3, account, "wrap", amount)
            
            elif choice == "2":  # Unwrap
                console.print(f"\n[green]🚀 Unwrapping WKAS for {len(accounts)} wallet(s)[/green]")
                
                for i, account in enumerate(accounts, 1):
                    console.print(f"\n[blue]Wallet {i}/{len(accounts)}[/blue]")
                    process_wallet(console, w3, account, "unwrap")
            
            elif choice == "3":  # Swap
                token_list = list(TOKENS.keys())
                console.print("\n[yellow]Available tokens:[/yellow]")
                for i, token in enumerate(token_list, 1):
                    console.print(f"  {i}. {token}")
                
                from_idx = IntPrompt.ask("[yellow]From token (number)", default=1) - 1
                to_idx = IntPrompt.ask("[yellow]To token (number)", default=2) - 1
                
                if 0 <= from_idx < len(token_list) and 0 <= to_idx < len(token_list) and from_idx != to_idx:
                    from_token = token_list[from_idx]
                    to_token = token_list[to_idx]
                    
                    console.print(f"\n[green]🚀 Swapping {from_token} -> {to_token} for {len(accounts)} wallet(s)[/green]")
                    
                    for i, account in enumerate(accounts, 1):
                        console.print(f"\n[blue]Wallet {i}/{len(accounts)}[/blue]")
                        process_wallet(console, w3, account, "swap", from_token=from_token, to_token=to_token)
                else:
                    console.print("[red]❌ Invalid selection[/red]")
            
            elif choice == "4":  # Full sequence with auto mode
                console.clear()
                console.print(Panel.fit(
                    "[bold red]⚠️ AUTO MODE WARNING ⚠️[/bold red]\n"
                    "[yellow]This will run continuously unt
