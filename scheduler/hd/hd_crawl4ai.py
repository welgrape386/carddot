"""
hd_crawl4ai.py - 현대카드 crawl4ai 크롤러

hd_cards.json에 등록된 카드 URL을 크롤링하여
output/md/{card_name}.md 로 저장.

[실행]
  python hd_crawl4ai.py                        # 전체 카드
  python hd_crawl4ai.py --card_id ME4          # 특정 카드만
  python hd_crawl4ai.py --card_id ME4 --skip_trim  # trim 없이 raw만 저장
"""

import asyncio
import argparse
import json
import os
import re
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai import DefaultMarkdownGenerator

# =============================================
# 경로
# =============================================
CARDS_JSON  = "hd_ouput/hd_cards.json"
MD_OUT_DIR  = "hd_ouput/md"
HTML_OUT_DIR = "hd_html"   # hd_html/{card_id}_main.html

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
    markdown_generator=DefaultMarkdownGenerator(),
)

# =============================================
# trim 로직 (inline — hd_utils 없이도 동작)
# =============================================

# 여기서부터 끝까지 제거
_CUT_FROM = [
    re.compile(r'^# 현대카드 SNS·패밀리·그룹사'),
    re.compile(r'^회사소개$'),
]

# 해당 줄만 제거
_SKIP_LINE = [
    re.compile(r'javascript:popup\.close'),
    re.compile(r'javascript:popup\.open'),
    re.compile(r'!\[.*?\]\(https?://'),
    re.compile(r'^\[다운로드\]\('),
    re.compile(r'^\[전화신청\]'),
    re.compile(r'^\[신규 회원'),
    re.compile(r'^\[카드 신청\]'),
    re.compile(r'^신청하기$'),
    re.compile(r'^뱃지$'),
    re.compile(r'^더보기$'),
]

# 섹션 통째로 제거
_SKIP_SECTION = [
    re.compile(r'^## 신속발급서비스'),
    re.compile(r'^# Tom Sachs'),
    re.compile(r'^### Header 타이틀'),
]

def trim_md(raw: str) -> str:
    """
    fit.md → trimmed.md 변환.
    
    [처리 순서]
    1. _3F_ 이전 GNB/로그인 팝업 제거
    2. 준법감시심의필 등 규정상 표시 필요 줄은 유지 (skip 제외)
    3. 카드소개 섹션 노이즈 제거
    4. 푸터/SNS 영역 제거
    """
    lines  = raw.split('\n')
    result = []
    body_started   = False
    skip           = False  # 섹션 스킵

    for line in lines:

        # 1. 본문 시작점 (_3F_ 기준)
        if not body_started:
            if re.search(r'_3F_', line):
                body_started = True
            else:
                continue

        # 2. 여기서부터 끝까지 잘라내기
        if any(p.search(line) for p in _CUT_FROM):
            break

        # 3. 자동 로그아웃 팝업
        if '자동 로그아웃 예정' in line:
            break

        # 4. 해당 줄만 제거
        if any(p.search(line) for p in _SKIP_LINE):
            continue

        # 5. 섹션 스킵 시작
        if any(p.search(line) for p in _SKIP_SECTION):
            skip = True
            continue

        # 6. 다음 # 헤더 나오면 섹션 스킵 종료
        if skip and re.match(r'^#', line):
            skip = False

        if not skip:
            result.append(line)

    return '\n'.join(result)


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
# 카드 이름 → 파일명 변환
# 예: "현대카드M"   → "현대카드M.md"
#     "현대카드 M 에디션4" → "현대카드M에디션4.md"  (공백 제거)
# =============================================
def card_name_to_filename(card_name: str) -> str:
    safe = re.sub(r'[\s/\\:*?"<>|]', '', card_name)  # 파일명 불가 문자 제거
    return f"{safe}.md"


# =============================================
# 카드 1개 크롤링 + 저장
# =============================================
async def crawl_card(
    crawler: AsyncWebCrawler,
    card: dict,
    skip_trim: bool = False,
) -> bool:
    card_id   = card['card_id']
    card_name = card['card_name']
    url       = card['url']
    filename  = card_name_to_filename(card_name)

    print(f"\n[{card_id}] {card_name}")
    print(f"  URL  : {url}")
    print(f"  파일 : {filename}")

    result = await crawler.arun(url=url, config=CRAWL_CFG)

    if not result.success:
        print(f"  ❌ 크롤링 실패: {result.error_message}")
        return False

    raw_md = result.markdown.raw_markdown if result.markdown else ''

    if not raw_md.strip():
        print(f"  ❌ 마크다운 비어있음")
        return False

    os.makedirs(MD_OUT_DIR, exist_ok=True)

    if skip_trim:
        # raw 그대로 저장
        out = os.path.join(MD_OUT_DIR, filename)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(raw_md)
        print(f"  ✅ raw 저장 | {len(raw_md):,}자 → {out}")
    else:
        # trimmed md 저장
        trimmed = trim_md(raw_md)
        out = os.path.join(MD_OUT_DIR, filename)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(trimmed)

        # raw md 별도 저장 (파서에서 팝업 영역 데이터 추출용 — annual_fee_notes 등)
        raw_out = os.path.join(MD_OUT_DIR, filename.replace('.md', '_raw.md'))
        with open(raw_out, 'w', encoding='utf-8') as f:
            f.write(raw_md)

        ratio = len(trimmed) / max(len(raw_md), 1) * 100
        print(f"  ✅ trim 저장 | raw {len(raw_md):,}자 → trimmed {len(trimmed):,}자 ({ratio:.0f}%)")
        print(f"  💾 trimmed : {out}")
        print(f"  💾 raw     : {raw_out}")

    # HTML 저장 (AI 파서용 — box_content 섹션 구조 보존)
    fit_html = result.cleaned_html or result.html or ""
    if fit_html:
        os.makedirs(HTML_OUT_DIR, exist_ok=True)
        html_path = os.path.join(HTML_OUT_DIR, f"{card_id}_main.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(fit_html)
        print(f"  💾 HTML    : {html_path} ({len(fit_html):,}자)")
    else:
        print(f"  ⚠️  HTML 비어있음 — HTML 저장 스킵")

    return True


# =============================================
# 메인
# =============================================
async def main():
    parser = argparse.ArgumentParser(description='현대카드 crawl4ai 크롤러')
    parser.add_argument('--card_id',    default=None,        help='특정 카드 ID (기본: 전체)')
    parser.add_argument('--skip_trim',  action='store_true', help='trim 없이 raw MD 저장')
    args = parser.parse_args()

    cards = load_cards(args.card_id)

    print('=' * 60)
    print(f'현대카드 크롤링 시작 ({len(cards)}개)')
    print(f'저장 위치: {MD_OUT_DIR}/')
    print(f'파일명 형식: {{카드명}}.md')
    print('=' * 60)

    ok, fail = 0, 0
    async with AsyncWebCrawler(config=BROWSER_CFG) as crawler:
        for card in cards:
            success = await crawl_card(crawler, card, skip_trim=args.skip_trim)
            if success:
                ok += 1
            else:
                fail += 1

    print('\n' + '=' * 60)
    print(f'완료 | 성공: {ok} / 실패: {fail}')
    print('=' * 60)


if __name__ == '__main__':
    asyncio.run(main())