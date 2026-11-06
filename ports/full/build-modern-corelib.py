"""Build pinned Mono CoreLib or shared libraries for Linux/musl x86 on a build host.

This requires an installed .NET SDK on the build host. It does not install an SDK
on iSH, execute a downloaded bootstrap script, or build a complete runtime/client.
Use the unmodified runtime source archive documented in MODERN-MONO.md.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('runtime_source', type=Path)
parser.add_argument('--dotnet', default='dotnet')
parser.add_argument('--libraries', action='store_true', help='Build the complete managed shared-framework libraries after CoreLib')
args = parser.parse_args()
source = args.runtime_source.resolve()
project = source / ('src/libraries/sfx.proj' if args.libraries else 'src/mono/System.Private.CoreLib/System.Private.CoreLib.csproj')
if not project.is_file():
    parser.error('runtime_source must contain the selected upstream runtime project')

# Recent MSBuild uses the SDK directory to launch .NET task hosts. The runtime
# repo overrides RuntimeIdentifierGraphPath, so MSBuild's SDK-10 fallback would
# otherwise mistake the source directory for an SDK directory.
sdk_version = subprocess.check_output([args.dotnet, '--version'], cwd=source, text=True).strip()
sdk_lines = subprocess.check_output([args.dotnet, '--list-sdks'], cwd=source, text=True).splitlines()
sdk_line = next((line for line in sdk_lines if line.startswith(sdk_version + ' [')), None)
if not sdk_line:
    sys.exit('Could not locate the active SDK directory from dotnet --list-sdks.')
sdk_directory = Path(sdk_line[len(sdk_version) + 2:-1]) / sdk_version
if not (sdk_directory / 'MSBuild.dll').is_file():
    sys.exit('The resolved SDK directory does not contain MSBuild.dll.')

command = [
    args.dotnet, 'build', str(project), '-c', 'Release', '--nologo',
    '--disable-build-servers', '-maxcpucount:1', '-nodeReuse:false',
    '-p:TargetOS=linux', '-p:TargetArchitecture=x86',
    # Generators/analyzers run inside the host's x64 compiler. Their IL must
    # remain AnyCPU even though CoreLib's target-specific constants select x86.
    '-p:PlatformTarget=AnyCPU',
    f'-p:NetCoreSdkRoot={sdk_directory}',
    '-p:RuntimeFlavor=Mono', '-p:__PortableTargetOS=linux-musl',
    '-p:CrossBuild=true', '-p:EnableSourceControlManagerQueries=false',
    '-p:SourceRevisionId=60629d14374c56f1cb51819049ad1fa529307f8d',
]
if not args.libraries:
    # Changing architecture alone can leave incompatible analyzer DLLs cached.
    command.append('--no-incremental')
result = subprocess.run(command, cwd=source)
if result.returncode:
    sys.exit(result.returncode)
if args.libraries:
    library_dir = source / 'artifacts/bin/microsoft.netcore.app.runtime.linux-musl-x86/Release/runtimes/linux-musl-x86/lib/net10.0'
    required = ['System.Runtime.dll', 'System.Console.dll', 'System.Net.Http.dll',
                'System.Security.Cryptography.dll', 'System.Text.Json.dll', 'System.Collections.dll']
    missing = [name for name in required if not (library_dir / name).is_file()]
    if missing:
        sys.exit('Shared-framework build returned zero but required output is absent: ' + ', '.join(missing))
    print('MCC_MODERN_LIBRARIES_BUILD_PASS', library_dir)
    print('Managed libraries compilation only. Native shims and runtime/client execution remain unverified.')
    sys.exit(0)
assembly = source / 'artifacts/bin/mono/linux.x86.Release/System.Private.CoreLib.dll'
if not assembly.is_file():
    sys.exit('Build returned zero but the expected Linux x86 CoreLib is absent.')
print('MCC_MODERN_CORELIB_BUILD_PASS', assembly)
print('SHA256', hashlib.sha256(assembly.read_bytes()).hexdigest())
print('CoreLib compilation only. Execution and full runtime/MCC compatibility are unverified.')
