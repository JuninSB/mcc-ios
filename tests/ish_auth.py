"""Exercise actual browser OAuth prompt and remote rejection, without any account secrets."""
import argparse
import pathlib
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('executable', type=pathlib.Path)
parser.add_argument('--mono', action='store_true')
parser.add_argument('--corrupt-cache', action='store_true')
args = parser.parse_args()
command = (['mono'] if args.mono else []) + [str(args.executable.resolve())]
with tempfile.TemporaryDirectory(prefix='mcc-ish-auth-') as state:
    config = pathlib.Path(state, 'test.ini')
    config.write_text('[Main]\nlogin=\npassword=\nconsoletitle=\nsessioncache=none\n[Logging]\ndebugmessages=true\n')
    if args.corrupt_cache:
        config.write_text('[Main]\nlogin=PortTest\npassword=\nconsoletitle=\nsessioncache=disk\n[Logging]\ndebugmessages=true\n')
        pathlib.Path(state, 'SessionCache.ini').write_text('porttest=a.b.c,PortTest,' + '0' * 32 + ',' + '1' * 32 + ',\nINVALID_SECRET_CACHE_LINE\n')
    process = subprocess.Popen(command + [str(config), 'BasicIO-NoColor'], cwd=state,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding='utf-8', errors='replace')
    try:
        output, _ = process.communicate('deliberately-invalid-authorization-code\n', timeout=35)
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate()
    assert 'Never enter your password here' in output, output
    assert 'Microsoft sign-in failed:' in output, output
    assert 'login.microsoftonline.com' in output, output
    assert 'AADSTS' in output or 'invalid_grant' in output, 'No remote Microsoft OAuth rejection observed: ' + output
    assert 'deliberately-invalid-authorization-code' not in output, 'OAuth code leaked into debug output'
    assert 'INVALID_SECRET_CACHE_LINE' not in output and 'a.b.c,PortTest' not in output, 'Cached credentials leaked'
    assert 'Password:' not in output, output
    assert 'Unhandled Exception' not in output and 'System.InvalidOperationException' not in output, output
    assert process.returncode == 1, (process.returncode, output)
    print('PASS: browser OAuth prompt, no password request, failed token exchange reported.')
    print(output)
