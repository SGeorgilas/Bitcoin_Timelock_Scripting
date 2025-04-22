# Βήματα Εκτέλεσης

## Prerequisites

1. **Bitcoin Core (regtest)**  
   - Εγκαταστήστε το Bitcoin Core και βεβαιωθείτε ότι έχετε ενεργοποιήσει το `regtest` mode.  
   - Στο `~/.bitcoin/bitcoin.conf` βάλτε:
     ```ini
     regtest=1
     server=1
     deprecatedrpc=create_bdb
     maxtxfee=0.01
     fallbackfee=0.001

     [regtest]
     rpcuser=your_username
     rpcpassword=your_password
     rpcport=18443
     ```
2. **Python 3.8+**  
   ```powershell
   pip install -r requirements.txt

3. **Ενεργοποίηση Περιβάλλοντος**:
   - Ενεργοποιήστε το Python περιβάλλον (environment) όπου έχουν εγκατασταθεί οι απαιτούμενες εξαρτήσεις.

4. **Επαναφορά Καταλόγου Regtest (Προαιρετικό)**:
   - Διαγράψτε τον κατάλογο ~/.bitcoin/regtest για να επαναφέρετε την τρέχουσα κατάσταση του blockchain..


## ΒΗΜΑΤΑ ΕΚΤΕΛΕΣΗΣ

### 1. Άνοιγμα δύο παραθύρων PowerShell και ορισμός μεταβλητών
Και στα 2 παράθυρα πρέπει να τρέξουν οι παρακάτω εντολές (αντικαταστήστε με τις δικές σας τιμές):
```sh
$daemon    = "C:\Program Files\Bitcoin\daemon"
$conf      = "C:\Users\<YourUser>\.bitcoin\bitcoin.conf"
$datadir   = "C:\Users\<YourUser>\AppData\Local\Bitcoin\regtest"
$Env:RPC_USER     = 'your_username'
$Env:RPC_PASSWORD = 'your_password'
$Env:RPC_PORT     = '18443'
```

### 2. Εκκίνηση του Bitcoin‐daemon (Window 1)
```sh
cd $daemon
.\bitcoind -regtest -conf="$conf" -datadir="$datadir"
```

### 3. Προετοιμασία Wallet & Διευθύνσεων (Window 2)
#### 3.1 Δημιουργία wallet

```sh
cd $daemon
bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -named createwallet wallet_name="timelockwallet" disable_private_keys=false descriptors=false load_on_startup=true
```
#### 3.2 Δημιουργία Legacy address

```sh
$legacy_addr = bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet getnewaddress "" legacy
```

#### 3.3 Λήψη pubkey & WIF

```sh
$addr_info = bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet getaddressinfo $legacy_addr | ConvertFrom-Json
$pubkey    = $addr_info.pubkey
$wif_key   = bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet dumpprivkey $legacy_addr
```


### 4. Εξόρυξη 101 blocks (maturity)

```sh
$mining_addr = bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet getnewaddress
bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" generatetoaddress 101 $mining_addr
```

### 5. Δημιουργία Timelocked P2SH (Script #1)

```sh
$result = python create_timelock_p2sh.py $pubkey 200 | ConvertFrom-Json
$p2sh_address      = $result.p2sh_address
$redeem_script_hex = $result.redeem_script_hex
```

### 6. Import P2SH Address στο wallet

```sh
bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet importaddress $p2sh_address "timelock" false false
```

### 7. Έλεγχος εισαγωγής

```sh
bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet getaddressesbylabel "timelock"
```


### 8.  Χρηματοδότηση P2SH (3 αποστολές)

```sh
$txid1 = bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet sendtoaddress $p2sh_address 0.3
$txid2 = bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet sendtoaddress $p2sh_address 0.7
$txid3 = bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet sendtoaddress $p2sh_address 0.5

# Επιβεβαίωση
bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" generatetoaddress 1 $mining_addr
```

### 9. Έλεγχος UTXOs

```sh
bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" `
  -rpcwallet=timelockwallet listunspent | ConvertFrom-Json
```

### 10. Προσθήκη σε Summary Variable

```sh
$summary = [ordered]@{
  Legacy_Address      = $legacy_addr
  Public_Key          = $pubkey
  WIF_Private_Key     = $wif_key
  P2SH_Address        = $p2sh_address
  Redeem_Script_Hex   = $redeem_script_hex
  Mining_Address      = $mining_addr
  Transaction_ID_1    = $txid1
  Transaction_ID_2    = $txid2
  Transaction_ID_3    = $txid3
} | ConvertTo-Json -Depth 10

Write-Host $summary
```


### 11. Προσπάθεια spending πριν το locktime (Script #2)

```sh
python spend_p2sh_timelock.py `
  --locktime 200 `
  --privkey $wif_key `
  --p2sh $p2sh_address `
  --destination $mining_addr `
  --feerate 1.0
# Θα δείτε: Rejected: non-final
```

### 12. Έλεγχος τρέχοντος block height

```sh
bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" getblockcount
```

## 13. Εξόρυξη +100 blocks (ξεπερνάμε το locktime)

```sh
bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" generatetoaddress 100 $mining_addr
```

## 14. Spending μετά το locktime

```sh
$txid_final = python spend_p2sh_timelock.py `
  --locktime 200 `
  --privkey $wif_key `
  --p2sh $p2sh_address `
  --destination $mining_addr `
  --feerate 1.0
```

## 15. Επιβεβαίωση broadcast & mining

```sh
bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" generatetoaddress 1 $mining_addr
bitcoin-cli -regtest -conf="$conf" -datadir="$datadir" gettransaction $txid_final
```

## Notes
- Μην χρησιμοποιείτε αυτά τα scripts σε mainnet!
- Προσαρμόστε ποσά, locktimes, fee‑rates κατά βούληση.
- Όλα τα raw TX, errors, bump‑fee logs εμφανίζονται στο stderr των Python scripts.

##License & Acknowledgments##

This code is provided for educational purposes as part of the Decentralized Technologies course at AUTh.
Feel free to adapt and improve.
