# saver.py - CSV 저장

import pandas as pd

def _escape_excel(val):
    if isinstance(val, str) and val.startswith(("-", "=", "+", "@")):
        return "'" + val
    return val

def save_card_info(card_info: dict | list, filepath: str):
    df = pd.DataFrame([card_info] if isinstance(card_info, dict) else card_info)
    cols = [
        "card_id",
        "company",
        "card_name",
        "card_type",
        "network",
        "is_domestic_foreign",
        "has_transport",
        "annual_fee_dom_basic",
        "annual_fee_dom_premium",
        "annual_fee_for_basic",
        "annual_fee_for_premium",
        "annual_fee_notes",
        "min_performance",
        "summary",
        "image_url",
        "link_url",
        "has_cashback",
        "updated_at",
    ]
    df = df.reindex(columns=cols)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"  저장 완료: {filepath}")


def save_benefits(benefit_rows: list, filepath: str):
    cols = [
        "benefit_id",
        "card_id",
        "row_type",
        "benefit_group",
        "benefit_title",
        "benefit_summary",
        "benefit_content",
        "category",
        "category_id",
        "on_offline",
        "benefit_type",
        "benefit_value",
        "benefit_unit",
        "target_merchants",
        "excluded_merchants",
        "performance_level",
        "performance_min",
        "performance_max",
        "min_amount",
        "max_count",
        "max_limit",
        "max_limit_unit",
        "updated_at",
        "benefit_main_title",
    ]
    df = pd.DataFrame(benefit_rows)
    df = df.reindex(columns=cols)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"  저장 완료: {filepath} ({len(df)}행)")


def save_notices(notice_rows: list, filepath: str):
    df = pd.DataFrame(notice_rows)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"  저장 완료: {filepath} ({len(df)}행)")


def save_events(event_rows: list, filepath: str):
    if not event_rows:
        print("  이벤트 없음 - 저장 생략")
        return
    cols = [
        "card_id",
        "company",
        "card_name",
        "origin_event_code",
        "event_title",
        "event_link",
        "start_date",
        "end_date",
        "event_type",
        "section",
        "event_content",
        "updated_at",
    ]
    df = pd.DataFrame(event_rows, columns=cols)
    df["event_content"] = df["event_content"].map(_escape_excel)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"  저장 완료: {filepath} ({len(df)}행)")