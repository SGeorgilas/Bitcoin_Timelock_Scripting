import sys
import json  # Χρησιμοποιείται για να τυπώσουμε το αποτέλεσμα σε JSON
from bitcoinutils.setup import setup
from bitcoinutils.keys import P2shAddress, PublicKey
from bitcoinutils.script import Script

def main():
    # Ρύθμιση για το local regtest δίκτυο
    setup("regtest")


    # Έλεγχος ορθής κλήσης
    if len(sys.argv) < 3:
        print("Usage: python create_timelock_p2sh.py <pubkey> <absolute_locktime>")
        return

    # Πρώτο όρισμα: hex του δημοσίου κλειδιού
    pubkey_hex = sys.argv[1]
    
    # Δεύτερο όρισμα: απόλυτο locktime (block height ή unix epoch)
    locktime = int(sys.argv[2])


    # Δημιουργούμε το αντικείμενο PublicKey από το hex
    pubkey = PublicKey(pubkey_hex)


    # Κατασκευή του redeem script με timelock + P2PKH
    redeem_script = Script([
        locktime,                             #Προώθηση του αριθμού locktime στο stack
        "OP_CHECKLOCKTIMEVERIFY",             #Έλεγχος προυπόθεσης locktime του transaction
        "OP_DROP",                            #Αφαίρεση locktime από το stack, για να μην μείνει μετά τον έλεγχο
        "OP_DUP",                             #Αντιγραφή του επόμενου στοιχείου του stack, (το δημ.κλειδί) προς υπογραφή
        "OP_HASH160",                         #Υπολογισμός SHA-256, μετά RIPEMD-160 του δημ.κλειδιού, φέρνοντας το hash160 του
        pubkey.get_address().to_hash160(),    #Προώθηση στο stack του αναμενόμενου hash160 του δημ.κλειδιού που είχε δοθεί αρχικά
        "OP_EQUALVERIFY",                     #Σύγκριση των δύο hash160, αν δεν είναι ίσα απορρίπτεται, αν είναι ίσα αφαιρούνται από το stack
        "OP_CHECKSIG"                         #Έλεγχος υπογραφής στο scriptsig για το αν είναι έγκυρη για το δημ.κλειδί.
    ])
    
    # Παράγωγή P2SH διεύθυνσης από το redeem script
    p2sh = P2shAddress.from_script(redeem_script)

    # Προετοιμασία του JSON
    result = {
        "p2sh_address": p2sh.to_string(),   # Η P2SH διεύθυνση
        "redeem_script_hex": redeem_script.to_hex(),  # Το redeem script σε hex
        "pubkey": pubkey.to_hex()     # Το δημόσιο κλειδί σε hex
    }

    # Εκτύπωση του JSON στο stdout
    print(json.dumps(result))  

if __name__ == '__main__':
    main()