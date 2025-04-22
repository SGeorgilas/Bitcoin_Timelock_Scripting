import sys, os, argparse
from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy
from bitcoinutils.setup import setup
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
from bitcoinutils.keys import PrivateKey, P2pkhAddress, P2wpkhAddress
from bitcoinutils.script import Script
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_der_canonize


# Βοηθητική συνάρτηση για debug εκτυπώσεις στο stderr
def debug(*a, **k):
    print(*a, file=sys.stderr, **k)


# Ανάλυση ορισμάτων γραμμής εντολών
def parse_args():
    p = argparse.ArgumentParser(description='Spend all funds from a timelocked P2SH on regtest')
    p.add_argument('--locktime',   type=int,   required=True, help='Absolute locktime (block height or epoch)')
    p.add_argument('--privkey',    required=True, help='WIF private key to unlock P2SH')
    p.add_argument('--p2sh',       required=True, help='P2SH address holding the funds')
    p.add_argument('--destination',required=True, help='Destination address (P2PKH or P2WPKH)')
    p.add_argument('--feerate',    type=float, default=1.0, help='Fee rate in sat/vbyte')
    return p.parse_args()


# Εκτίμηση μέγιστου μεγέθους συναλλαγής (vbytes)
def estimate_tx_size(n_in, n_out):
    return 10 + n_in*148 + n_out*34



def main():
    args = parse_args()

    # --- 1) Σύνδεση στο RPC ---
    user = os.getenv('RPC_USER'); pwd = os.getenv('RPC_PASSWORD')
    if not user or not pwd:
        debug("FATAL: set RPC_USER/RPC_PASSWORD"); sys.exit(1)
    rpc = AuthServiceProxy(f'http://{user}:{pwd}@127.0.0.1:18443')
    setup('regtest')  # Ρύθμιση για regtest περιβάλλον
    debug("RPC_URL =", rpc._AuthServiceProxy__service_url)

    # --- 2) Ανάκτηση UTXOs ---
    utxos = rpc.listunspent(0,9999999,[args.p2sh])
    if not utxos:
        debug("No UTXOs at", args.p2sh); sys.exit(1)
    debug(f"DEBUG fetched {len(utxos)} UTXOs")

    # Συλλογή inputs και άθροιση συνολικού ποσού
    inputs = []; total = Decimal('0')
    for u in utxos:
        inputs.append((u['txid'],u['vout'],Decimal(str(u['amount']))))
        total += Decimal(str(u['amount']))
    debug("DEBUG total BTC available =", total)

    # --- 3) Δημιουργία redeem script ---
    priv = PrivateKey(args.privkey); pub = priv.get_public_key()
    redeem = Script([
        args.locktime,
        'OP_CHECKLOCKTIMEVERIFY','OP_DROP',
        'OP_DUP','OP_HASH160', pub.get_address().to_hash160(),
        'OP_EQUALVERIFY','OP_CHECKSIG'
    ])
    redeem_hex = redeem.to_hex()
    debug("DEBUG redeem script hex =", redeem_hex)

    # --- 4) Προετοιμασία scriptPubKey προορισμού ---
    dest = args.destination
    is_segwit = dest.startswith('bcrt1')
    dest_spk = P2wpkhAddress(dest).to_script_pub_key() if is_segwit else P2pkhAddress(dest).to_script_pub_key()

    # --- Συνάρτηση κατασκευής και υπογραφής TX ---
    def build_and_sign(fee_sats):
        fee_btc = Decimal(fee_sats)/Decimal('1e8')
        send_amt = total - fee_btc
        if send_amt <= 0:
            debug("Fee too high"); sys.exit(1)
        out_sats = int(send_amt * Decimal('1e8'))

        # Δημιουργία εισόδων
        txins = []
        for txid,vout,_ in inputs:
            ti = TxInput(txid,vout)
            ti.sequence = (0).to_bytes(4,'little')
            txins.append(ti)

        # Δημιουργία εξόδου
        txout = TxOutput(out_sats, dest_spk)
        lt_bytes = args.locktime.to_bytes(4,'little')
        tx = Transaction(txins,[txout],locktime=lt_bytes)

        # Υπογραφή κάθε input
        for i in range(len(tx.inputs)):
            h = tx.get_transaction_digest(i, redeem)
            sk = SigningKey.from_string(priv.key.to_string(),curve=SECP256k1)
            der = sk.sign_digest(h, sigencode=sigencode_der_canonize)+b'\x01'
	    # scriptSig κατασκευάζεται με [sig, pubkey, redeem]
            tx.inputs[i].script_sig = Script([der.hex(), pub.to_hex(), redeem_hex])

        return tx, tx.serialize(), tx.get_txid()

    # --- 5) Πρώτη απόπειρα με βασική προμήθεια ---
    sz = estimate_tx_size(len(inputs),1)
    base_fee = int(args.feerate * sz)
    debug(f"Signing with fee={base_fee} sats (est size={sz})…")
    tx, raw, txid = build_and_sign(base_fee)
    debug("Raw signed TX:", raw)


    # Έλεγχος αποδοχής στο mempool
    res = rpc.testmempoolaccept([raw])[0]
    debug("testmempoolaccept ->", res)
    if res.get('allowed'):
        rpc.sendrawtransaction(raw)
        print(txid)
        return

    # --- 6) Bumping fee αν χρειάζεται ---
    if 'min relay fee' in res.get('reject-reason',''):
        want = int(res['reject-details'].split('<')[1])
        debug(f"Bumping to {want} sats…")
        tx, raw, txid = build_and_sign(want)
        debug("Raw bumped TX:", raw)
        res2 = rpc.testmempoolaccept([raw])[0]
        debug("after bump ->", res2)
        if res2.get('allowed'):
            rpc.sendrawtransaction(raw)
            print(txid)
            return
        debug("Still rejected:", res2.get('reject-reason'))
    else:
        debug("Rejected:", res.get('reject-reason'))
    sys.exit(1)

if __name__=='__main__':
    main()
