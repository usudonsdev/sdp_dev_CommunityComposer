# -*- coding: utf-8 -*-
from urllib.parse import urlencode

from flask import (
    Blueprint,
    current_app,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from app.c1_ui.models import Category, CommunityFormData, validate_community_form
from app.c1_ui.service_clients import CommunityServiceClient, CommunityServiceUnavailable


c1_ui = Blueprint("c1_ui", __name__)


def auth_token() -> str | None:
    return request.cookies.get(current_app.config["AUTH_COOKIE_NAME"])


def require_auth():
    if not current_app.config.get("REQUIRE_AUTH_TOKEN", True):
        return None
    if auth_token():
        return None
    return redirect(
        f"{url_for('c1_ui.show_login')}?{urlencode({'error': 'ログインしてください。'})}"
    )


def template_context(**extra):
    return {
        "auth_token": auth_token(),
        "categories": [item.value for item in Category],
        "show_new_button": True,
        **extra,
    }


@c1_ui.get("/")
def root():
    return redirect(url_for("c1_ui.show_home"))


@c1_ui.get("/login")
def show_login():
    if auth_token():
        return redirect(url_for("c1_ui.show_home"))

    return render_template(
        "login.html",
        **template_context(
            title="ログイン",
            heading="大学Googleアカウントでログイン",
            body="認証はGoogleの画面で行う。本システムはパスワードを保持・処理しない。",
            button_label="大学Googleアカウントでログイン",
            login_url=url_for("c1_ui.request_login"),
            error=request.args.get("error"),
            admin_mode=False,
            show_new_button=False,
        ),
    )


@c1_ui.get("/login/google")
def request_login():
    return redirect(current_app.config["AUTH_GOOGLE_LOGIN_URL"])


@c1_ui.get("/admin/login")
def show_admin_login():
    return render_template(
        "login.html",
        **template_context(
            title="管理者用ログイン",
            heading="管理者用Googleログイン",
            body="Google認証後、F1ログイン情報を参照して管理者権限を確認する。",
            button_label="管理者用Googleログイン",
            login_url=url_for("c1_ui.request_admin_login"),
            error=request.args.get("error"),
            admin_mode=True,
            show_new_button=False,
        ),
    )


@c1_ui.get("/admin/login/google")
def request_admin_login():
    return redirect(current_app.config["AUTH_ADMIN_GOOGLE_LOGIN_URL"])


@c1_ui.get("/auth/callback")
def handle_google_auth_result():
    token = request.args.get("auth_token")
    error = request.args.get("error")
    if error or not token:
        message = error or "Google認証に失敗した。"
        return redirect(f"{url_for('c1_ui.show_login')}?{urlencode({'error': message})}")

    response = make_response(redirect(url_for("c1_ui.show_home")))
    response.set_cookie(
        current_app.config["AUTH_COOKIE_NAME"],
        token,
        httponly=True,
        samesite="Lax",
    )
    return response


@c1_ui.get("/communities")
def show_home():
    guard = require_auth()
    if guard:
        return guard

    keyword = request.args.get("keyword") or None
    category = request.args.get("category") or None
    communities = CommunityServiceClient().get_community_list(
        keyword=keyword,
        category=category,
        auth_token=auth_token(),
    )
    return render_template(
        "home.html",
        **template_context(
            title="メイン画面",
            communities=communities,
            keyword=keyword or "",
            selected_category=category or "",
        ),
    )


@c1_ui.get("/communities/new")
def show_create_form():
    guard = require_auth()
    if guard:
        return guard

    form = CommunityFormData(
        name="",
        category=Category.CREATIVE.value,
        summary="",
        content="",
        contact="",
    )
    return render_template(
        "community_form.html",
        **template_context(
            title="コミュニティ作成・編集画面",
            form=form,
            errors={},
            action=url_for("c1_ui.save_community"),
            mode="new",
            service_message=None,
        ),
    )


@c1_ui.post("/communities")
def save_community():
    guard = require_auth()
    if guard:
        return guard

    form = form_data_from_request()
    errors = validate_community_form(form)
    if errors:
        return (
            render_template(
                "community_form.html",
                **template_context(
                    title="コミュニティ作成・編集画面",
                    form=form,
                    errors=errors,
                    action=url_for("c1_ui.save_community"),
                    mode="new",
                    service_message=None,
                ),
            ),
            400,
        )

    try:
        community_id = CommunityServiceClient().save_community(
            data=form,
            auth_token=auth_token(),
        )
    except CommunityServiceUnavailable as exc:
        return (
            render_template(
                "community_form.html",
                **template_context(
                    title="コミュニティ作成・編集画面",
                    form=form,
                    errors={},
                    action=url_for("c1_ui.save_community"),
                    mode="new",
                    service_message=str(exc),
                ),
            ),
            503,
        )

    return redirect(url_for("c1_ui.show_community_detail", community_id=community_id))


@c1_ui.get("/communities/<community_id>")
def show_community_detail(community_id: str):
    guard = require_auth()
    if guard:
        return guard

    community = CommunityServiceClient().get_community_detail(
        community_id=community_id,
        auth_token=auth_token(),
    )
    if community is None:
        return (
            render_template(
                "message.html",
                **template_context(
                    title="対象なし",
                    heading="対象コミュニティが存在しない。",
                    message="メイン画面に戻って、コミュニティを選択し直してください。",
                ),
            ),
            404,
        )

    return render_template(
        "community_detail.html",
        **template_context(title=community.name, community=community),
    )


@c1_ui.get("/communities/<community_id>/edit")
def show_edit_form(community_id: str):
    guard = require_auth()
    if guard:
        return guard

    community = CommunityServiceClient().get_community_detail(
        community_id=community_id,
        auth_token=auth_token(),
    )
    if community is None:
        return (
            render_template(
                "message.html",
                **template_context(
                    title="対象なし",
                    heading="対象コミュニティが存在しない。",
                    message="メイン画面に戻って、コミュニティを選択し直してください。",
                ),
            ),
            404,
        )

    form = CommunityFormData(
        name=community.name,
        category=community.category,
        summary=community.summary,
        content=community.content,
        contact=community.contact,
        image_url=community.image_url,
    )
    return render_template(
        "community_form.html",
        **template_context(
            title="コミュニティ作成・編集画面",
            form=form,
            errors={},
            action=url_for("c1_ui.update_community", community_id=community_id),
            mode="edit",
            service_message=None,
        ),
    )


@c1_ui.post("/communities/<community_id>")
def update_community(community_id: str):
    guard = require_auth()
    if guard:
        return guard

    form = form_data_from_request()
    errors = validate_community_form(form)
    if errors:
        return (
            render_template(
                "community_form.html",
                **template_context(
                    title="コミュニティ作成・編集画面",
                    form=form,
                    errors=errors,
                    action=url_for("c1_ui.update_community", community_id=community_id),
                    mode="edit",
                    service_message=None,
                ),
            ),
            400,
        )

    try:
        saved_id = CommunityServiceClient().save_community(
            data=form,
            auth_token=auth_token(),
            community_id=community_id,
        )
    except CommunityServiceUnavailable as exc:
        return (
            render_template(
                "community_form.html",
                **template_context(
                    title="コミュニティ作成・編集画面",
                    form=form,
                    errors={},
                    action=url_for("c1_ui.update_community", community_id=community_id),
                    mode="edit",
                    service_message=str(exc),
                ),
            ),
            503,
        )

    return redirect(url_for("c1_ui.show_community_detail", community_id=saved_id))


@c1_ui.post("/communities/<community_id>/delete")
def request_delete_community(community_id: str):
    guard = require_auth()
    if guard:
        return guard

    try:
        CommunityServiceClient().delete_community(
            community_id=community_id,
            auth_token=auth_token(),
        )
    except CommunityServiceUnavailable as exc:
        return (
            render_template(
                "message.html",
                **template_context(
                    title="削除未接続",
                    heading="C3コミュニティ活動処理部が未接続である。",
                    message=str(exc),
                ),
            ),
            503,
        )

    return redirect(url_for("c1_ui.show_home"))


@c1_ui.get("/not-implemented/<path:name>")
def not_implemented(name: str):
    return (
        render_template(
            "message.html",
            **template_context(
                title="未接続",
                heading="外部処理部が未接続である。",
                message=f"{name} は後続担当の処理部と接続後に動作する。",
                show_new_button=False,
            ),
        ),
        501,
    )


def form_data_from_request() -> CommunityFormData:
    return CommunityFormData(
        name=request.form.get("name", ""),
        category=request.form.get("category", ""),
        summary=request.form.get("summary", ""),
        content=request.form.get("content", ""),
        contact=request.form.get("contact", ""),
        image_url=request.form.get("image_url") or None,
    )
