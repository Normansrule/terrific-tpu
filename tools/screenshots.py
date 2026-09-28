#!/usr/bin/env python3
"""screenshots.py - capture the web pages into docs/img/*.png for the README.

    pip install playwright && playwright install chromium
    python3 tools/screenshots.py        (or: make screenshots)

Starts a local web server (the 3-D pages use JavaScript modules, which
browsers refuse to load from file://), drives each page into an
interesting state, and saves a screenshot.
"""
import asyncio
import functools
import http.server
import os
import threading

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "img")
PORT = 8765


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = functools.partial(Quiet, directory=ROOT)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


async def main():
    from playwright.async_api import async_playwright
    os.makedirs(OUT, exist_ok=True)
    srv = serve()
    errors = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        async def page(name, w=1440, h=900, action=None, full=False):
            pg = await b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            pg.on("pageerror", lambda e: errors.append((name, str(e))))
            await pg.goto(f"http://127.0.0.1:{PORT}/web/{name}.html", wait_until="load")
            await pg.wait_for_timeout(900)
            if action:
                await action(pg)
            await pg.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=full)
            print("  captured", name)
            return pg

        async def tour(pg):
            await pg.evaluate("window.__tour.go(3, true); window.__tour.setT(window.__tour.snaps.findIndex(x => x.state === 3) + 6.5)")
            await pg.wait_for_timeout(6000)

        async def chip(pg):
            for _ in range(20):
                await pg.click("#step")

        async def arr(pg):
            for _ in range(14):
                await pg.click("#step")

        async def chal(pg):
            await pg.fill("#src", "LDW w=0\nMMUL ub=0 rows=4 acc=0\nHALT\n")
            await pg.click("#run")
            await pg.wait_for_timeout(1500)

        await page("index", action=lambda pg: pg.wait_for_timeout(1200))
        await page("tour", action=tour)
        await page("chip", action=chip)
        await page("apps", h=1100)
        await page("array3d", action=arr)
        await page("challenges", action=chal)
        async def race(pg):
            await pg.click("#go")
            await pg.wait_for_timeout(600)
            await pg.evaluate("window.__race.finish()")
            await pg.wait_for_timeout(1500)

        async def xray(pg):
            await pg.wait_for_timeout(1500)
            await pg.evaluate("window.__xray.jump('mxu')")
            await pg.wait_for_timeout(1500)

        await page("race", h=1000, action=race)
        await page("xray", action=xray)
        await page("research", h=1100)
        await page("playground")
        await page("explorers")
        await b.close()
    srv.shutdown()
    print("page errors:", errors or "none")


if __name__ == "__main__":
    asyncio.run(main())
