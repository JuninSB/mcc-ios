"""Real TCP fixture for the protocol-774 login/configuration transport; not a play-session test."""
import argparse
import io
import pathlib
import socket
import subprocess
import zlib
import struct
from ish_network import vi, read_vi, string

parser = argparse.ArgumentParser()
parser.add_argument('executable', type=pathlib.Path)
parser.add_argument('--mono', action='store_true')
args = parser.parse_args()
with socket.socket() as listener:
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    listener.settimeout(10)
    command = (['mono'] if args.mono else []) + [str(args.executable.resolve()), '--modern-session', '127.0.0.1', str(listener.getsockname()[1])]
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        with listener.accept()[0] as connection:
            connection.settimeout(10)
            stream = connection.makefile('rb')
            compressed = False
            def receive():
                size = read_vi(stream)
                raw = stream.read(size)
                assert len(raw) == size
                if compressed:
                    frame = io.BytesIO(raw)
                    expanded = read_vi(frame)
                    raw = frame.read()
                    if expanded:
                        raw = zlib.decompress(raw)
                        assert len(raw) == expanded
                return raw
            def send(raw):
                if compressed:
                    raw = vi(len(raw)) + zlib.compress(raw)
                connection.sendall(vi(len(raw)) + raw)
            handshake = io.BytesIO(receive())
            assert read_vi(handshake) == 0 and read_vi(handshake) == 774
            uuid = bytes.fromhex('00112233445566778899aabbccddeeff')
            assert receive() == b'\0' + string('PortTest') + uuid
            send(b'\x04' + vi(17) + string('test:plugin') + b'data')
            assert receive() == b'\x02' + vi(17) + b'\0'
            send(b'\x05' + string('test:cookie'))
            assert receive() == b'\x04' + string('test:cookie') + b'\0'
            send(b'\x03\0')  # Enable compression with threshold zero.
            compressed = True
            send(b'\x02' + uuid + string('PortTest') + b'\0')
            assert receive() == b'\x03'
            assert receive() == b'\x00' + string('en_US') + bytes([2, 0, 1, 0, 1, 0, 1, 2])
            send(b'\x0e\x01' + string('minecraft') + string('core') + string('1.21.11'))
            assert receive() == b'\x07\0'  # Full registry transfer requested.
            send(b'\x04' + bytes.fromhex('0123456789abcdef'))
            assert receive() == b'\x04' + bytes.fromhex('0123456789abcdef')
            send(b'\x05' + bytes.fromhex('fedcba98'))
            assert receive() == b'\x05' + bytes.fromhex('fedcba98')
            send(b'\x03')
            assert receive() == b'\x03'
            join = struct.pack('>iB', 42, 0) + vi(1) + string('minecraft:overworld')
            join += vi(20) + vi(2) + vi(2) + bytes([0, 1, 0])
            join += vi(0) + string('minecraft:overworld') + struct.pack('>q', 123456)
            join += bytes([0, 255, 0, 0, 0]) + vi(0) + vi(63) + b'\x01'
            send(b'\x30' + join)
            assert receive() == b'\x2b'
            send(b'\x30' + join[:-1] + b'\x00')
            assert receive() == b'\x2b'  # No unsigned message leaked while secure-chat was true.
            chat = io.BytesIO(receive())
            assert read_vi(chat) == 8
            assert chat.read(read_vi(chat)) == b'ISH_CHAT_OUTBOUND'
            timestamp, salt = struct.unpack('>qq', chat.read(16))
            assert timestamp > 0 and salt == 0 and chat.read() == bytes(6)
            assert receive() == b'\x06' + string('version')
            def player_chat(signed):
                signature = b'\x01' + bytes([7]) * 256 if signed else b'\x00'
                sender = b'FixturePlayer'
                return b'\x3f' + vi(0) + uuid + vi(0) + signature + string('player fixture') + bytes(16) + bytes([0, 0, 0, 1]) + b'\x08' + struct.pack('>H', len(sender)) + sender + b'\x00'
            send(player_chat(False))
            send(player_chat(True))
            assert receive() == b'\x05\x01'
            send(player_chat(True))  # A retransmitted signature is not acknowledged twice.
            send(b'\x2b' + bytes.fromhex('fedcba9876543210'))
            assert receive() == b'\x1b' + bytes.fromhex('fedcba9876543210')
            send(b'\x3b' + bytes.fromhex('89abcdef'))
            assert receive() == b'\x2c' + bytes.fromhex('89abcdef')
            say = b'fixture-say'
            server = b'Server'
            send(b'\x21\x08' + struct.pack('>H', len(say)) + say + vi(1) + b'\x08' + struct.pack('>H', len(server)) + server + b'\x00')
            # Unnamed NBT TAG_String followed by isOverlay=false.
            send(b'\x77\x08\x00\x02hi\x00')
            send(b'\x46' + vi(1) + struct.pack('>ddddddffi', 10, 64, 20, 0, 0, 0, 90, 10, 0))
            assert receive() == b'\x00' + vi(1)
            assert receive() == b'\x1e' + struct.pack('>dddffB', 10, 64, 20, 90, 10, 0)
            # Relative XYZ/yaw/pitch flags apply to the previous position.
            send(b'\x46' + vi(2) + struct.pack('>ddddddffi', 1, 2, -1, 0, 0, 0, 5, -5, 31))
            assert receive() == b'\x00' + vi(2)
            assert receive() == b'\x1e' + struct.pack('>dddffB', 11, 66, 19, 95, 5, 0)
            send(b'\x20\x08\x00\x03bye')
            send(vi(0x7fff) + b'\x2a')  # Harness marker after configuration transition.
        output, _ = child.communicate(timeout=10)
        assert child.returncode == 0, (child.returncode, output)
        print('PASS: TCP protocol-774 login/configuration, client settings, Join Game/seaLevel/secure-chat fields, Player Loaded, play controls and NBT text.')
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate()
