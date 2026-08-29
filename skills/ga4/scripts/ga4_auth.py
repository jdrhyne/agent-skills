#!/usr/bin/env python3
"""Protected installed-app OAuth setup for read-only GA4 Data API access."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any


SCOPES = ("https://www.googleapis.com/auth/analytics.readonly",)
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "ga4"
DEFAULT_CLIENT_FILE = DEFAULT_CONFIG_DIR / "client_secret.json"
DEFAULT_TOKEN_FILE = DEFAULT_CONFIG_DIR / "token.json"


class AuthError(RuntimeError):
    """Safe, non-secret authentication configuration error."""


def local_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else Path.cwd() / path


def require_private_directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise AuthError(f"credential directory must be a real directory: {path}")
    info = path.stat()
    if info.st_uid != os.getuid():
        raise AuthError(f"credential directory must be owned by the current user: {path}")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise AuthError(f"credential directory must reject group and other access: {path}")


def ensure_private_directory(path: Path) -> None:
    if not path.exists():
        old_umask = os.umask(0o077)
        try:
            path.mkdir(mode=0o700, parents=True)
        finally:
            os.umask(old_umask)
    require_private_directory(path)


def require_private_file(path_value: str | os.PathLike[str]) -> Path:
    path = local_path(path_value)
    require_private_directory(path.parent)
    if path.is_symlink() or not path.is_file():
        raise AuthError(f"credential file must be a regular non-symbolic-link file: {path}")
    info = path.stat()
    if info.st_uid != os.getuid():
        raise AuthError(f"credential file must be owned by the current user: {path}")
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise AuthError(f"credential file must have mode 0600: {path}")
    return path


def validate_installed_client_file(path_value: str | os.PathLike[str]) -> Path:
    path = require_private_file(path_value)
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuthError("client credential JSON is unreadable or malformed") from exc
    installed = payload.get("installed") if isinstance(payload, dict) else None
    if not isinstance(installed, dict):
        raise AuthError("client credential JSON must contain a Desktop app 'installed' object")
    for field in ("client_id", "client_secret", "auth_uri", "token_uri"):
        if not isinstance(installed.get(field), str) or not installed[field]:
            raise AuthError(f"client credential JSON is missing installed.{field}")
    return path


def write_private_token(path_value: str | os.PathLike[str], payload: str) -> Path:
    path = local_path(path_value)
    ensure_private_directory(path.parent)
    if path.exists():
        require_private_file(path)
    elif path.is_symlink():
        raise AuthError(f"token path must not be a symbolic link: {path}")
    descriptor = -1
    temporary = ""
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=".token-", dir=path.parent, text=True)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = ""
        os.chmod(path, 0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
    return path


def load_stored_credentials(path_value: str | os.PathLike[str]):
    path = require_private_file(path_value)
    try:
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise AuthError("Google OAuth dependencies are not installed; use requirements.txt") from exc
    try:
        return Credentials.from_authorized_user_file(str(path), scopes=SCOPES)
    except Exception as exc:
        raise AuthError("stored OAuth token is unreadable or invalid; re-run ga4_auth.py") from exc


def parse_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be 0 or an integer from 1024 to 65535") from exc
    if port != 0 and not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be 0 or an integer from 1024 to 65535")
    return port


def authorize(client_file: Path, token_file: Path, port: int) -> Path:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise AuthError("Google OAuth dependencies are not installed; use requirements.txt") from exc
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_file), scopes=SCOPES)
        credentials = flow.run_local_server(
            host="127.0.0.1",
            port=port,
            open_browser=True,
            access_type="offline",
            prompt="consent",
            authorization_prompt_message="Complete authorization in the browser window.",
            success_message="Authorization complete. You may close this browser window.",
        )
        token_json = credentials.to_json()
    except Exception as exc:
        raise AuthError("interactive OAuth failed; no token was written") from exc
    return write_private_token(token_file, token_json)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    forbidden = {"--access-token", "--authorization-code", "--client-secret", "--code", "--refresh-token"}
    if any(argument.split("=", 1)[0] in forbidden for argument in arguments):
        print("Error: credential values and authorization codes must not be passed in arguments", file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser(description="Authorize read-only GA4 Data API access", allow_abbrev=False)
    parser.add_argument("--client-secrets", default=str(DEFAULT_CLIENT_FILE), help="protected Desktop OAuth client JSON path")
    parser.add_argument("--token-file", default=str(DEFAULT_TOKEN_FILE), help="protected token JSON destination")
    parser.add_argument("--port", type=parse_port, default=0, help="loopback port; 0 selects an available port")
    args = parser.parse_args(arguments)
    try:
        client_file = validate_installed_client_file(args.client_secrets)
        token_file = authorize(client_file, local_path(args.token_file), args.port)
    except AuthError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Authorization complete. Protected credentials stored at {token_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
