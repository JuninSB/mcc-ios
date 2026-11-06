# Modern Mono native feasibility experiment

The .NET 10 source still selects x86 native sources in Mono's CMake files and
does not exclude Linux musl x86 in `eng/Subsets.props`. This is evidence worth
testing, not a claim of a supported runtime or a working iSH port.

Pinned upstream source:

- URL: https://codeload.github.com/dotnet/runtime/tar.gz/refs/tags/v10.0.0
- SHA-256: `cbc351c6f7afa4fcb622c8faf09f2371933fbd1413672556a410e3bfff061ddf`
- Tag commit: `60629d14374c56f1cb51819049ad1fa529307f8d`
- Official build instructions: https://github.com/dotnet/runtime/blob/v10.0.0/docs/workflow/building/mono/README.md

The normal complete build is `./build.sh mono+libs`. The experiment in
`build-modern-mono-native.sh` instead probes the native CMake stage on Alpine
3.22 x86. It retains JIT, interpreter, reflection emit, threads and sockets.
It does not build managed libraries, native library shims, a deployment pack or
the MCC application. A passing native build alone cannot run MCC or establish
modern .NET compatibility. The separate net472 dependency probe remains relevant
if a usable modern runtime cannot be produced.

To reproduce with the existing QEMU setup in `tests/ALPINE-X86.md`:

1. Put the pinned archive in the temporary payload directory as
   `runtime-v10.0.0.tar.gz`, alongside `build-modern-mono-native.sh`.
2. Generate a separate overlay:

   ```sh
   python tests/prepare_alpine_boot.py --startup-script tests/modern_mono_alpine.sh --output /path/to/payload/modern.apkovl.tar.gz
   ```

3. Use the documented foreground QEMU command, with 3072 MiB of guest memory
   and `apkovl=http://10.0.2.2:8766/modern.apkovl.tar.gz`.
4. Inspect the actual configure/build errors. Require both
   `MCC_MODERN_MONO_NATIVE_BUILD_PASS` and `MCC_MODERN_MONO_EXIT=0` before recording
   a passing native build. No full-client milestone changes on this result.

The runtime source stays outside the MCC repository. Archive extraction on the
Windows host encountered Windows path-length restrictions in library tests; the
native experiment extracts its source directly in Linux instead. This host issue
does not establish a Mono runtime incompatibility.

## Observed results, 2026-11-06

Alpine 3.22.8 confirmed `i686` / APK `x86`, verified the source hash, installed
Clang 20.1.8 and completed the C/C++ compiler ABI checks. The first native
configuration then failed because `llvm-ar` was absent. This is a missing build
tool, not evidence that the runtime cannot support x86. The guest setup now
explicitly installs `llvm20`. In the same VM, installing that package allowed configuration
to resume: CMake reported `CMAKE_SYSTEM_PROCESSOR=x86`, `TARGET_ARCH=x86` and
`CMAKE_CROSSCOMPILING=FALSE`, then began its native header/function checks.
Native configuration subsequently passed (`MCC_MODERN_MONO_CONFIGURE_PASS`),
producing a 363-step Ninja build. Compilation reached at least step 45 before
the VM was stopped at the user's request to free host RAM. The native build did
not complete. Its temporary objects were in the diskless guest's RAM filesystem
and were not retained; the pinned source archive and successful CoreLib output
remain on the host. Clang reported `-Wsync-alignment` in Mono's 64-bit atomic
helper on x86. That warning has not been suppressed or established harmless.

The user subsequently clarified that the VM may run when it is doing necessary
compilation work; its shutdown was based on an assumption that it was idle.
Prefer host builds where practical to reduce pressure on this 4 GiB host.
A Windows-host cross-configuration
experiment using Zig 0.15.2, CMake 4.1.2 and Ninja 1.13.1 has identified the Linux
x86 target and compiler ABI; see the completed cross-build results below.
Restart a small Alpine guest later when an executable actually needs runtime
validation or necessary native compilation.

## Managed CoreLib build

Run on a development host with .NET SDK 10 installed:

```sh
python ports/full/build-modern-corelib.py /path/to/runtime-10.0.0
```

The helper builds the existing Mono `System.Private.CoreLib` project, retaining
`TARGET_X86`, `TARGET_32BIT`, `TARGET_LINUX` and reflection emit. Build-time
generators remain AnyCPU so the host's x64 compiler can load them. `Platform`
must be inferred by the Mono project, rather than globally forced on all its
tool projects: forcing it changes the ILLink output directory and breaks task
resolution. A clean rebuild is needed after changing assembly architecture.

