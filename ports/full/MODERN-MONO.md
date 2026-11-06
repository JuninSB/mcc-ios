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
x86 target and compiler ABI; configuration and linking are still unproven.
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
It does not prove execution, a complete library distribution, or MCC/iSH
compatibility. Native runtime, library shims, remaining libraries, deployment and
feature-specific tests are still required.
