"""Package the native/CoreLib bootstrap probe, never the MCC application."""
import argparse
import hashlib
import io
from pathlib import Path
import tarfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime-source', type=Path, required=True)
parser.add_argument('--native-build', type=Path, required=True)
parser.add_argument('--probe', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--debug-symbols', action='store_true')
args = parser.parse_args()
files = {
    'mono-sgen': args.native_build / 'mono/mini/mono-sgen',
    'System.Private.CoreLib.dll': args.runtime_source / 'artifacts/bin/mono/linux.x86.Release/System.Private.CoreLib.dll',
    'System.Runtime.dll': args.runtime_source / 'artifacts/bin/System.Runtime/Release/net10.0/System.Runtime.dll',
    'MinimalProbe.dll': args.probe,
    'LICENSE.TXT': args.runtime_source / 'LICENSE.TXT',
    'THIRD-PARTY-NOTICES.TXT': args.runtime_source / 'THIRD-PARTY-NOTICES.TXT',
}
for library in args.native_build.rglob('*.so'):
    if library.name in files:
        parser.error('Duplicate native library basename: ' + library.name)
    files[library.name] = library
if args.debug_symbols:
    for symbols in (args.native_build / 'mono/mini').glob('*.dbg'):
        files[symbols.name] = symbols
for name, path in files.items():
    if not path.is_file():
        parser.error('Missing probe input: ' + str(path))
args.output.parent.mkdir(parents=True, exist_ok=True)
checksums = []
with tarfile.open(args.output, 'w:gz') as archive:
    for name, path in sorted(files.items()):
        data = path.read_bytes()
        checksums.append(hashlib.sha256(data).hexdigest() + '  ' + name)
        entry = tarfile.TarInfo(name)
        entry.size = len(data)
        entry.mode = 0o755 if name == 'mono-sgen' or name.endswith('.so') else 0o644
        archive.addfile(entry, io.BytesIO(data))
    data = ('\n'.join(checksums) + '\n').encode('ascii')
    entry = tarfile.TarInfo('SHA256SUMS')
    entry.size = len(data)
    archive.addfile(entry, io.BytesIO(data))
with args.output.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
args.output.with_suffix(args.output.suffix + '.sha256').write_text(
    digest + '  ' + args.output.name + '\n', encoding='ascii', newline='\n')
print('PACKAGED_BOOTSTRAP_PROBE', args.output, digest)
