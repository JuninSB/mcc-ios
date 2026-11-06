"""Experimental Windows-host native Mono build for Linux/musl x86.

Uses the pinned source/tools in MODERN-MONO.md. No host installer or VM is used.
This does not build library shims, a complete distribution, or the MCC client.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('runtime_source', type=Path)
parser.add_argument('--tools-dir', type=Path, required=True)
parser.add_argument('--binutils-dir', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--dotnet', default='dotnet')
parser.add_argument('--jobs', type=int, default=1)
parser.add_argument('--configure-only', action='store_true')
parser.add_argument('--log-file', type=Path, help='Append complete tool output to a local build log')
args = parser.parse_args()
if os.name != 'nt' or args.jobs < 1:
    parser.error('This experiment requires Windows and a positive job count.')
source = args.runtime_source.resolve()
tools_dir = args.tools_dir.resolve()
output = args.output.resolve()
binutils = args.binutils_dir.resolve()
if not (source / 'src/mono/mono.proj').is_file():
    parser.error('runtime_source must contain the pinned dotnet/runtime source.')
manifest = json.loads(Path(__file__).with_name('cross-tools.json').read_text(encoding='utf-8'))
executables = {}
for name, spec in manifest.items():
    archive = tools_dir / spec['archive']
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != spec['sha256']:
        sys.exit('Tool archive checksum mismatch: ' + name)
    executable = tools_dir / spec['executable']
    if not executable.is_file():
        sys.exit('Extract the verified tool archive before building: ' + name)
    executables[name] = executable
environment = os.environ.copy()
for tool in ['ar', 'nm', 'ranlib', 'strings', 'objdump', 'readelf', 'objcopy', 'ld']:
    executable = binutils / (tool + '.exe')
    if not executable.is_file():
        sys.exit('Missing GNU binutils tool: ' + str(executable))
    environment['CLR_' + ('LINK' if tool == 'ld' else tool.upper())] = str(executable)

def run(command):
    print('Running', Path(str(command[0])).name, flush=True)
    if args.log_file:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        with args.log_file.open('a', encoding='utf-8') as log:
            completed = subprocess.run([str(part) for part in command], cwd=source, env=environment,
                                       stdout=log, stderr=subprocess.STDOUT)
    else:
        completed = subprocess.run([str(part) for part in command], cwd=source, env=environment)
    if completed.returncode:
        if args.log_file:
            print('\n'.join(args.log_file.read_text(encoding='utf-8', errors='replace').splitlines()[-60:]))
        sys.exit(completed.returncode)

# Standalone CMake generates files according to the host OS, leaving Linux's
# _version.c absent on Windows. Generate both formats using upstream targets.
version_command = [args.dotnet, 'msbuild', source / 'src/mono/mono.proj', '-nologo',
                   '-nodeReuse:false', '-p:Configuration=Release', '-p:TargetOS=linux',
                   '-p:TargetArchitecture=x86', '-p:RuntimeFlavor=Mono',
                   '-p:__PortableTargetOS=linux-musl', '-p:CrossBuild=true',
                   '-p:EnableSourceControlManagerQueries=false',
                   '-p:SourceRevisionId=60629d14374c56f1cb51819049ad1fa529307f8d']
run(version_command + ['-t:GenerateRuntimeVersionFile'])
run(version_command + ['-t:GenerateNativeVersionFile', '-p:OS=Unix',
                       '-p:NativeVersionFile=' + (source / 'artifacts/obj/_version.c').as_posix()])
output.mkdir(parents=True, exist_ok=True)
toolchain = output / 'zig-x86-musl.cmake'
zig = executables['zig'].as_posix()
lines = ['set(CMAKE_SYSTEM_NAME Linux)', 'set(CMAKE_SYSTEM_PROCESSOR x86)']
for language, driver in [('C', 'cc'), ('CXX', 'c++'), ('ASM', 'cc')]:
    lines.extend([f'set(CMAKE_{language}_COMPILER "{zig}")',
                  f'set(CMAKE_{language}_COMPILER_ARG1 {driver})',
                  f'set(CMAKE_{language}_COMPILER_TARGET x86-linux-musl)'])
toolchain.write_text('\n'.join(lines) + '\n', encoding='utf-8')
run([executables['cmake'], '-S', source / 'src/mono', '-B', output, '-G', 'Ninja',
     '-DCMAKE_MAKE_PROGRAM=' + executables['ninja'].as_posix(),
     '-DCMAKE_TOOLCHAIN_FILE=' + toolchain.as_posix(),
     '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_INSTALL_PREFIX=/usr/local',
     # Zig defaults to static musl executables. Mono must dlopen components
     # and native library shims, which musl's static dlopen stub cannot do.
     # Components link libmonosgen too. Export the executable's initialized
     # runtime APIs/state so ELF symbol interposition does not use a second,
     # uninitialized copy (confirmed by the EventPipe bootstrap backtrace).
     '-DCMAKE_EXE_LINKER_FLAGS=-dynamic -Wl,--export-dynamic',
     '-DCLR_CMAKE_HOST_ARCH=x86', '-DCLR_CMAKE_TARGET_ARCH=x86',
     '-DCLR_CMAKE_HOST_OS=linux', '-DCLR_CMAKE_TARGET_OS=linux',
     '-DCLR_CMAKE_TARGET_UNIX=1', '-DCLR_CMAKE_HOST_LINUX_MUSL=1',
     '-DCLR_CMAKE_TARGET_LINUX_MUSL=1', '-DCLR_CMAKE_USE_SYSTEM_ZLIB=0',
     '-DENABLE_LLVM_RUNTIME=OFF'])
print('MCC_MODERN_MONO_CROSS_CONFIGURE_PASS', flush=True)
if args.configure_only:
    sys.exit(0)
run([executables['cmake'], '--build', output, '--parallel', args.jobs])
binary = output / 'mono/mini/mono-sgen'
with binary.open('rb') as stream:
    header = stream.read(52)
    if len(header) != 52 or header[:6] != b'\x7fELF\x01\x01' or int.from_bytes(header[18:20], 'little') != 3:
        sys.exit('Native build did not produce the expected little-endian x86 ELF32 executable.')
    ph_offset = int.from_bytes(header[28:32], 'little')
    ph_size = int.from_bytes(header[42:44], 'little')
    ph_count = int.from_bytes(header[44:46], 'little')
    interpreter = None
    if ph_size != 32 or ph_count > 512:
        sys.exit('Unexpected ELF program-header table.')
    for index in range(ph_count):
        stream.seek(ph_offset + ph_size * index)
        program_header = stream.read(ph_size)
        if int.from_bytes(program_header[:4], 'little') == 3:  # PT_INTERP
            stream.seek(int.from_bytes(program_header[4:8], 'little'))
            interpreter = stream.read(min(int.from_bytes(program_header[16:20], 'little'), 1024)).rstrip(b'\0')
    if interpreter != b'/lib/ld-musl-i386.so.1':
        sys.exit('Mono needs the Alpine x86 dynamic loader for native shims/components; static PIE is insufficient.')
exports = subprocess.check_output([str(binutils / 'nm.exe'), '-D', str(binary)], text=True, env=environment)
for symbol in ['mono_get_corlib', 'mono_metadata_signature_alloc']:
    if not any(line.split()[-1:] == [symbol] and ' U ' not in line for line in exports.splitlines()):
        sys.exit('The standalone runtime must export its APIs for dynamic components: ' + symbol)
print('MCC_MODERN_MONO_CROSS_NATIVE_BUILD_PASS', binary)
print('Execution, library shims and full runtime/client compatibility remain unverified.')
