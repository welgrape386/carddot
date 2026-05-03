"""
debug2.py - 부가서비스/Platinum 영역 HTML 구조 확인
python debug2.py
"""
from bs4 import BeautifulSoup
import re

card_name = "신한카드 Point Plan+"

with open(f"raw_{card_name}.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# ── 1. "부가서비스 변경가능" 텍스트 주변 구조
print("=" * 60)
print("[1] 부가서비스 변경가능 사유 영역")
for tag in soup.find_all(string=re.compile("부가서비스 변경가능")):
    p = tag.parent
    print(f"  태그: <{p.name}> | 부모: <{p.parent.name}> | 클래스: {p.parent.get('class')}")
    print(f"  내용 앞부분: {p.get_text(strip=True)[:80]}")
    print()

# ── 2. "Platinum" 섹션 구조
print("[2] Platinum 영역")
for tag in soup.find_all(string=re.compile("Platinum")):
    p = tag.parent
    if p.name in ["h3", "h4", "strong", "b", "dt"]:
        print(f"  태그: <{p.name}> | 클래스: {p.get('class')}")
        print(f"  내용: {p.get_text(strip=True)[:80]}")
        print()

# ── 3. dl/dt/dd 구조 확인 (부가서비스 설명 영역)
print("[3] dl/dt/dd 구조")
for dl in soup.find_all("dl")[:5]:
    dt = dl.find("dt")
    dd = dl.find("dd")
    if dt:
        print(f"  dt: {dt.get_text(strip=True)[:50]}")
    if dd:
        print(f"  dd: {dd.get_text(strip=True)[:80]}")
    print()

# ── 4. 카드발급 유의사항 구조
print("[4] 카드발급 유의사항 영역")
for tag in soup.find_all(string=re.compile("카드발급 유의사항")):
    p = tag.parent
    print(f"  태그: <{p.name}> | 클래스: {p.get('class')}")
    # 부모의 전체 텍스트
    container = p.parent
    print(f"  컨테이너: <{container.name}> | 클래스: {container.get('class')}")
    print(f"  내용: {container.get_text(strip=True)[:200]}")
    print()

# ── 5. 전체 섹션 클래스 파악 (혜택 자세히보기 이후)
print("[5] 혜택 자세히보기 이후 주요 태그 구조")
detail_h3 = soup.find("h3", string=re.compile("혜택 자세히보기"))
if detail_h3:
    count = 0
    for el in detail_h3.find_all_next():
        if el.name in ["h3", "h4", "dt", "section", "article", "div"]:
            cls = el.get("class", [])
            txt = el.get_text(strip=True)[:40]
            print(f"  <{el.name}> class={cls} | {txt}")
            count += 1
            if count > 40:
                print("  ... (이하 생략)")
                break