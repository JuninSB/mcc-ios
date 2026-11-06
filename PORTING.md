# iSH port: engineering and verification

## Strategy and compatibility assessment

Use upstream `previous` commit b3cc2351ee14d8e4fadc6f0e6115478872143c48,
which targets .NET Framework 4.0 and implements protocols 1.4.6 through 1.18.2.
The modern root application targets net10.0; its Roslyn, Consolonia/Avalonia,
Magick.NET, Sentry and other modern dependencies cannot simply be retargeted to Mono.
The imported runtime has no NuGet runtime dependencies. Its C# protocol, DNS,
JSON parser, managed BouncyCastle AES subset and DotNetZip compression are retained.
RSA/SHA1 use framework crypto; HTTP authentication uses SslStream with TLS 1.2
and certificate validation. Microsoft browser authorization, Xbox Live/XSTS,
ownership, profile and join-session calls remain real upstream implementations.

Native requirements are Mono, musl, zlib and TLS support supplied by Alpine's Mono
package. Windows clipboard/icon helpers remain compiled but BasicIO and disabled
icon settings avoid them in normal iSH operation. Advanced terminal editing is not used.
Mono scripting remains present, but runtime compilation and every bot require separate testing.
The old command dispatcher remains intact; modern Brigadier features are not backported.
Configuration uses the historical embedded INI template and private per-user working directory.

Sources:
* https://github.com/ish-app/ish/wiki/FAQ (32-bit emulator and incomplete syscall coverage)
* https://pkgs.alpinelinux.org/package/v3.22/community/x86/mono (Mono 6.14.1, x86)
* https://github.com/MCCTeam/Minecraft-Console-Client/tree/b3cc2351ee14d8e4fadc6f0e6115478872143c48

## Changes

* POSIX launch/install scripts, dependency availability checks and private state directory.
* Browser OAuth enforced so no Microsoft password prompt is used. Accept pasted redirect URL.
* Escape OAuth code and refresh-token form parameters; report token exchange errors.
* Remove access-token debug output and unnecessary token file watcher (inotify).
* Handle BasicIO failure paths without Console.KeyAvailable; handle stdin EOF without spinning.
* Fix compression threshold zero, retaining encryption and authentication.
* Alternative SDK build project targeting net40/x86 for host verification.
* New user-visible C# messages use Translations.resx and Translations.Designer.cs.

## Reproducible build

On Alpine x86: `sh install.sh`, then `sh run.sh`. No remote executable is downloaded.
On a .NET SDK build host:

```sh
dotnet build ports/ish/MinecraftClient/Build.csproj -c Release
```

The SDK host build downloads Microsoft.NETFramework.ReferenceAssemblies.net40 1.0.3
only at build time. Alpine builds use installed Mono framework assemblies via xbuild.
Keep CDDL notices and LICENSE.md with source/distribution. Bundled BouncyCastle and
DotNetZip code have their own permissive licenses; full license notices must accompany release.
Full BouncyCastle MIT and DotNetZip MS-PL license texts are included in
ports/ish/licenses. No prebuilt binaries are distributed at this stage.

Further audit found request/response debug dumps and cache migration logs that
could reveal credentials. These were removed, and refresh failures now fall back
to interactive sign-in instead of escaping as unhandled exceptions.

The Mono AES-CFB8 stream was checked directly against an independent OpenSSL 3.5.9
oracle on the Windows build host. Encryption, fragmented writes, decryption and EOF
all passed. The test exposed ReadByte returning zero instead of -1 at EOF; fixed.
Run `dotnet build tests/ish-crypto/IshCrypto.csproj -c Release`, then
`python3 tests/ish_crypto.py tests/ish-crypto/bin/Release/net40/IshCrypto.exe`
(add `--mono` on Linux and `--openssl /path/to/openssl` when needed).

CI publication was attempted on branch ish-port but GitHub rejected the push:
the authenticated OAuth app lacks workflow scope. No CI result exists yet. The
changes are committed locally; INSTRUÇÕES.txt is ignored and was not committed.

## Verification observed on Windows build host

* net40/x86 SDK build: passed, zero warnings and errors after compatibility changes.
* Real executable `--help`: passed from system temporary directory.
* `sh -n` run.sh, install.sh, scripts/diagnose-ish.sh: passed using Git POSIX shell.
* Controlled local 1.8.9 endpoint: real handshake/login, compressed inbound chat,
  outbound chat from stdin, keep-alive reply, `/exit` with status zero: passed.
