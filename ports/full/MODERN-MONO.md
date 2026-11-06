# Modern Mono native feasibility experiment

The .NET 10 source still selects x86 native sources in Mono's CMake files and
does not exclude Linux musl x86 in `eng/Subsets.props`. This is evidence worth
testing, not a claim of a supported runtime or a working iSH port.

Pinned upstream source:

- URL: https://codeload.github.com/dotnet/runtime/tar.gz/refs/tags/v10.0.0
- SHA-256: `cbc351c6f7afa4fcb622c8faf09f2371933fbd1413672556a410e3bfff061ddf`
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
