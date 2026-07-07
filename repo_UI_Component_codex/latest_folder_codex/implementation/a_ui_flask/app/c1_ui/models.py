# -*- coding: utf-8 -*-
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Category(str, Enum):
    SPORTS = "スポーツ"
    CREATIVE = "制作"
    STUDY = "学習"
    OTHER = "その他"


@dataclass(frozen=True)
class CommunitySummary:
    community_id: str
    name: str
    category: str
    summary: str
    image_url: str | None
    updated_at: datetime
    can_edit: bool = False
    can_delete: bool = False


@dataclass(frozen=True)
class CommunityDetail(CommunitySummary):
    content: str = ""
    contact: str = ""
    created_at: datetime | None = None


@dataclass(frozen=True)
class CommunityFormData:
    name: str
    category: str
    summary: str
    content: str
    contact: str = ""
    image_url: str | None = None


def validate_community_form(data: CommunityFormData) -> dict[str, str]:
    errors: dict[str, str] = {}

    if not data.name.strip():
        errors["name"] = "コミュニティ名を入力してください。"

    if not data.content.strip():
        errors["content"] = "コミュニティ内容を入力してください。"

    if data.category not in {item.value for item in Category}:
        errors["category"] = "カテゴリを選択してください。"

    limits = {
        "name": 80,
        "summary": 160,
        "content": 2000,
    }
    values = {
        "name": data.name,
        "summary": data.summary,
        "content": data.content,
    }
    for field, limit in limits.items():
        if len(values[field]) > limit:
            errors[field] = f"{limit}文字以内で入力してください。"

    return errors
