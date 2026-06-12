"""
hd_crawl4ai.py - 현대카드 crawl4ai 크롤러

hd_cards.json에 등록된 카드 URL을 크롤링하여
hd_html/{card_id}_main.html 로 저장.

[실행]
  python hd_crawl4ai.py                 # 전체 카드
  python hd_crawl4ai.py --card_id ME4  # 특정 카드만
"""

import asyncio
import argparse
import json
import os
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# =============================================
# 경로
# =============================================
CARDS_JSON   = "hd_cards.json"
HTML_OUT_DIR = "hd_html"

# =============================================
# 브라우저 설정
# =============================================
BROWSER_CFG = BrowserConfig(
    headless=True,
    user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    extra_args=["--disable-blink-features=AutomationControlled"],
)

# =============================================
# 현대카드 팝업 오픈 JS
# 혜택 상세가 .modal_pop(display:none) 안에 숨겨져 있음
# =============================================
JS_OPEN_POPUPS = """
    document.querySelectorAll('.modal_pop').forEach(el => {
        el.style.display = 'block';
        el.style.visibility = 'visible';
        el.style.opacity = '1';
    });
    document.querySelectorAll('.accodSlide').forEach(el => {
        el.style.display = 'block';
    });
"""

CRAWL_CFG = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    wait_until="domcontentloaded",
    js_code=JS_OPEN_POPUPS,
    delay_before_return_html=3.0,
    word_count_threshold=5,
)


# =============================================
# 카드 목록 로드
# =============================================
def load_cards(card_id: str = None) -> list:
    if not os.path.exists(CARDS_JSON):
        raise FileNotFoundError(f"카드 목록 파일 없음: {CARDS_JSON}")
    with open(CARDS_JSON, encoding='utf-8') as f:
        cards = json.load(f)
    if card_id:
        cards = [c for c in cards if c['card_id'] == card_id]
        if not cards:
            raise ValueError(f"card_id '{card_id}'를 {CARDS_JSON}에서 찾을 수 없음")
    return cards


# =============================================
# 카드 1개 크롤링 + HTML 저장
# =============================================
async def crawl_card(crawler: AsyncWebCrawler, card: dict) -> bool:
    card_id   = card['card_id']
    card_name = card['card_name']
    url       = card['url']

    print(f"\n[{card_id}] {card_name}")
    print(f"  URL: {url}")

    result = await crawler.arun(url=url, config=CRAWL_CFG)

    if not result.success:
        print(f"  ❌ 크롤링 실패: {result.error_message}")
        return False

    fit_html = result.cleaned_html or result.html or ""
    if not fit_html.strip():
        print(f"  ❌ HTML 비어있음")
        return False

    os.makedirs(HTML_OUT_DIR, exist_ok=True)
    html_path = os.path.join(HTML_OUT_DIR, f"{card_id}_main.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(fit_html)
    print(f"  ✅ HTML 저장: {html_path} ({len(fit_html):,}자)")

    return True


# =============================================
# 메인
# =============================================
async def main():
    parser = argparse.ArgumentParser(description='현대카드 crawl4ai 크롤러')
    parser.add_argument('--card_id', default=None, help='특정 카드 ID (기본: 전체)')
    args = parser.parse_args()

    cards = load_cards(args.card_id)

    print('=' * 60)
    print(f'현대카드 크롤링 시작 ({len(cards)}개)')
    print(f'저장 위치: {HTML_OUT_DIR}/')
    print('=' * 60)

    ok, fail = 0, 0
    async with AsyncWebCrawler(config=BROWSER_CFG) as crawler:
        for card in cards:
            success = await crawl_card(crawler, card)
            if success:
                ok += 1
            else:
                fail += 1

    print('\n' + '=' * 60)
    print(f'완료 | 성공: {ok} / 실패: {fail}')
    print('=' * 60)


if __name__ == '__main__':
    asyncio.run(main())
