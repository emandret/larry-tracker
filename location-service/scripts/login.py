"""One-off interactive Apple login, run locally (not in Docker) to seed a session.

2FA can't be completed headlessly inside a container, so this script logs in
once on your machine and writes the resulting session to ../data/account.json.
The location-service container then mounts that file and reuses the session,
re-authenticating only when Apple invalidates it.

Usage:
    cd location-service
    uv run scripts/login.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from findmy import (
    AsyncAppleAccount,
    LocalAnisetteProvider,
    LoginState,
    RemoteAnisetteProvider,
    SmsSecondFactorMethod,
    TrustedDeviceSecondFactorMethod,
)

STORE_PATH = Path(__file__).parent.parent.parent / "data" / "account.json"
ANISETTE_LIBS_PATH = Path(__file__).parent.parent.parent / "data" / "ani_libs.bin"

# Optional: set to use a remote anisette server instead of the built-in local one.
ANISETTE_SERVER_URL = os.environ.get("FINDMY_ANISETTE_SERVER_URL") or None


async def main() -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    anisette = (
        RemoteAnisetteProvider(ANISETTE_SERVER_URL)
        if ANISETTE_SERVER_URL
        else LocalAnisetteProvider(libs_path=str(ANISETTE_LIBS_PATH))
    )
    account = AsyncAppleAccount(anisette)

    email = input("Apple ID email: ")
    password = input("Apple ID password: ")

    state = await account.login(email, password)

    if state == LoginState.REQUIRE_2FA:
        methods = await account.get_2fa_methods()
        for i, method in enumerate(methods):
            if isinstance(method, TrustedDeviceSecondFactorMethod):
                print(f"{i} - Trusted Device")
            elif isinstance(method, SmsSecondFactorMethod):
                print(f"{i} - SMS ({method.phone_number})")

        method = methods[int(input("Method? > "))]
        await method.request()
        code = input("Code? > ")
        await method.submit(code)

    account.to_json(str(STORE_PATH))
    print(f"Logged in as {account.account_name}. Session saved to {STORE_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
