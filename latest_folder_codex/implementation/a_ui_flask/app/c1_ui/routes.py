# -*- coding: utf-8 -*-
from urllib.parse import urlencode

from flask import (
    Blueprint,
    current_app,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.c1_ui.google_oauth import (
    build_authorize_url,
    exchange_code_for_id_token,
    google_oauth_configured,
    issue_oauth_state,
    validate_oauth_state,
)
from app.c1_ui.models import Category, CommunityFormData, validate_community_form
from app.c1_ui.service_clients import (
    AuthServiceClient,
    AuthServiceRejected,
    AuthServiceUnavailable,
    CommunityServiceClient,
    CommunityServiceRejected,
    CommunityServiceUnavailable,
)


c1_ui = Blueprint("c1_ui", __name__)


THEME_STYLESHEETS = {
    "classic": None,
    "campus": "theme-campus.css",
    "social": "theme-social.css",
    "compact": "theme-compact.css",
}


def auth_token() -> str | None:
    return request.cookies.get(current_app.config["AUTH_COOKIE_NAME"])


def current_user_id() -> str | None:
    return request.cookies.get("user_id") or current_app.config.get("COMMUNITY_CREATOR_USER_ID")


def mock_auth_enabled() -> bool:
    return bool(current_app.config.get("AUTH_MOCK_ENABLED"))


def mock_auth_tokens() -> set[str]:
    return {"mock-user-token", "mock-admin-token"}


UNIVERSITY_EMAIL_DOMAIN = "@shibaura-it.ac.jp"


def validate_university_email(email: str) -> str | None:
    normalized = (email or "").strip().lower()
    if not normalized or "@" not in normalized:
        return "メールアドレスを入力してください。"
    if not normalized.endswith(UNIVERSITY_EMAIL_DOMAIN):
        return "芝浦工業大学のメールアドレス（@shibaura-it.ac.jp）のみ利用できます。"
    return None


def is_valid_auth_token(token: str | None) -> bool:
    if not token:
        return False
    if token in mock_auth_tokens():
        return False
    if not current_app.config.get("AUTH_SERVICE_BASE_URL") and current_app.config.get("TESTING"):
        return True
    return AuthServiceClient().verify_token(token) is not None


def clear_auth_cookies(response):
    response.delete_cookie(current_app.config["AUTH_COOKIE_NAME"])
    response.delete_cookie("user_id")
    return response


def login_redirect(*, error: str | None = None, clear_cookies: bool = False):
    params = {}
    if error:
        params["error"] = error
    location = url_for("c1_ui.show_login")
    if params:
        location = f"{location}?{urlencode(params)}"
    response = make_response(redirect(location))
    if clear_cookies:
        clear_auth_cookies(response)
    return response


def require_auth():
    if not current_app.config.get("REQUIRE_AUTH_TOKEN", True):
        return None
    token = auth_token()
    if is_valid_auth_token(token):
        return None
    return login_redirect(
        error="ログインしてください。",
        clear_cookies=bool(token),
    )


def template_context(**extra):
    theme = request.args.get("theme", "classic")
    if theme not in THEME_STYLESHEETS:
        theme = "classic"
    return {
        "auth_token": auth_token(),
        "categories": [item.value for item in Category],
        "show_new_button": True,
        "selected_theme": theme,
        "theme_stylesheet": THEME_STYLESHEETS[theme],
        **extra,
    }


@c1_ui.get("/")
def root():
    guard = require_auth()
    if guard:
        return guard
    return redirect(url_for("c1_ui.show_home"))


@c1_ui.get("/login")
def show_login():
    if request.args.get("force") in {"1", "true"}:
        response = make_response(redirect(url_for("c1_ui.show_login")))
        return clear_auth_cookies(response)
    if is_valid_auth_token(auth_token()):
        return redirect(url_for("c1_ui.show_home"))

    return render_template(
        "login.html",
        **template_context(
            title="ログイン",
            heading="大学メールアドレスでログイン" if mock_auth_enabled() else "大学Googleアカウントでログイン",
            body=(
                "芝浦工大のメールアドレスを入力してログインする。"
                if mock_auth_enabled()
                else "認証はGoogleの画面で行う。本システムはパスワードを保持・処理しない。"
            ),
            button_label="大学Googleアカウントでログイン",
            login_url=url_for("c1_ui.request_login"),
            email_login_url=url_for("c1_ui.submit_email_login"),
            email_login_mode=mock_auth_enabled(),
            error=request.args.get("error"),
            admin_mode=False,
            show_new_button=False,
        ),
    )


@c1_ui.get("/logout")
def logout():
    return login_redirect(error="ログアウトしました。", clear_cookies=True)


@c1_ui.get("/login/google")
def request_login():
    if mock_auth_enabled():
        return redirect(url_for("c1_ui.show_login"))
    return _start_google_login(admin=False)


@c1_ui.get("/admin/login/google")
def request_admin_login():
    if mock_auth_enabled():
        return redirect(url_for("c1_ui.show_admin_login"))
    return _start_google_login(admin=True)


def _start_google_login(*, admin: bool):
    if google_oauth_configured():
        state = issue_oauth_state(admin=admin)
        return redirect(build_authorize_url(admin=admin, state=state))

    login_endpoint = "c1_ui.show_admin_login" if admin else "c1_ui.show_login"
    fallback_key = "AUTH_ADMIN_GOOGLE_LOGIN_URL" if admin else "AUTH_GOOGLE_LOGIN_URL"
    fallback_url = current_app.config[fallback_key]
    if fallback_url.startswith("/not-implemented"):
        return redirect(
            f"{url_for(login_endpoint)}?{urlencode({'error': 'Google OAuthが未設定です。.envにGOOGLE_CLIENT_IDとGOOGLE_CLIENT_SECRETを設定してください。'})}"
        )
    return redirect(fallback_url)


@c1_ui.get("/admin/login")
def show_admin_login():
    return render_template(
        "login.html",
        **template_context(
            title="管理者用ログイン",
            heading="管理者用メールアドレスでログイン" if mock_auth_enabled() else "管理者用Googleログイン",
            body=(
                "管理者として登録済みの芝浦工大メールアドレスを入力してログインする。"
                if mock_auth_enabled()
                else "Google認証後、F1ログイン情報を参照して管理者権限を確認する。"
            ),
            button_label="管理者用Googleログイン",
            login_url=url_for("c1_ui.request_admin_login"),
            email_login_url=url_for("c1_ui.submit_admin_email_login"),
            email_login_mode=mock_auth_enabled(),
            error=request.args.get("error"),
            admin_mode=True,
            show_new_button=False,
        ),
    )


@c1_ui.post("/login/email")
def submit_email_login():
    return _submit_email_login(admin=False)


@c1_ui.post("/admin/login/email")
def submit_admin_email_login():
    return _submit_email_login(admin=True)


def _submit_email_login(*, admin: bool):
    login_endpoint = "c1_ui.show_admin_login" if admin else "c1_ui.show_login"
    email = request.form.get("email", "")
    validation_error = validate_university_email(email)
    if validation_error:
        return redirect(f"{url_for(login_endpoint)}?{urlencode({'error': validation_error})}")

    try:
        auth_result = AuthServiceClient().login(
            google_auth={
                "email": email.strip().lower(),
                "mock_email_auth": "1",
            },
            fallback_auth_token=None,
            admin=admin,
        )
    except (AuthServiceUnavailable, AuthServiceRejected) as exc:
        message = str(exc) or "ログインに失敗しました。"
        return redirect(f"{url_for(login_endpoint)}?{urlencode({'error': message})}")

    response = make_response(redirect(url_for("c1_ui.show_home")))
    response.set_cookie(
        current_app.config["AUTH_COOKIE_NAME"],
        auth_result.auth_token,
        httponly=True,
        samesite="Lax",
    )
    if auth_result.user_id:
        response.set_cookie(
            "user_id",
            auth_result.user_id,
            httponly=True,
            samesite="Lax",
        )
    return response


@c1_ui.get("/auth/google/callback")
def handle_google_oauth_callback():
    return _handle_google_oauth_callback(admin=False)


@c1_ui.get("/admin/auth/google/callback")
def handle_admin_google_oauth_callback():
    return _handle_google_oauth_callback(admin=True)


def _oauth_id_token_session_key(*, admin: bool) -> str:
    return "oauth_id_token_admin" if admin else "oauth_id_token_user"


def _handle_google_oauth_callback(*, admin: bool):
    login_endpoint = "c1_ui.show_admin_login" if admin else "c1_ui.show_login"
    auth_callback_endpoint = (
        "c1_ui.handle_admin_google_auth_result"
        if admin
        else "c1_ui.handle_google_auth_result"
    )
    error = request.args.get("error")
    if error:
        return redirect(f"{url_for(login_endpoint)}?{urlencode({'error': error})}")

    state = request.args.get("state")
    if not validate_oauth_state(admin=admin, state=state):
        return redirect(
            f"{url_for(login_endpoint)}?{urlencode({'error': 'Google認証の state が無効です。もう一度ログインしてください。'})}"
        )

    code = request.args.get("code")
    if not code:
        return redirect(
            f"{url_for(login_endpoint)}?{urlencode({'error': 'Google認証コードを取得できない。'})}"
        )

    try:
        token_payload = exchange_code_for_id_token(code=code, admin=admin)
    except ValueError:
        return redirect(
            f"{url_for(login_endpoint)}?{urlencode({'error': 'Google認証に失敗した。'})}"
        )

    session[_oauth_id_token_session_key(admin=admin)] = token_payload["id_token"]
    return redirect(url_for(auth_callback_endpoint))


@c1_ui.get("/auth/callback")
def handle_google_auth_result():
    return handle_auth_callback(admin=False)


@c1_ui.get("/admin/auth/callback")
def handle_admin_google_auth_result():
    return handle_auth_callback(admin=True)


def handle_auth_callback(*, admin: bool):
    error = request.args.get("error")
    login_endpoint = "c1_ui.show_admin_login" if admin else "c1_ui.show_login"
    if error:
        return redirect(f"{url_for(login_endpoint)}?{urlencode({'error': error})}")

    session_key = _oauth_id_token_session_key(admin=admin)
    id_token = request.args.get("id_token") or session.pop(session_key, None)
    if not id_token:
        return redirect(
            f"{url_for(login_endpoint)}?{urlencode({'error': '認証情報を取得できませんでした。'})}"
        )

    google_auth = {
        "id_token": id_token,
        "email": request.args.get("email"),
        "google_user_id": request.args.get("google_user_id"),
    }

    try:
        auth_result = AuthServiceClient().login(
            google_auth=google_auth,
            fallback_auth_token=None,
            admin=admin,
        )
    except (AuthServiceUnavailable, AuthServiceRejected) as exc:
        message = error or "Google認証に失敗した。"
        if str(exc):
            message = str(exc)
        return redirect(f"{url_for(login_endpoint)}?{urlencode({'error': message})}")

    response = make_response(redirect(url_for("c1_ui.show_home")))
    response.set_cookie(
        current_app.config["AUTH_COOKIE_NAME"],
        auth_result.auth_token,
        httponly=True,
        samesite="Lax",
    )
    if auth_result.user_id:
        response.set_cookie(
            "user_id",
            auth_result.user_id,
            httponly=True,
            samesite="Lax",
        )
    return response


def mock_auth_params(*, admin: bool) -> dict[str, str]:
    if admin:
        return {
            "email": current_app.config["AUTH_MOCK_ADMIN_EMAIL"],
            "user_id": current_app.config["AUTH_MOCK_ADMIN_USER_ID"],
            "mock_email_auth": "1",
        }
    return {
        "email": current_app.config["AUTH_MOCK_USER_EMAIL"],
        "user_id": current_app.config["AUTH_MOCK_USER_ID"],
        "mock_email_auth": "1",
    }


@c1_ui.get("/communities")
def show_home():
    guard = require_auth()
    if guard:
        return guard

    keyword = request.args.get("keyword") or None
    category = request.args.get("category") or None
    try:
        communities = CommunityServiceClient().get_community_list(
            keyword=keyword,
            category=category,
            auth_token=auth_token(),
        )
    except CommunityServiceUnavailable as exc:
        return (
            render_template(
                "message.html",
                **template_context(
                    title="一覧取得エラー",
                    heading="コミュニティ一覧を取得できない。",
                    message=str(exc),
                ),
            ),
            503,
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
            creator_user_id=current_user_id(),
        )
    except (CommunityServiceUnavailable, CommunityServiceRejected) as exc:
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
            getattr(exc, "status_code", 503),
        )

    return redirect(url_for("c1_ui.show_community_detail", community_id=community_id))


