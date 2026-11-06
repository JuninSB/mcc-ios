"""Independent OpenSSL oracle for the actual MonoAesStream class, including fragmented writes and EOF."""
import argparse
import pathlib
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('executable', type=pathlib.Path)
parser.add_argument('--mono', action='store_true')
parser.add_argument('--openssl', default='openssl')
args = parser.parse_args()
key = bytes(range(16))
plain = bytes(range(256)) * 3 + b'MCC-iSH-CFB8-fragmentation'
with tempfile.TemporaryDirectory(prefix='mcc-ish-crypto-') as state:
    directory = pathlib.Path(state)
    key_path, plain_path, cipher_path = [directory / name for name in ['key', 'plain', 'cipher']]
    key_path.write_bytes(key)
    plain_path.write_bytes(plain)
    subprocess.run([args.openssl, 'enc', '-aes-128-cfb8', '-K', key.hex(), '-iv', key.hex(),
                    '-in', str(plain_path), '-out', str(cipher_path)], check=True)
    command = (['mono'] if args.mono else []) + [str(args.executable.resolve())]
    subprocess.run(command + [str(key_path), str(plain_path), str(cipher_path)], check=True, timeout=20)
    print('PASS: MonoAesStream AES-128-CFB8 matches OpenSSL, fragmented writes decrypt correctly, EOF returns -1.')
