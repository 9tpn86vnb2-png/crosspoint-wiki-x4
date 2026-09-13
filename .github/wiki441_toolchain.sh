#!/usr/bin/env bash
set -euo pipefail
python -m pip install https://github.com/pioarduino/platformio-core/archive/refs/tags/v6.1.19.zip
python -m pip install -r requirements.txt
python -m pip install 'littlefs-python>=0.16.0' 'fatfs-ng>=0.1.14' 'pyyaml>=6.0.2' 'rich-click>=1.8.6' 'zopfli>=0.2.2' 'intelhex>=2.3.0' 'rich>=14.0.0' 'urllib3<2' 'cryptography>=45.0.3' 'certifi>=2025.8.3' 'ecdsa>=0.19.1' 'bitstring>=4.3.1' 'reedsolo>=1.5.3,<1.8' 'esp-idf-size>=2.0.0' 'esp-coredump>=1.14.0' 'esptool>=5,<6'
python - <<'PY'
from pathlib import Path
(Path.home()/'.platformio/packages/framework-arduinoespressif32-libs/esp32c3/sdkconfig.crosspoint').unlink(missing_ok=True)
PY
pio run -e wiki_x4_beta 2>&1 | tee wiki-build.log
