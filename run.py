"""
Local dev entrypoint. Must set the Windows event loop policy *before* uvicorn's own
asyncio.run() creates the process event loop -- setting it inside app modules is too
late, since importing the app happens after uvicorn has already created its loop.
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
