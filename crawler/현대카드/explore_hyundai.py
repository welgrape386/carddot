import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 카드 전용 HTML 파일 직접 fetch
        await page.goto('https://www.hyundaicard.com/docfiles/resources/pc/html/carDtl/ME4_PC.html')
        await page.wait_for_load_state('networkidle')
        
        html = await page.content()
        
        with open('ME4_PC.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print('ME4_PC.html 저장 완료')
        print(f'파일 크기: {len(html):,} bytes')
        
        # 주요 텍스트 빠르게 확인
        for selector in ['h2', 'h3', 'h4', 'strong', '.tit', '[class*="tit"]']:
            try:
                els = await page.query_selector_all(selector)
                for el in els[:5]:
                    t = (await el.inner_text()).strip()
                    if t and len(t) < 80:
                        print(f'[{selector}] {t}')
            except:
                pass
        
        await browser.close()

asyncio.run(main())