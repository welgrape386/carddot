"""
KB국민카드 HTML 크롤러
kb_crawl_targets.json 기준으로 미수집 카드 HTML 수집
"""
import asyncio, json, os, argparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai import DefaultMarkdownGenerator

HTML_DIR   = "html"
CARDS_JSON = "kb_crawl_targets.json"

BROWSER_CFG = BrowserConfig(
    headless=True,
    user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    extra_args=["--disable-blink-features=AutomationControlled"],
)

CRAWL_CFG = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    wait_until="domcontentloaded",
    wait_for="css:.benefitList1",
    css_selector="#main_contents",
    delay_before_return_html=5.0,
    word_count_threshold=10,
    markdown_generator=DefaultMarkdownGenerator(),
)

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--card_id", default=None)
    return p.parse_args()

async def crawl_card(crawler, card):
    cid  = card["card_id"]
    name = card["card_name"]
    url  = card["url"]
    out  = f"{HTML_DIR}/{cid}_main.html"

    if os.path.exists(out):
        print(f"  [SKIP] {cid} 이미 수집됨")
        return True

    print(f"\n[{cid}] {name}")
    try:
        result = await crawler.arun(url=url, config=CRAWL_CFG)
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return False

    if not result.success:
        print(f"  ❌ 실패: {result.error_message}")
        return False

    html = result.cleaned_html or result.html or ""
    if not html.strip():
        print(f"  ❌ HTML 비어있음")
        return False

    os.makedirs(HTML_DIR, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ 저장: {out} ({len(html):,}자)")
    return True

async def main():
    args = parse_args()
    with open(CARDS_JSON, encoding="utf-8") as f:
        cards = json.load(f)

    if args.card_id:
        cards = [c for c in cards if c["card_id"] == args.card_id]

    print(f"크롤링 대상: {len(cards)}개")
    success, fail = 0, 0

    async with AsyncWebCrawler(config=BROWSER_CFG) as crawler:
        for card in cards:
            ok = await crawl_card(crawler, card)
            if ok: success += 1
            else:  fail    += 1

    print(f"\n완료 | 성공: {success} / 실패: {fail}")

if __name__ == "__main__":
    asyncio.run(main())