@c1_ui.get("/communities/<community_id>")
def show_community_detail(community_id: str):
    guard = require_auth()
    if guard:
        return guard

    try:
        community = CommunityServiceClient().get_community_detail(
            community_id=community_id,
            auth_token=auth_token(),
        )
    except CommunityServiceUnavailable as exc:
        return (
            render_template(
                "message.html",
                **template_context(
                    title="詳細取得エラー",
                    heading="コミュニティ詳細を取得できない。",
                    message=str(exc),
                ),
            ),
            503,
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

    try:
        community = CommunityServiceClient().get_community_detail(
            community_id=community_id,
            auth_token=auth_token(),
        )
    except CommunityServiceUnavailable as exc:
        return (
            render_template(
                "message.html",
                **template_context(
                    title="詳細取得エラー",
                    heading="コミュニティ詳細を取得できない。",
                    message=str(exc),
                ),
            ),
            503,
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
    except (CommunityServiceUnavailable, CommunityServiceRejected) as exc:
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
            getattr(exc, "status_code", 503),
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
    except (CommunityServiceUnavailable, CommunityServiceRejected) as exc:
        return (
            render_template(
                "message.html",
                **template_context(
                    title="削除未接続",
                    heading="コミュニティ削除を完了できない。",
                    message=str(exc),
                ),
            ),
            getattr(exc, "status_code", 503),
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
        contact="",
        image_url=request.form.get("image_url") or None,
    )
