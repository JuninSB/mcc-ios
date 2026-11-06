"""Controlled 1.8 endpoint exercising the real MCC executable, no auth bypass on public servers."""
import argparse
import json
import pathlib
import queue
import socket
import struct
import subprocess
import tempfile
import threading
import time
import zlib


def vi(value):
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    return bytes(result + bytes([value]))


def read_vi(stream):
    value = 0
    for shift in range(0, 35, 7):
        b = stream.read(1)
        if not b:
            raise EOFError()
        value |= (b[0] & 127) << shift
        if b[0] < 128:
            return value
    raise ValueError('Invalid VarInt')


def string(value):
    data = value.encode()
    return vi(len(data)) + data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=pathlib.Path)
    parser.add_argument('--mono', action='store_true')
    parser.add_argument('--threshold', type=int, default=1)
    parser.add_argument('--finish', choices=['exit', 'disconnect', 'drop', 'truncated', 'oversize', 'bad-compression'], default='exit')
    args = parser.parse_args()
    command = (['mono'] if args.mono else []) + [str(args.executable.resolve())]
    with socket.socket() as listener, tempfile.TemporaryDirectory(prefix='mcc-ish-test-') as state:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        listener.settimeout(20)
        config = pathlib.Path(state, 'test.ini')
        config.write_text('[Main]\nlogin=PortTest\npassword=-\nserverip=127.0.0.1:%d\nmcversion=1.8.9\nmcforge=false\nconsoletitle=\nsessioncache=none\nminecraftrealms=false\nterrainandmovements=false\n' % listener.getsockname()[1])
        process = subprocess.Popen(command + [str(config), 'BasicIO-NoColor'], cwd=state,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace')
        lines = []
        def capture():
            for line in process.stdout:
                lines.append(line)
        reader = threading.Thread(target=capture, daemon=True)
        reader.start()
        try:
            with listener.accept()[0] as connection:
                connection.settimeout(15)
                stream = connection.makefile('rb')
                def packet(compressed=False):
                    size = read_vi(stream)
                    data = stream.read(size)
                    if len(data) != size:
                        raise EOFError()
                    if compressed:
                        import io
                        frame = io.BytesIO(data)
                        expanded = read_vi(frame)
                        data = frame.read()
                        if expanded:
                            data = zlib.decompress(data)
                            assert len(data) == expanded
                    return data
                def send(data, compressed=False):
                    if compressed:
                        data = vi(len(data)) + zlib.compress(data)
                    connection.sendall(vi(len(data)) + data)
                handshake = packet()
                assert handshake[:2] == b'\x00\x2f', handshake
                assert packet() == b'\x00' + string('PortTest')
                send(b'\x03' + vi(args.threshold))
                send(b'\x02' + string('00000000-0000-0000-0000-000000000001') + string('PortTest'), True)
                # Join game: entity, mode, dimension, difficulty, max players, level type, reduced debug.
                send(b'\x01' + struct.pack('>iBbBB', 1, 0, 0, 1, 10) + string('default') + b'\x00', True)
                send(b'\x02' + string(json.dumps({'text': 'ISH_NETWORK_VERIFIED'})) + b'\x00', True)
                send(b'\x00' + vi(12345), True)
                process.stdin.write('ISH_OUTBOUND_VERIFIED\n')
                process.stdin.flush()
                keepalive = chat = False
                deadline = time.monotonic() + 15
                while not (keepalive and chat) and time.monotonic() < deadline:
                    data = packet(True)
                    keepalive |= data == b'\x00' + vi(12345)
                    chat |= data == b'\x01' + string('ISH_OUTBOUND_VERIFIED')
                assert keepalive and chat, (keepalive, chat)
                if args.finish == 'disconnect':
                    send(b'\x40' + string(json.dumps({'text': 'ISH_DISCONNECT_VERIFIED'})), True)
                elif args.finish == 'drop':
                    connection.shutdown(socket.SHUT_RDWR)
                elif args.finish == 'truncated':
                    connection.sendall(vi(20) + b'\x00')
                    connection.shutdown(socket.SHUT_RDWR)
                elif args.finish == 'oversize':
                    connection.sendall(vi(8 * 1024 * 1024 + 1))
                elif args.finish == 'bad-compression':
                    # The declared expanded size is deliberately larger than actual data.
                    broken = vi(32) + zlib.compress(b'\x00\x01')
                    connection.sendall(vi(len(broken)) + broken)
                if args.finish != 'exit':
                    deadline = time.monotonic() + 8
                    while not any('Not connected to any server' in line for line in lines) and time.monotonic() < deadline:
                        time.sleep(0.05)
                    assert any('Not connected to any server' in line for line in lines), ''.join(lines)
                    if args.finish in ('oversize', 'bad-compression'):
                        assert any('Invalid or oversized network packet' in line for line in lines), ''.join(lines)
                    if args.finish == 'disconnect':
                        assert any('ISH_DISCONNECT_VERIFIED' in line for line in lines), ''.join(lines)
                process.stdin.write('/exit\n')
                process.stdin.flush()
                process.wait(timeout=15)
            reader.join(timeout=2)
            assert any('ISH_NETWORK_VERIFIED' in line for line in lines), ''.join(lines)
            assert process.returncode == 0, (process.returncode, ''.join(lines))
            print(f'PASS: real MCC handshake, login, compressed chat in/out, keepalive, finish={args.finish}.')
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            print(''.join(lines))


if __name__ == '__main__':
    main()