* Compression threshold zero regression: passed against the same real executable.
* OAuth prompt and real Microsoft rejection of invalid code: exercised without secrets.
  This exposed Console.KeyAvailable failure under redirected input, subsequently fixed.
  Rerun passed: actionable error, no password prompt, EOF exits with code 1 and no exception.

The network fixture intentionally uses a local offline-mode endpoint to test protocol I/O;
it does not verify online authentication or substitute for online-mode support.

## Remaining validation and known limits

Additional Windows regressions passed: server disconnect packet, TCP FIN, truncated
packet followed by FIN, oversized frame and inconsistent decompressed-size header.
Each returns to the offline prompt and accepts /exit with status zero. Fixes include
single bounded stdin broker, stopping the old prompt consumer on disconnect, EOF-aware
socket receive, complete socket sends and an 8 MiB packet/decompression buffer limit.
Malformed cached JWTs fall back to browser login; malformed cache contents are not
printed, even in debug. The corrupt-cache OAuth rejection test passed as well.

The user will provide a Minecraft Java 1.21.11 server on their phone. This is now
an explicit required target, not supported by the imported legacy protocol yet.
Modern login/configuration/play transitions, packet routing and chat need adaptation
before this endpoint can be tested. The progress JSON includes this pending version
milestone; the denominator changed from 16 to 17, with the original eight checks retained.

Protocol 774 preparation: Configuration12111 implements the mandatory configuration
control replies with packet IDs from modern MCC's PacketPalette1219/1216 tables.
Its Windows net40/x86 harness verifies 64-bit keep-alive echo, 32-bit pong, absent-cookie
response, empty known-pack selection requesting full registries, finish acknowledgement,
rejection of wrong-sized keep-alive and prevention of replies after leaving configuration.
Test command: `tests/ish-crypto/bin/Release/net40/IshCrypto.exe --configuration`.
It deliberately does not accept server codes of conduct automatically. This component
is not yet wired into a complete protocol-774 connection; no new version is advertised.

Network text preparation: NetworkText12111 parses unnamed NBT roots (string, compound,
list) into the existing chat component representation. DataTypes.ReadNextChat chooses
this path for protocol 765+ and preserves legacy JSON for older protocols. The new
reader limits nesting to 64 and nodes to 8192 and bounds allocation by available bytes.
The host harness tests root strings/compounds/lists, final text rendering through the
actual ChatParser, unread packet trailing fields, truncated input, huge list counts,
invalid tag types and excessive nesting. This prepares modern chat/disconnect decoding;
it does not yet provide login/play routing, signed chat or connection to 1.21.11.

Login12111 now encodes the protocol-774 Login Start (username + UUID in Java network
byte order), consumes Login Success including optional signed profile properties,
produces the empty acknowledgement payload and declines unsupported login plugin
requests while preserving their transaction ID. The host harness checks exact wire
bytes against a literal UUID, signed-property consumption, duplicate success rejection,
truncated success rejection and negative plugin response. All passed with zero build
warnings. This codec is not yet wired to the live connection and is not proof of
Microsoft authentication, signed chat or a complete protocol-774 login session.

ModernSession12111 now connects the login/configuration codecs to a real framed TCP
transport. It implements compression including zero threshold, login acknowledgements,
plugin and cookie replies, configuration controls and encrypted transport using existing
RSA/AES plus the legitimate session join check when the server requests authentication.
Real encryption in this new session is not yet exercised. Server resource-pack,
transfer and code-of-conduct requests stop with an explicit unsupported-policy error.
The TCP fixture `tests/ish_modern_session.py` passed on Windows, checking protocol 774,
UUID wire bytes, plugin/cookie replies, compressed configuration and the exact transition
boundary. It is a library/session harness, not the complete interactive MCC play path.

User endpoint corrected: Paper 1.21.11 at 192.168.100.249, port 25565. The host
is on the same /24 subnet. Initial Minecraft and SSH connection attempts timed out;
the user explained the server was still starting. Maintenance directory supplied as
/sdcard/testserver. No SSH login or changes on the phone were performed.

The original .29 address was a user typo. The corrected .249 endpoint answered a
real status request: Paper 1.21.11, protocol 774, max 20 players. SSH responds on
8022 (OpenSSH_10.4); port 22 refuses connections. SSH username is still required
before maintenance can be attempted.

