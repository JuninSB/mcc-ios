"""Inventory the modern MCC source/dependency surface for the full iSH port.
This produces audit evidence, not a claim that inventoried features are ported.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument('--output', default='progress/full-scope.json')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
project = root / 'MinecraftClient/MinecraftClient.csproj'
xml = ET.parse(project).getroot()
cache = Path.home() / '.nuget/packages'
dependencies = []
for reference in xml.iter('PackageReference'):
    name, version = reference.attrib['Include'], reference.attrib['Version']
    package = cache / name.lower() / version
    dependencies.append({
        'name': name, 'version': version,
        'cached': package.is_dir(),
        'frameworks': sorted(p.name for p in (package / 'lib').iterdir()) if (package / 'lib').is_dir() else [],
        'runtimeIdentifiers': sorted(p.name for p in (package / 'runtimes').iterdir()) if (package / 'runtimes').is_dir() else [],
    })
modules = []
for directory in sorted((root / 'MinecraftClient').iterdir()):
    if not directory.is_dir() or directory.name in ('bin', 'obj', 'config'):
        continue
    sources = []
    for source in sorted(directory.rglob('*.cs')):
        sources.append({'path': source.relative_to(root).as_posix(), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    if sources:
        modules.append({'name': directory.name, 'sourceFiles': sources, 'fullPortStatus': 'pending'})
report = {
    'scope': 'All current main MCC runtime features, including TUI, minimap, inventory, world, physics, commands, bots, scripting and integrations',
    'targetFramework': next(xml.iter('TargetFramework')).text,
    'note': 'Source-file inventory and cached package assets are audit evidence only. No full module is marked ported by this report.',
    'dependencies': dependencies,
    'projectReferences': [item.attrib['Include'] for item in xml.iter('ProjectReference')],
    'embeddedResources': [item.attrib['Include'] for item in xml.iter('EmbeddedResource') if 'Include' in item.attrib],
    'modules': modules,
    'rootSources': [p.relative_to(root).as_posix() for p in sorted((root / 'MinecraftClient').glob('*.cs'))],
}
output = root / args.output
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
probe = root / 'ports/full/CompatibilityProbe.csproj'
probe.parent.mkdir(parents=True, exist_ok=True)
project_xml = ET.Element('Project', Sdk='Microsoft.NET.Sdk')
properties = ET.SubElement(project_xml, 'PropertyGroup')
ET.SubElement(properties, 'TargetFramework').text = 'net472'
ET.SubElement(properties, 'EnableDefaultCompileItems').text = 'false'
items = ET.SubElement(project_xml, 'ItemGroup')
ET.SubElement(items, 'PackageReference', Include='Microsoft.NETFramework.ReferenceAssemblies.net472', Version='1.0.3', PrivateAssets='all')
for dependency in dependencies:
    ET.SubElement(items, 'PackageReference', Include=dependency['name'], Version=dependency['version'])
ET.indent(project_xml)
probe.write_text(ET.tostring(project_xml, encoding='unicode') + '\n', encoding='utf-8')
print(f'{len(modules)} modules, {sum(len(m["sourceFiles"]) for m in modules)} module source files, {len(dependencies)} dependencies inventoried.')
for dependency in dependencies:
    print(dependency['name'], dependency['frameworks'], dependency['runtimeIdentifiers'])
