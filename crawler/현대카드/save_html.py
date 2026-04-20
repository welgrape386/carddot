import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        await page.goto("https://www.hyundaicard.com/cpc/cr/CPCCR0201_01.hc?cardWcd=ME4")
        
        # networkidle 까지 대기 (모든 요청 완료 후)
        await page.wait_for_load_state("networkidle")
        
        # 스크롤 끝까지 내려서 lazy load 콘텐츠 로드
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        
        html = await page.content()
        with open("ME4_main.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"저장 완료 / 크기: {len(html):,} bytes")
        
        await browser.close()

asyncio.run(main())