Real server probe passed on the Windows build host using
`IshCrypto.exe --modern-probe 192.168.100.249 25565`: the new transport completed
login/configuration, received Join Game (entity 419, seaLevel 63, secureChat false),
and sent Player Loaded. No Microsoft credentials were supplied by this diagnostic
probe, so this result is not online-account authentication validation. The probe
closed immediately after join and does not prove chat, sustained session or iSH
execution. It used the actual port assembly, not a separate fake client.

Play12111 implements core protocol-774 play controls using modern MCC's packet IDs:
64-bit keep-alive, 32-bit ping/pong, NBT system/overlay messages, NBT disconnect
reasons, teleport acknowledgement and absolute/relative position/rotation updates.
The TCP fixture now checks these after login/configuration, including two teleports
and exact binary client responses. There is still no interactive 1.21.11 entry point,
player chat/signing, world state or bot integration for this path.
It must not be advertised as a complete 1.21.11 connection or iSH validation.

Join Game and Client Information are now included in the TCP fixture. Client settings
are sent in configuration with a small view distance. Play12111 parses the full
1.21.11 Join Game payload, including CommonPlayerSpawnInfo, seaLevel and the subsequent
secure-chat flag, and sends Player Loaded. The current modern MCC Join Game reader
appears to omit seaLevel; the port uses the official 1.21.11 server bytecode instead.
The server bundler was downloaded via Mojang's version_manifest_v2.json, its SHA-1
checked against official version metadata, and the inner server.jar inspected with
javap. Obfuscated classes aew (ClientboundLoginPacket) and ahx (CommonPlayerSpawnInfo)
confirm two successive VarInts after death-location data: portal cooldown and sea level.
No server binary was added to the repository. Mapping references:
https://mappings.dev/1.21.11/net/minecraft/network/protocol/game/ClientboundLoginPacket.html
https://mappings.dev/1.21.11/net/minecraft/network/protocol/game/CommonPlayerSpawnInfo.html
The fixture checks that seaLevel=63 is not mistaken for enforcesSecureChat=true.

Unsigned modern chat/command encoding is now implemented and gated on Join Game's
secure-chat flag. The fixture checks refusal to send when secureChat=true, then exact
chat timestamp/salt/signature/ack-window/checksum fields and the unsigned /version
command when the test server permits unsigned chat. This does not implement signing.
The real endpoint command probe passed on the Windows build host: it joined the
user's Paper, sent /version and decoded the NBT reply identifying Paper 1.21.11-132
(API 1.21.11-R0.1-SNAPSHOT). Player chat reception/ack tracking and interactive runtime
integration are still pending; no Microsoft account or iSH validation is claimed.

User-requested /say diagnostic: the real Paper received the attempt from PortTest
and replied with command.unknown.command / command.context.here. The command was
not available to this test player; no permissions were changed and no server-wide
say message was sent. The port decoded the actual join and command-error system
messages. The diagnostic returns status 46 for this outcome, checking error keys
before looking for the marker because command-error context echoes the command.
SSH console execution remains pending the user's SSH login name.

Server-console say reception is now verified on the real Paper. The test listener
stayed connected while the user ran say and received the exact body
`MCC_ISH_SERVER_MESSAGE_TEST oi`, exiting with status zero. This required implementing
the 0x21 disguised/profileless chat packet separately from 0x77 system chat, including
registry-backed and direct chat-type holder layouts and sender/optional-target text.
The TCP fixture additionally verifies this packet and sender parsing. This validates
server-generated say messages, not signed player-chat reception. The listener used
the Windows host and the same actual port assembly; iSH execution is still unverified.
DataTypes.ReadData now rejects impossible byte lengths before allocating arrays,
so malformed modern login/configuration string/byte-array lengths cannot request
buffers larger than the current frame or the 8 MiB port limit.

Latest integration: explicit mcversion=1.21.11 now routes through ModernConsole12111
in the actual Program entry point after normal configuration and session authentication.
The console supports stdin chat/commands, system/disguised/player messages and /exit.
Player signatures are not cryptographically verified and the UI labels them unverified;
filtered messages are suppressed. Signed message delivery acknowledgement is separate
from verification, with bounded duplicate tracking. Signing, modern bot/world/inventory
integration and automatic reconnect remain absent. Automatic version selection is not
yet routed to this experimental path; select 1.21.11 explicitly.

`tests/ish_interactive_modern.py ... --host ... --offline-test` passed against the
real Paper using the main MinecraftClient.exe (not the harness): INI load, join,
/version response, normal chat MCC_ISH_CHAT_ROUNDTRIP echoed as player chat, and
/exit with process status zero. The test is explicitly an offline-mode test against
a controlled server; it does not replace legitimate Microsoft account authentication
or prove iSH compatibility. The existing session/auth path remains used in normal operation.

