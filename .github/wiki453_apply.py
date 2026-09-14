#!/usr/bin/env python3
from pathlib import Path
import base64,gzip
parts = [Path(__file__).with_name(f"wiki453_apply.b64.{i:02d}").read_text().strip() for i in range(5)]
source = gzip.decompress(base64.b64decode("".join(parts), validate=True)).decode()
exec(compile(source, __file__, "exec"))
