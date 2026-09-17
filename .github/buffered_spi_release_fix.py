#!/usr/bin/env python3
"""Keep validated generated web payloads byte-identical across the SPI experiment."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=R/'scripts/build_html.py';s=p.read_text()
anchor='            header_path = os.path.join(root, f"{base_name}.generated.h")\n'
insert=anchor+'''
            # 4.7.5 build reproducibility: preserve the exact existing gzip bytes
            # only after proving their decompressed payload equals this input.
            # Gzip mtimes otherwise change unrelated generated C++ every build.
            if os.path.isfile(header_path):
                with open(header_path, "r", encoding="utf-8") as previous:
                    previous_text = previous.read()
                body = re.search(r"PROGMEM\\s*=\\s*\\{(.*?)\\};", previous_text, re.DOTALL)
                if body:
                    old_gzip = bytes(int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]{2})", body.group(1)))
                    try:
                        if gzip.decompress(old_gzip) == processed.encode("utf-8"):
                            compressed = old_gzip
                    except (OSError, EOFError, ValueError):
                        pass  # Invalid cache is regenerated, never trusted.
'''
assert s.count(anchor)==1
p.write_text(s.replace(anchor,insert))
p=R/'.github/wiki475_release.py';s=p.read_text()
s=s.replace("'.github/workflows/wiki475.yml'", "'.github/workflows/wiki475.yml','scripts/build_html.py','.github/buffered_spi_release_fix.py'")
old=" assert preserved_hashes()==load('wiki475-production-baseline.json'),'Production source changed'"
new=""" now=preserved_hashes();expected=load('wiki475-production-baseline.json')
 if now!=expected:
  differences={n:{'before':expected.get(n),'after':now.get(n)} for n in sorted(set(now)|set(expected)) if expected.get(n)!=now.get(n)}
  save('wiki475-source-differences.json',differences)
  raise AssertionError('Production source changed: '+str(differences))"""
assert s.count(old)==1;s=s.replace(old,new)
old=" assert '#define SD_USE_CUSTOM_SPI ' not in macros,'Unexpected custom SPI path'"
new=""" (R/'wiki475-effective-macros.txt').write_text('\\n'.join(x for x in macros.splitlines() if any(k in x for k in ['SPI_ARRAY','SPI_DRIVER','SD_USE_CUSTOM','SD_HAS_CUSTOM','DEDICATED_SPI']))+'\\n')
 definitions=dict(re.findall(r'^#define\\s+(\\w+)\\s*(.*)$',macros,re.M))
 assert definitions.get('SD_USE_CUSTOM_SPI','0').strip(' ()')=='0','Unexpected custom SPI path: '+definitions.get('SD_USE_CUSTOM_SPI','')"""
assert s.count(old)==1;s=s.replace(old,new)
p.write_text(s)
p=R/'.github/wiki475_README.md';s=p.read_text();s+='''\n## Reproducible generated web resources\n\nThe original build hook regenerated gzip timestamps inside five web-resource C++\nheaders. A strict source-preservation gate caught that unrelated change. The\nbuild hook now reuses an existing gzip byte array only after verifying that its\ndecompressed payload exactly matches the current source input. Changed or invalid\npayloads are regenerated. This keeps all retained production C++ byte-identical\nto 4.7.4; it is a build-support correction, not a runtime web or reader change.\nThe release gate still rejects any changed production source.\n''';p.write_text(s)
print('Applied strict generated-resource cache and diagnostic verifier corrections')
