"""
Получение session string для telegram-mcp через QR-код.

Что делает:
  1. Спрашивает API ID и API Hash (из my.telegram.org).
  2. Показывает QR-код — сканируете его в Telegram на телефоне:
     Настройки → Устройства → Подключить устройство.
  3. Если включена двухэтапная аутентификация — спрашивает облачный пароль.
  4. Сохраняет API ID, API Hash и session string прямо в Связку ключей macOS.
     Session string на экран НЕ выводится — его не надо копировать руками
     и он не попадёт в запись экрана.

Запуск (из папки telegram-mcp, после установки окружения):
  .venv/bin/pip install qrcode
  .venv/bin/python /путь/к/session_qr.py

Идея и QR-подход — из навыка telegram-mcp-setup (Bayram Annakov, MIT).
"""

import asyncio
import getpass
import subprocess
import sys

SERVICE = "telegram-mcp"


def save_to_keychain(account: str, value: str) -> None:
    subprocess.run(
        ["security", "add-generic-password", "-a", account, "-s", SERVICE, "-w", value, "-U"],
        check=True,
    )


async def main() -> None:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    from telethon.sessions import StringSession

    api_id = int(input("API ID: ").strip())
    api_hash = input("API Hash: ").strip()

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()

    try:
        import qrcode
    except ImportError:
        qrcode = None
        print("Пакет qrcode не установлен — покажу ссылку, её можно превратить в QR любым генератором.")

    while True:
        qr_login = await client.qr_login()
        if qrcode:
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
            qr.add_data(qr_login.url)
            qr.make(fit=True)
            print("\nОтсканируйте в Telegram: Настройки → Устройства → Подключить устройство\n")
            qr.print_ascii(invert=True)
        else:
            print(f"\n{qr_login.url}\n")

        try:
            print("Жду сканирования (код живёт 30 секунд)...")
            await qr_login.wait(timeout=30)
            break
        except asyncio.TimeoutError:
            print("QR-код истёк, рисую новый.")
        except SessionPasswordNeededError:
            password = getpass.getpass("Включена двухэтапная аутентификация. Облачный пароль: ")
            await client.sign_in(password=password)
            break

    session = client.session.save()
    me = await client.get_me()
    await client.disconnect()

    if len(session) < 100:
        sys.exit("Session string подозрительно короткий — что-то пошло не так. Запустите скрипт ещё раз.")

    save_to_keychain("api_id", str(api_id))
    save_to_keychain("api_hash", api_hash)
    save_to_keychain("session_string", session)

    name = me.first_name or me.username or "аккаунт"
    print(f"\nГотово. Вошли как {name}. Ключи сохранены в Связку ключей (сервис «{SERVICE}»).")


if __name__ == "__main__":
    asyncio.run(main())
