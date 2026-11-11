import asyncio
import sys
import pytest

# On Windows, WindowsSelectorEventLoopPolicy avoids loopback socketpair network
# restrictions in sandboxed or offline environments.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

