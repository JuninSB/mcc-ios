# Alpine x86 validation under QEMU

This is a build-host test, not an iPhone runtime dependency and not an iSH emulator.
It exercises Alpine x86/musl, Mono, POSIX scripts and the real MCC assembly. It does
not validate iSH's emulated syscalls, iOS suspension or iPhone memory/performance.

The current host setup uses the official QEMU Windows build
`qemu-w64-setup-20260811.exe`, extracted with 7-Zip after verifying the vendor's
SHA-512 checksum. No installer was run. Kernel/initramfs are from the official
Alpine v3.22 x86 netboot directory. Runtime files stay in system temp, outside Git.

Prepare a temporary `payload` directory containing:

1. `mcc-ish-source.tar`, produced with `git archive --format=tar --output <path>
   HEAD ports/ish run.sh install.sh scripts/diagnose-ish.sh tests`.
2. `mcc.apkovl.tar.gz`, produced with
   `python3 tests/prepare_alpine_boot.py --output <payload>/mcc.apkovl.tar.gz`.

Serve only that directory on the host loopback interface:
`python3 -m http.server 8766 --bind 127.0.0.1 --directory <payload>`.
QEMU user networking maps the host to guest address 10.0.2.2.

Boot QEMU with `-accel tcg -cpu qemu32 -m 1536 -nodefaults -display none
-serial stdio -monitor none -no-reboot`, the downloaded `-kernel vmlinuz-lts` and
`-initrd initramfs-lts`, and `-nic user,model=virtio-net-pci`.
Pass the following kernel command line as one `-append` argument:

```text
console=ttyS0,115200 loglevel=3 ip=dhcp alpine_repo=http://dl-cdn.alpinelinux.org/alpine/v3.22/main modules=loop,squashfs,virtio_net modloop=http://dl-cdn.alpinelinux.org/alpine/v3.22/releases/x86/netboot/modloop-lts apkovl=http://10.0.2.2:8766/mcc.apkovl.tar.gz
```

The overlay starts the tests via OpenRC's local service, without interactive serial
input, additional control ports, SSH or host installation. It enables only the main
and community repositories of the same Alpine branch, builds via `install.sh`, runs
the launcher and executes network, crypto, modern-protocol and negative OAuth tests.

Require **both** `MCC_ALPINE_TEST_PASS` and `MCC_ALPINE_EXIT=0` before recording
success. Boot/login alone is not a passing MCC/Mono test. Preserve the output and
investigate any nonzero exit. No credentials, task-instructions file or prebuilt MCC
binary are included in this minimal source archive. APK packages use Alpine's normal
signature verification; there is no `--allow-untrusted` or disabled TLS validation.

The minimal overlay explicitly initializes loopback before local TCP fixtures.
Without this, Alpine booted successfully but bind(127.0.0.1) failed before the client
could start. This was a test-VM setup issue, not an MCC protocol failure.
After an interrupted test suite, run `sh tests/resume_alpine.sh` from the source
root in the guest. It checks launcher behavior with HOME absent as well as the
remaining runtime fixtures; require its final pass/exit markers before recording success.