Alpine x86 host validation preparation: downloaded QEMU's official Windows build
qemu-w64-setup-20260811.exe and verified its SHA-512 against the vendor checksum.
Extracted into system temp without running an installer. Booted the official Alpine
v3.22 x86 netboot kernel/initramfs under QEMU TCG/qemu32 with 1536 MiB RAM. Observed
Linux 6.12.115-0-lts i686, Alpine 3.22.8, DHCP and a root console login. A minimal
source archive (only port, scripts and tests; no task-instructions file) was prepared.
No Mono build/runtime result is available: bulk serial input through Windows ConPTY
lost characters, and that console session was terminated during recovery. Automatic
approval review subsequently rejected launching a TCP-serial-controlled QEMU process,
returning only 'blocked by policy'. No TCP-controlled VM was started by that attempt.
This is boot evidence for Alpine x86, not successful Mono or iSH validation. A safer
foreground serial session with paced input can be investigated next. All downloaded
tools and VM artifacts remain outside the repo in system temp/mcc-alpine-x86.

Follow-up: the safer foreground QEMU setup now boots with an apkovl generated by
tests/prepare_alpine_boot.py and runs tests through OpenRC without console input or
additional control ports. This path was accepted and is running. Observed guest
markers: MCC_ALPINE_TEST_START, i686, APK architecture x86, Alpine 3.22.8. The actual
install.sh installed Mono 6.14.1-r0 plus ca-certificates successfully and started
xbuild with Configuration Release / Platform x86. Compilation and the subsequent
runtime tests are still in progress, so no Mono build/test pass is recorded yet.
The source payload's Git archive comment identifies application revision
39fca888e6ad9a63059e7c4602a9f816281ee667. Reproduction steps are in tests/ALPINE-X86.md.

Observed outcome of this run: Mono/xbuild Release/x86 compiled successfully and
install.sh confirmed the executable. The initial launcher failed because OpenRC
did not provide HOME. run.sh now falls back to the UID's home from /etc/passwd
without assigning HOME, and `env -u HOME sh run.sh --help` passed in the guest.
The overlay also needed loopback explicitly initialized for local fixtures.
After that environment correction, legacy compressed chat/keepalive/exit, truncated
TCP recovery, AES-CFB8 vs OpenSSL, codec harnesses and modern TCP fixtures passed
on Alpine x86. The final OAuth rejection test failed: Mono's certificate store did
not trust the HTTPS endpoint, and AutoTimeout allowed the exception to escape its
worker thread and terminate the process. This is not a passing OAuth suite.

Corrections under verification: install.sh synchronizes the standard CA bundle
into Mono's trust store with cert-sync (system store for root, user store otherwise),
without disabling certificate checks. AutoTimeout captures worker failures and
rethrows on the calling thread where the authentication code can report them.
The same guest received SHA-256-verified source updates and started a Mono rebuild;
final TLS/OAuth results are pending. A --timeout-failure harness regression was added.

Actual iSH testing has not run. Alpine x86/Mono build and network/crypto fixtures
have passed locally under QEMU; the TLS/OAuth suite is being repeated after fixes.
WSL is disabled on this host. A written CI workflow is not evidence of a passing CI run.
Real account OAuth, refresh, online encrypted session and every version in the declared
legacy range remain unverified. Startup memory/time on iSH remains unmeasured.
Experimental 1.21.11 chat/commands are implemented, but signing and modern TUI/bot/
world/inventory integration remain absent. This is not a completed port of the net10 app.

Latest Alpine result: the Mono rebuild returned REBUILD_EXIT=0. After syncing the
normal CA bundle, the suite completed with MCC_ALPINE_TEST_PASS and
MCC_ALPINE_RESUME_EXIT=0. HTTPS certificate verification succeeded and Microsoft
returned the expected AADSTS error for the deliberately invalid authorization code;
the process reported it cleanly and exited with code 1. No actual account was used.
The same Mono-built main executable then passed the real Paper 1.21.11 interactive
test: INI load, join, /version response, player-chat roundtrip and /exit status zero.
This is verified on Alpine 3.22.8 x86 / Mono 6.14.1, not only on Windows.

Publication plan: publish the tested source and docs on ish-port without changing
any GitHub workflow. The CI file remains local because the current OAuth token lacks
workflow scope. No workflow update or main-branch merge is included.
