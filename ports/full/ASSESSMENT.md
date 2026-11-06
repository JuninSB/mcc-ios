# Modern runtime compatibility, measured

The user explicitly requires the full current MCC feature set. The net40 prototype
does not meet that scope and is not the completion target. No minimap, inventory,
bot, scripting, protocol version or integration may silently disappear to make a
compatibility build pass.

The generated inventory covers 18 source modules, 525 module C# files, root runtime
sources and 19 declared dependencies. File hashes freeze the source surface to be
preserved. Source presence is not treated as an implemented/tested feature.

## Executed probe

`dotnet restore ports/full/CompatibilityProbe.csproj` targeting net472 failed with
NU1202 for Consolonia 11.3.12.6 (net8.0 only) and ModelContextProtocol.AspNetCore
1.4.1 (net8/net9/net10 only). The restore also reported MessagePack 3.1.8 advisory
GHSA-qhrr-8q5h-9q3h; it remains a real dependency finding, not a suppressed warning.

Cached Magick.NET 14.15.0 assets include Linux x64/arm64 and Windows x86, but no
Linux x86 native library. Its managed netstandard asset does not solve native loading.
Many other dependencies do have older-compatible assets, including Brigadier,
DSharpPlus, Roslyn, Telegram.Bot and Tomlet; they must not all be assumed incompatible.

NuGet package index probes returned 404 for
Microsoft.NETCore.App.Runtime.Mono.linux-x86 and linux-musl-x86, and 200 for linux-x64.
That establishes absence of those ready-made runtime packs, not impossibility of
building a runtime. Official modern Mono documentation describes building mono+libs:
https://github.com/dotnet/runtime/blob/v10.0.0/docs/workflow/building/mono/README.md

## Required next implementation work

Establish whether a modern Mono runtime plus libraries can build/run for Linux
x86/musl under iSH constraints, before committing to a runtime source port. Otherwise
backport incompatible dependencies and APIs with equivalent feature behavior.
Consolonia/TUI, MCP HTTP hosting and native image bindings need explicit solutions;
disabling them is not a full port. Preserve the current main source/protocol palettes,
then validate each inventoried feature on the target. A successful restore or a
HelloWorld runtime smoke test alone will not establish full MCC compatibility.
