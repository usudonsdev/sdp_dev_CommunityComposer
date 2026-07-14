"""ログイン処理向けの共有スレッドプール。

CPU バウンドなパスワード検証や外部 I/O（Google 検証・SMTP）を
リクエストスレッドから切り離し、200 ユーザー規模の同時ログインでも
他リクエストをブロックしにくくする。
"""
from __future__ import annotations

import atexit
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Callable, TypeVar

from flask import Flask, current_app

T = TypeVar("T")

_executor: ThreadPoolExecutor | None = None
_DEFAULT_MAX_WORKERS = 16


def get_login_executor(app: Flask | None = None) -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        if app is None:
            app = current_app._get_current_object()
        max_workers = int(app.config.get("LOGIN_EXECUTOR_MAX_WORKERS", _DEFAULT_MAX_WORKERS))
        _executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="login-worker",
        )
    return _executor


def shutdown_login_executor() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None


def run_login_task(fn: Callable[..., T], /, *args, **kwargs) -> T:
    """ブロッキングなログイン処理を共有プールで実行し、結果を待つ。"""
    app = current_app._get_current_object()
    timeout = float(app.config.get("LOGIN_TASK_TIMEOUT_SECONDS", 30))

    def _wrapped() -> T:
        with app.app_context():
            return fn(*args, **kwargs)

    future = get_login_executor(app).submit(_wrapped)
    try:
        return future.result(timeout=timeout)
    except FuturesTimeoutError as exc:
        future.cancel()
        raise TimeoutError("ログイン処理がタイムアウトしました。") from exc


def submit_login_task(fn: Callable[..., T], /, *args, **kwargs):
    """結果を待たずにバックグラウンドで実行する（メール送信など）。"""
    app = current_app._get_current_object()

    def _wrapped() -> T:
        with app.app_context():
            return fn(*args, **kwargs)

    return get_login_executor(app).submit(_wrapped)


def init_login_executor(app: Flask) -> None:
    """アプリ起動時にプールを初期化し、終了時に解放する。"""
    get_login_executor(app)
    atexit.register(shutdown_login_executor)