The helper also resolves the actual installed SDK directory and supplies
`NetCoreSdkRoot`. Recent MSBuild falls back to `RuntimeIdentifierGraphPath` when
that property is absent in SDK 10; the runtime repository overrides that graph
path, so the fallback otherwise identifies the source directory as an SDK and
reports an empty SDK version. This workaround preserves the build tasks.

The helper passed on the Windows build host with SDK 10.0.402, zero warnings and
zero errors. Output:

`artifacts/bin/mono/linux.x86.Release/System.Private.CoreLib.dll`

SHA-256: `686976c01273b7651bc16aea825a386a7cd7d492f8c38249d48d19b0b7aebfc0`.

This proves compilation of the modern Mono CoreLib for the target definitions.
It does not prove a complete runtime distribution or MCC/iSH compatibility.

## Windows cross build and managed libraries

`cross-tools.json` pins the official Windows ZIP downloads and their SHA-256
checksums. Verify/download them under a temporary tools directory as `zig.zip`,
`cmake.zip` and `ninja.zip`, then extract into its `zig`, `cmake` and `ninja`
subdirectories respectively. Supply an existing GNU binutils directory whose
tools support ELF x86; the experiment used the host's MinGW binutils.

```text
python ports/full/build-modern-mono-cross.py RUNTIME_SOURCE --tools-dir TOOLS --binutils-dir BINUTILS --output NATIVE_OUTPUT --log-file BUILD_LOG
python ports/full/build-modern-corelib.py RUNTIME_SOURCE --libraries
```

These are development-host operations. They do not install an SDK/compiler on
the phone. Both builds use one compilation worker by default on this 4 GiB host.
The cross build generates native version files using upstream MSBuild targets;
the standalone Windows CMake path otherwise omits Linux's `_version.c` and
initially produces a fallback runtime-version header for version 6.

The Windows cross build completed all 411 Ninja steps. Inspection found that
Zig's default musl executable was static PIE, so the helper now requires dynamic
linking and verifies the ELF32 x86 interpreter `/lib/ld-musl-i386.so.1`.
Static musl's `dlopen` stub cannot load Mono components/native shims.

The managed `sfx.proj` build completed in 1:24:56, with a formal summary of zero
warnings/errors, and produced 171 shared-framework DLLs under the Linux musl x86
runtime-pack directory. It also printed unresolved-reference messages during
intermediate processing. Those messages remain recorded concerns to investigate
and validate through execution; they are not dismissed by the final summary.

## Bootstrap execution probe

`tests/modern-runtime/MinimalProbe.csproj` checks 32-bit little-endian execution,
CoreLib major version 10, dynamic-code support and object survival across GC.
It returns the distinctive exit code 73 only after those checks. This does not
test console I/O, networking, cryptography, scripting or any MCC feature.

Build the probe with the host SDK, then package it using
`tests/package_modern_smoke.py`. The package includes checksums, native components,
CoreLib and the System.Runtime implementation facade. Use
`tests/prepare_alpine_boot.py --startup-script tests/modern_mono_smoke.sh` for a
512 MiB Alpine test guest; it powers off automatically on completion or failure.
The external checksum file explicitly uses LF for BusyBox compatibility.
Require both `MCC_MODERN_SMOKE_PASS` and `MCC_MODERN_SMOKE_EXIT=0`.

The initial execution reached `mono-sgen --version` on Alpine 3.22.8 x86, but
loading managed code aborted with SIGSEGV (exit 134). A separate diagnostic
overlay, `tests/modern_mono_gdb.sh`, with `--debug-symbols` packaging, captured:

```text
ep_rt_mono_runtime_provider_init
mono_metadata_signature_alloc(m=0x0)
mono_image_alloc0(image=0x0)
mono_image_lock(image=0x0)
__pthread_mutex_lock(m=0x6ec)
```

The initialized executable and the component-linked `libmonosgen-2.0.so` were
separate copies; the executable exported no Mono runtime APIs. The helper now
adds `--export-dynamic` and checks the exports so components can use the running
instance. After relinking, the probe reached `Program.Main` and progressed to
`Assembly.GetName`, eliminating the EventPipe null-image failure. It then failed
while resolving `System.Native` during culture/environment initialization; this
native shim has not been built/packaged yet. The managed probe still exits 134,
so the execution test is not passing. Components and diagnostics were not disabled
to avoid the failure. GDB's own exit zero is a diagnostic result, not a passing
managed-runtime test.

Native library shims, runtime execution, deployment and full MCC feature tests
are still required before this can replace the partial net40 alpha.
