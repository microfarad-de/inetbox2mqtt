# Crypto-Class for Strings with bonding the key with the machine.unique_id
#
#
# This modules are using the machine_unique_number for encrypt / decrypt
# So the data is only on the target-system usable
# based on ESP32 Micropython implementation of cryptographic
#
# reference:
# https://pycryptodome.readthedocs.io/en/latest/src/cipher/classic.html#cbc-mode
# https://docs.micropython.org/en/latest/library/ucryptolib.html

import os
from Crypto.Cipher import AES
import uuid

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN_DIR      = f"{PROJECT_ROOT}/html/"

class crypto():
    def encrypt(self, text):
        BLOCK_SIZE = 32
        IV_SIZE = 16
        # Padding plain text with space
        text = text.encode("utf-8")
        pad = BLOCK_SIZE - len(text) % BLOCK_SIZE
        text = text + " ".encode("utf-8")*pad
        key1 = uuid.getnode().to_bytes(6, 'big')
        key = bytearray(b'I_am_32bytes=256bits_key_padding')
        for i in range(len(key1)-1):
            key[i] = key1[i]
            key[len(key)-i-1] = key1[i]
        # Generate iv with HW random generator
        iv = os.urandom(IV_SIZE)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ct_bytes = iv + cipher.encrypt(text)
        return ct_bytes

    # you need only one of this modules
    def decrypt(self, enc_bytes):
        BLOCK_SIZE = 32
        IV_SIZE = 16
        MODE_CBC = 2
        key1 = uuid.getnode().to_bytes(6, 'big')
        key = bytearray(b'I_am_32bytes=256bits_key_padding')
        for i in range(len(key1)-1):
            key[i] = key1[i]
            key[len(key)-i-1] = key1[i]
        # Generate iv with HW random generator
        iv = enc_bytes[:IV_SIZE]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.decrypt(enc_bytes)[IV_SIZE:].strip().decode("utf-8")



class fn_crypto():
    def __init__(self):
        pass

    def fn_write_encrypt(self, f, x):
        cip = crypto()
        x = cip.encrypt(x)
        f.write(len(x).to_bytes(2, 'little'))
        f.write(x)


    def fn_write_eof_encrypt(self, f):
        x=0
        f.write(x.to_bytes(2, 'little'))


    def fn_read_decrypt(self, f):
        cip = crypto()
        x = int.from_bytes(f.read(2), "little")
        if x > 0:
            return cip.decrypt(f.read(x))
        else: return ""


    def fn_read_str_decrypt(self, f, x):
        cip = crypto()
        return cip.decrypt(f.read(x))


    def get_decrypt_key(self, fn, key):
        with open(GEN_DIR + fn, "rb") as f:
            s = self.fn_read_decrypt(f)
            while s != "":
                if s.find(key) > -1:
                    f.close()
                    return s[s.find(":")+1:]
                s = self.fn_read_decrypt(f)
            f.close()
        print('Err in crypto_keys: key not found')
        return ''
