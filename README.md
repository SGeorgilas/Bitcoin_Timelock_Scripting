Βήματα εκτέλεσης
1. Περιβάλλον PowerShell
Ανοίγουμε 2 παράθυρα PowerShell και ορίζουμε σε κάθε ένα:

powershell
Copy
Edit
# paths — προσαρμόστε στα δικά σας:
$daemon  = "C:\Program Files\Bitcoin\daemon"
$conf    = "C:\Program Files\Bitcoin\bitcoin.conf"
$datadir = "C:\Users\Desktop PC\AppData\Local\Bitcoin"

# RPC credentials (όπως στο bitcoin.conf)
$Env:RPC_USER     = 'your_username'
$Env:RPC_PASSWORD = 'your_password'
$Env:RPC_PORT     = '18443'
2. Εκκίνηση bitcoind (1ο παράθυρο)
powershell
Copy
Edit
CD $daemon
./bitcoind -regtest -conf="$conf" -datadir="$datadir"
3. Προετοιμασία CLI (2ο παράθυρο)
powershell
Copy
Edit
CD $daemon
4. Δημιουργία wallet που θα παρακολουθεί τη timelock διεύθυνση
powershell
Copy
Edit
./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -named createwallet wallet_name="timelockwallet" disable_private_keys=false descriptors=false load_on_startup=true
5. Δημιουργία legacy διεύθυνσης
powershell
Copy
Edit
$legacy_addr = ./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet getnewaddress "" "legacy"
6. Λήψη pubkey
powershell
Copy
Edit
$addr_info = ./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet getaddressinfo $legacy_addr | ConvertFrom-Json
$pub_key = $addr_info.pubkey
7. Λήψη WIF private key
powershell
Copy
Edit
$wif_key = ./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet dumpprivkey $legacy_addr
8. Δημιουργία P2SH timelock
powershell
Copy
Edit
$result = python create_timelock_p2sh.py $pub_key 200 | ConvertFrom-Json
$p2sh_address      = $result.p2sh_address
$redeem_script_hex = $result.redeem_script_hex
9. Εισαγωγή της P2SH διεύθυνσης στο wallet
powershell
Copy
Edit
./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet importaddress $p2sh_address "timelock" false false
10. Έλεγχος import
powershell
Copy
Edit
./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet getaddressesbylabel "timelock"
11. Δημιουργία mining διεύθυνσης
powershell
Copy
Edit
$mining_addr = ./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet getnewaddress
12. Mine 101 blocks (maturity των coinbase)
powershell
Copy
Edit
./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  generatetoaddress 101 $mining_addr
13. Στείλτε BTC στο P2SH (παράδειγμα 3 αποστολών)
powershell
Copy
Edit
$txid1 = ./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet sendtoaddress $p2sh_address 5.0
$txid2 = ./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet sendtoaddress $p2sh_address 7.0
$txid3 = ./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet sendtoaddress $p2sh_address 3.0
14. Mine 1 block για επιβεβαίωση
powershell
Copy
Edit
./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" generatetoaddress 1 $mining_addr
15. Έλεγχος UTXOs στη timelock διεύθυνση
powershell
Copy
Edit
./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet listunspent | ConvertFrom-Json
16. Summary σε JSON
powershell
Copy
Edit
$summary = [ordered]@{
  "Legacy_Address"      = $legacy_addr
  "Public_Key"          = $pub_key
  "WIF_Private_Key"     = $wif_key
  "P2SH_Address"        = $p2sh_address
  "Redeem_Script_Hex"   = $redeem_script_hex
  "Mining_Address"      = $mining_addr
  "Transaction_ID_1"    = $txid1
  "Transaction_ID_2"    = $txid2
  "Transaction_ID_3"    = $txid3
} | ConvertTo-Json -Depth 10

Write-Host $summary
17. Εκτέλεση spender script (θα βγάλει Rejected: non-final)
powershell
Copy
Edit
python spend_p2sh_timelock.py `
  --locktime 200 --privkey $wif_key --p2sh $p2sh_address `
  --destination $mining_addr --feerate 1.0
18. Ελέγξτε block height & ξεπεράστε το timelock
powershell
Copy
Edit
./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" getblockcount
# mine +100 blocks
./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  generatetoaddress 100 $mining_addr
19. Rerun spender & mine 1 block
powershell
Copy
Edit
$txid_final = python spend_p2sh_timelock.py `
  --locktime 200 --privkey $wif_key --p2sh $p2sh_address `
  --destination $mining_addr --feerate 1.0

./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" generatetoaddress 1 $mining_addr
20. Επιβεβαίωση τελικής συναλλαγής
powershell
Copy
Edit
./bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" gettransaction $txid_final
