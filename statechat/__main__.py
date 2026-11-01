import asyncio
import os
import sys

from .server import serve

port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8765))
try:
    asyncio.run(serve(port=port))
except KeyboardInterrupt:
    pass
