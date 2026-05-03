"""
crawler.py - 삼성카드 페이지 크롤링 (Playwright + aiohttp 기반)
"""

import asyncio
import json
import re
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from config import BASE_URL, CDN_BASE, LIST_URLS, BROWSER_HEADLESS, USER_AGENT


# ── 공통 유틸 ─────────────────────────────────────────────────

def log(msg: str):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")

def line():
    print("=" * 60)


# ── STEP 1: Playwright로 __NUXT__ 추출 ───────────────────────

async def get_nuxt_data(card_code: str) -> dict:
    url = BASE_URL + card_code

    async def handle_route(route):
        if route.request.resource_type in ("image", "media", "font", "stylesheet"):
            await route.abort()
        else:
            await route.continue_()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=BROWSER_HEADLESS)
        context = await browser.new_context(user_agent=USER_AGENT, locale="ko-KR")
        page = await context.new_page()
        await page.route("**/*", handle_route)
        log(f"페이지 접속: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.wait_for_function(
                "() => { try { return !!(window.__NUXT__?.data?.[0]?.wcms?.pdList?.length); } catch(e) { return false; } }",
                timeout=15000,
            )
        except Exception:
            await page.wait_for_timeout(5000)
        nuxt_data = await page.evaluate("() => window.__NUXT__?.data?.[0] || null")
        sell_start_dt = await page.evaluate(
            "() => document.getElementById('sellStrtdt')?.textContent?.trim() || ''"
        )
        await browser.close()

    if not nuxt_data:
        raise RuntimeError("__NUXT__.data[0] 추출 실패")

    with open(f"nuxt_debug_{card_code}.json", "w", encoding="utf-8") as f:
        json.dump(nuxt_data, f, ensure_ascii=False, indent=2)

    return {
        "card_code":     card_code,
        "sell_start_dt": sell_start_dt,
        "nuxt_data":     nuxt_data,
    }


# ── 목록 페이지 HTML 저장 ─────────────────────────────────────

async def save_list_page_html():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(LIST_URLS[0], wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        html = await page.content()
        with open("list_page_playwright.html", "w", encoding="utf-8") as f:
            f.write(html)
        await browser.close()
    log("목록 페이지 저장 완료: list_page_playwright.html")


# ── HTML fetch 헬퍼 ───────────────────────────────────────────

async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    full_url = url if url.startswith("http") else CDN_BASE + url
    async with session.get(full_url) as resp:
        return await resp.text()