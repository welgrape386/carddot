"""
crawler.py - KB국민카드 페이지 크롤링 (Playwright 기반)

동작:
1. Playwright로 카드 상세페이지 HTML 추출 (브라우저 재사용)
2. 모든 탭(tabCon00~tabCon03, 서브탭 포함) 강제 display:block 처리 후 반환
"""

from datetime import datetime
from playwright.async_api import Browser

from config import BASE_URL, CARD_PAGE_CODE, BROWSER_HEADLESS, USER_AGENT


def log(msg: str):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")


def line():
    print("=" * 60)


async def get_page_html(browser: Browser, cooperation_code: str) -> tuple[str, str]:
    """
    브라우저를 재사용해 카드 상세 페이지 HTML 반환.
    모든 탭을 강제로 display:block 처리 후 추출.

    Returns:
        (html, target_url)
    """
    target_url = (
        f"{BASE_URL}{CARD_PAGE_CODE}"
        f"?mainCC=a&cooperationcode={cooperation_code}"
    )

    context = await browser.new_context(
        user_agent=USER_AGENT,
        locale="ko-KR",
    )
    page = await context.new_page()

    # 불필요한 리소스 차단 (속도 개선)
    await page.route(
        "**/*",
        lambda route: route.abort()
        if route.request.resource_type in ("image", "media", "font", "stylesheet")
        else route.continue_()
    )

    log(f"[1/3] 페이지 접속: {target_url}")
    await page.goto(target_url, wait_until="domcontentloaded", timeout=30_000)
    try:
        await page.wait_for_selector(".cardKind", timeout=8_000)
    except Exception:
        pass

    # 모든 탭 강제 노출 — tabConXX 패턴 전체
    await page.evaluate("""
        () => {
            document.querySelectorAll('[id^="tabCon"]').forEach(el => {
                el.style.display = 'block';
                el.style.visibility = 'visible';
                el.classList.remove('hide', 'hidden', 'is-hidden');
            });
        }
    """)

    log(f"[2/3] 데이터 추출 중...")
    html = await page.content()

    await page.close()
    await context.close()

    return html, target_url
