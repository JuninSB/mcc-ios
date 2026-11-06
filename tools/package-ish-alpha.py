"""Package the tested partial console as an explicit alpha, never a full MCC release."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
parser.add_argument('--version', default='alpha.1')
parser.add_argument('--source-commit', required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
output = Path(args.output).resolve()
output.mkdir(parents=True, exist_ok=True)
name = 'mcc-ish-console-' + args.version
files = {}
binary_dir = root / 'ports/ish/MinecraftClient/bin/Release'
for file in ['MinecraftClient.exe', 'MinecraftClient.exe.config']:
    files['ports/ish/MinecraftClient/bin/Release/' + file] = (binary_dir / file).read_bytes()
for source, destination in [('run.sh', 'launcher.sh'), ('install.sh', 'install.sh'), ('LICENSE.md', 'LICENSE.md'), ('scripts/diagnose-ish.sh', 'scripts/diagnose-ish.sh')]:
    files[destination] = (root / source).read_bytes().replace(b'\r\n', b'\n')
for license_file in (root / 'ports/ish/licenses').iterdir():
    if license_file.is_file():
        files['licenses/' + license_file.name] = license_file.read_bytes()
files['licenses/README.md'] = files['licenses/README.md'].replace(b'../../../LICENSE.md', b'../LICENSE.md')
files['run.sh'] = b'''#!/bin/sh
set -eu
umask 077
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v mono >/dev/null 2>&1 || [ ! -f "$project_dir/.runtime-ready" ]; then
    sh "$project_dir/install.sh"
    touch "$project_dir/.runtime-ready"
fi
exec sh "$project_dir/launcher.sh" "$@"
'''
readme = '''# MCC para iSH: console alpha de teste

ESTA BUILD E PARCIAL. NAO E O PORTE COMPLETO DO MCC.

Alvo: Alpine Linux x86 de 32 bits, Mono. Validado em Alpine 3.22.8/Mono 6.14.1
sob QEMU. Ainda nao validado no iSH real nem com login Microsoft bem-sucedido.
Nao precisa instalar .NET 10 no iPhone. O executavel ja esta compilado.

Descompacte, entre nesta pasta e execute:

    sh run.sh --mcversion=1.21.11 --serverip=ENDERECO:25565

Primeira execucao instala Mono/certificados pelo apk, se disponiveis, e sincroniza
os certificados do Mono. Precisa de acesso root para instalar pacotes ausentes.
O repositorio community deve estar habilitado para a MESMA versao do Alpine.
Nao misture repositorios de versoes diferentes nem desative validacao TLS.

Login Microsoft: abra o link mostrado no Safari, autentique e cole o codigo ou
URL de retorno. Nunca digite sua senha Microsoft no terminal. Login real ainda
precisa de validacao. Para teste offline, use somente seu servidor controlado e
as opcoes --login=PortTest --password=-. Isso nao autentica uma conta premium.

Funciona nos testes 1.21.11: entrada, chat/comandos, mensagens de sistema e /exit.
Ausentes no caminho 1.21.11: minimapa/TUI moderna, inventario, mundo/movimento,
bots modernos, reconexao automatica e assinatura de chat. Servidores que exigem
assinatura nao permitem envio pelo caminho atual. Recursos da base antiga ate
1.18.2 existem, mas nao foram todos validados. Nenhuma afirmacao de porte 100%.

Configuracao/tokens ficam em ~/.config/mcc-ish; nao compartilhe SessionCache.ini.
O iOS pode suspender o cliente em segundo plano; mantenha iSH em primeiro plano.

Diagnostico: sh scripts/diagnose-ish.sh
Sair: /exit
Se o setup falhar, corrija o erro e execute sh run.sh novamente.
Para repetir sincronizacao de certificados: sh install.sh.
Para recompilar, obtenha o repositorio fonte; esta distribuicao contem binario.

Confira SHA256SUMS antes de executar. BUILD.json identifica fonte e compilacao.
Fonte: https://github.com/JuninSB/mcc-ios/tree/ish-port
'''
files['LEIA-ME.md'] = readme.encode('utf-8')
metadata = {
    'version': args.version, 'status': 'partial-console-alpha',
    'sourceCommit': args.source_commit,
    'sourceUrl': 'https://github.com/JuninSB/mcc-ios/tree/' + args.source_commit,
    'portSourceTree': subprocess.check_output(['git', 'rev-parse', 'HEAD:ports/ish'], cwd=root, text=True).strip(),
    'buildSdk': subprocess.check_output(['dotnet', '--version'], text=True).strip(),
    'buildCommand': 'dotnet build ports/ish/MinecraftClient/Build.csproj -c Release -p:ContinuousIntegrationBuild=true -p:Deterministic=true',
    'targetFramework': 'net40', 'architecture': 'x86', 'runtime': 'Mono',
    'validatedEnvironment': 'Alpine 3.22.8 x86 / Mono 6.14.1 under QEMU',
    'validatedOnIOS': False, 'fullModernMccPort': False,
    'binarySha256': hashlib.sha256(files['ports/ish/MinecraftClient/bin/Release/MinecraftClient.exe']).hexdigest(),
}
files['BUILD.json'] = (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode()
files['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + path + '\n' for path, data in sorted(files.items())).encode()
with tarfile.open(output / (name + '.tar.gz'), 'w:gz') as archive:
    for path, data in sorted(files.items()):
        entry = tarfile.TarInfo(name + '/' + path)
        entry.size = len(data)
        entry.mode = 0o755 if path.endswith('.sh') else 0o644
        archive.addfile(entry, io.BytesIO(data))
with zipfile.ZipFile(output / (name + '.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
    for path, data in sorted(files.items()):
        entry = zipfile.ZipInfo(name + '/' + path)
        entry.external_attr = (0o100755 if path.endswith('.sh') else 0o100644) << 16
        entry.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(entry, data)
archives = [output / (name + suffix) for suffix in ('.tar.gz', '.zip')]
(output / 'SHA256SUMS').write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n' for path in archives), encoding='utf-8')
for path in archives: print(path)
