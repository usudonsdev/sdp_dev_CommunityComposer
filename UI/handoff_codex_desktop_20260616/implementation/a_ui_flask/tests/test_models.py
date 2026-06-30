import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.c1_ui.models import CommunityFormData, validate_community_form


def test_validate_community_form_requires_name_and_content():
    data = CommunityFormData(
        name="",
        category="制作",
        summary="UI設計を学ぶ",
        content="",
        contact="sit-web@example.com",
    )

    errors = validate_community_form(data)

    assert "name" in errors
    assert "content" in errors


def test_validate_community_form_accepts_valid_input():
    data = CommunityFormData(
        name="Web制作研究会",
        category="制作",
        summary="UI設計と実装を一緒に学ぶ。",
        content="週に1回、Web制作を学ぶ。",
        contact="sit-web@example.com",
    )

    errors = validate_community_form(data)

    assert errors == {}


def test_validate_community_form_checks_length_limit():
    data = CommunityFormData(
        name="あ" * 81,
        category="制作",
        summary="概要",
        content="内容",
        contact="sit-web@example.com",
    )

    errors = validate_community_form(data)

    assert "name" in errors


def test_validate_community_form_rejects_unknown_category():
    data = CommunityFormData(
        name="Web制作研究会",
        category="未選択",
        summary="UI設計と実装を一緒に学ぶ。",
        content="週に1回、Web制作を学ぶ。",
        contact="sit-web@example.com",
    )

    errors = validate_community_form(data)

    assert "category" in errors
