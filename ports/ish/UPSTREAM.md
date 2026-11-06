# Provenance

The `MinecraftClient` directory contains the runtime from MCCTeam/Minecraft-Console-Client,
branch `previous`, commit `b3cc2351ee14d8e4fadc6f0e6115478872143c48`.
Only the runtime directory was imported, not upstream tooling, documentation or GUI.
Copyright notices remain in each file. CDDL 1.0 applies; see ../../LICENSE.md.
This separate compatibility runtime deliberately retains the legacy protocols (1.4.6 to
1.18.2). It does not implement the modern runtime's newer versions.

Build.csproj is a build-host alternative to the original Mono/xbuild project.
