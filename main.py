import os
import asyncio
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", "10000"))

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

ADMIN_ID = 1145626218

# اگر خواستی بعداً از Render تنظیمش کنی
ENV_BUSINESS_CONNECTION_ID = os.getenv("BUSINESS_CONNECTION_ID")

# =========================================================
# PROVIDERS
# =========================================================

PROVIDERS = {
    "HVPN": {
        "username": "@H_VPNbot",
        "chat_id": 6683626212,
    },

    # فعلاً Chat ID دو سرویس دیگر را نداریم
    # بعد از تست از Business Message استخراج می‌کنیم
    "MXCloud": {
        "username": "@mxcloudbot",
        "chat_id": None,
    },

    "SVN": {
        "username": "@SvnProBot",
        "chat_id": None,
    },
}

dp = Dispatcher()

# Business connections دریافت‌شده
business_connections = {}


# =========================================================
# MENU
# =========================================================

def menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📱 سرویس‌های من"),
                KeyboardButton(text="📊 استعلام وضعیت"),
            ],
            [
                KeyboardButton(text="🛒 خرید سرویس"),
                KeyboardButton(text="🔄 تمدید سرویس"),
            ],
            [
                KeyboardButton(text="💰 کیف پول"),
                KeyboardButton(text="🎫 پشتیبانی"),
            ],
        ],
        resize_keyboard=True,
    )


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "سلام 👋\n"
        "به پنل خدمات VPN خوش آمدید.\n\n"
        "از منوی زیر سرویس‌های خود را مدیریت کنید.",
        reply_markup=menu(),
    )


# =========================================================
# BUSINESS CONNECTION
# =========================================================

@dp.business_connection()
async def business_connection_handler(
    business_connection: types.BusinessConnection,
):
    connection_id = business_connection.id

    business_connections[connection_id] = business_connection

    print("BUSINESS CONNECTION RECEIVED")
    print("ID:", connection_id)
    print("USER ID:", business_connection.user.id)
    print("USERNAME:", business_connection.user.username)
    print("CAN REPLY:", business_connection.can_reply)
    print("IS ENABLED:", business_connection.is_enabled)


def get_business_connection_id():
    if business_connections:
        return list(business_connections.keys())[-1]

    if ENV_BUSINESS_CONNECTION_ID:
        return ENV_BUSINESS_CONNECTION_ID

    return None


# =========================================================
# BUSINESS STATUS
# =========================================================

@dp.message(Command("business"))
async def business_status(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    connection_id = get_business_connection_id()

    if not connection_id:
        await message.answer(
            "❌ هیچ Business Connection پیدا نشد."
        )
        return

    connection = business_connections.get(connection_id)

    if connection:

        username = connection.user.username

        if username:
            username = "@" + username

        await message.answer(
            "✅ Business Connection فعال است.\n\n"
            f"Connection ID:\n{connection_id}\n\n"
            f"User ID: {connection.user.id}\n"
            f"Username: {username}\n"
            f"Can Reply: {connection.can_reply}\n"
            f"Enabled: {connection.is_enabled}"
        )

    else:

        await message.answer(
            "✅ Business Connection ID پیدا شد.\n\n"
            f"Connection ID:\n{connection_id}"
        )


# =========================================================
# SEND TO PROVIDER
# =========================================================

async def send_to_provider(
    bot: Bot,
    connection_id: str,
    provider_key: str,
    text: str,
):

    provider = PROVIDERS[provider_key]

    chat_id = provider["chat_id"]

    if not chat_id:
        raise RuntimeError(
            f"Chat ID برای {provider['username']} هنوز ثبت نشده است."
        )

    sent = await bot.send_message(
        business_connection_id=connection_id,
        chat_id=chat_id,
        text=text,
    )

    return sent


# =========================================================
# TEST HVPN
# =========================================================

@dp.message(Command("test_hvpn_business"))
async def test_hvpn_business(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    connection_id = get_business_connection_id()

    if not connection_id:
        await message.answer(
            "❌ Business Connection پیدا نشد."
        )
        return

    connection = business_connections.get(connection_id)

    if connection:

        if not connection.is_enabled:
            await message.answer(
                "❌ Business Connection غیرفعال است."
            )
            return

        if not connection.can_reply:
            await message.answer(
                "❌ Business Connection اجازه پاسخ دادن ندارد."
            )
            return

    await message.answer(
        "🟡 ارسال /start به H_VPNbot..."
    )

    try:

        sent = await send_to_provider(
            message.bot,
            connection_id,
            "HVPN",
            "/start",
        )

        await message.answer(
            "✅ پیام با موفقیت ارسال شد.\n\n"
            "Provider: @H_VPNbot\n"
            f"Chat ID: {PROVIDERS['HVPN']['chat_id']}\n"
            f"Message ID: {sent.message_id}\n\n"
            "⏳ منتظر پاسخ Provider هستیم."
        )

    except Exception as e:

        await message.answer(
            "❌ ارسال ناموفق بود.\n\n"
            f"Error Type:\n{type(e).__name__}\n\n"
            f"Error:\n{e}"
        )


# =========================================================
# TEST ALL PROVIDERS
# =========================================================

@dp.message(Command("test_business_all"))
async def test_business_all(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    connection_id = get_business_connection_id()

    if not connection_id:
        await message.answer(
            "❌ Business Connection پیدا نشد."
        )
        return

    connection = business_connections.get(connection_id)

    if connection:

        if not connection.is_enabled:
            await message.answer(
                "❌ Business Connection غیرفعال است."
            )
            return

        if not connection.can_reply:
            await message.answer(
                "❌ Business Connection اجازه ارسال ندارد."
            )
            return

    await message.answer(
        "🟡 تست Providerها شروع شد..."
    )

    results = []

    for provider_key, provider in PROVIDERS.items():

        if not provider["chat_id"]:

            results.append(
                f"🟡 {provider['username']}\n"
                "Chat ID هنوز ثبت نشده است."
            )

            continue

        try:

            sent = await send_to_provider(
                message.bot,
                connection_id,
                provider_key,
                "/start",
            )

            results.append(
                f"✅ {provider['username']}\n"
                f"Chat ID: {provider['chat_id']}\n"
                f"Message ID: {sent.message_id}"
            )

        except Exception as e:

            results.append(
                f"❌ {provider['username']}\n"
                f"{type(e).__name__}: {e}"
            )

        await asyncio.sleep(2)

    await message.answer(
        "📊 نتیجه تست Business:\n\n"
        + "\n\n".join(results)
    )


# =========================================================
# RECEIVE BUSINESS MESSAGES
# =========================================================

@dp.business_message()
async def business_message_handler(
    message: types.Message,
):

    print("===================================")
    print("BUSINESS MESSAGE RECEIVED")
    print("Connection ID:", message.business_connection_id)
    print("Chat ID:", message.chat.id)
    print("Chat Type:", message.chat.type)
    print("Username:", message.chat.username)
    print("Text:", message.text)
    print("===================================")

    response = (
        message.text
        or message.caption
        or "پیام بدون متن"
    )

    try:

        await message.bot.send_message(
            ADMIN_ID,
            "📥 پیام Business دریافت شد.\n\n"
            f"Connection ID:\n"
            f"{message.business_connection_id}\n\n"
            f"Chat ID:\n"
            f"{message.chat.id}\n\n"
            f"Username:\n"
            f"@{message.chat.username}"
            if message.chat.username
            else
            "Username:\nندارد\n\n"
            f"متن:\n{response}"
        )

    except Exception as e:

        print(
            "Error forwarding Business message:",
            e
        )


# =========================================================
# EDITED BUSINESS MESSAGE
# =========================================================

@dp.edited_business_message()
async def edited_business_message_handler(
    message: types.Message,
):

    print(
        "Edited Business message:",
        message.business_connection_id,
        message.chat.id,
        message.text,
    )


# =========================================================
# NORMAL MESSAGES
# =========================================================

@dp.message()
async def all_messages(message: types.Message):

    text = (message.text or "").strip()

    # Telegram ID
    if text == "/id":

        await message.answer(
            f"Telegram ID شما:\n"
            f"{message.from_user.id}"
        )

        return

    # تست ارتباط مستقیم قدیمی
    if text in [
        "/test_all",
        "/test_all@Ehvpnonebot",
    ]:

        if message.from_user.id != ADMIN_ID:
            return

        await message.answer(
            "🟡 تست ارتباط مستقیم با Providerها..."
        )

        results = []

        for provider_key, provider in PROVIDERS.items():

            try:

                sent = await message.bot.send_message(
                    chat_id=provider["chat_id"]
                    if provider["chat_id"]
                    else provider["username"],
                    text="/start",
                )

                results.append(
                    f"✅ {provider['username']}\n"
                    f"Message ID: {sent.message_id}"
                )

            except Exception as e:

                results.append(
                    f"❌ {provider['username']}\n"
                    f"{type(e).__name__}: {e}"
                )

        await message.answer(
            "📊 نتیجه:\n\n"
            + "\n\n".join(results)
        )

        return

    # MENU

    if text == "📱 سرویس‌های من":

        await message.answer(
            "فعلاً سرویسی برای این حساب ثبت نشده است."
        )

    elif text == "📊 استعلام وضعیت":

        await message.answer(
            "🔄 سیستم استعلام در حال آماده‌سازی است."
        )

    elif text == "🛒 خرید سرویس":

        await message.answer(
            "🛒 بخش خرید به‌زودی فعال می‌شود."
        )

    elif text == "🔄 تمدید سرویس":

        await message.answer(
            "🔄 بخش تمدید به‌زودی فعال می‌شود."
        )

    elif text == "💰 کیف پول":

        await message.answer(
            "💰 موجودی کیف پول: ۰ تومان"
        )

    elif text == "🎫 پشتیبانی":

        await message.answer(
            "🎫 پیام خود را ارسال کنید؛ "
            "پشتیبانی بررسی می‌کند."
        )

    else:

        await message.answer(
            "لطفاً یکی از گزینه‌های منو را انتخاب کنید.",
            reply_markup=menu(),
        )


# =========================================================
# WEBHOOK
# =========================================================

async def on_startup(bot: Bot):

    if not WEBHOOK_URL:

        raise RuntimeError(
            "RENDER_EXTERNAL_URL is not available"
        )

    await bot.set_webhook(
        WEBHOOK_URL
    )

    print(
        "Webhook set:",
        WEBHOOK_URL
    )


async def on_shutdown(bot: Bot):

    try:

        await bot.delete_webhook(
            drop_pending_updates=False
        )

    finally:

        await bot.session.close()


# =========================================================
# HEALTH
# =========================================================

async def health(request):

    return web.Response(
        text="OK"
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    bot = Bot(TOKEN)

    app = web.Application()

    app.router.add_get(
        "/",
        health
    )

    app.router.add_get(
        "/health",
        health
    )

    secret = os.getenv(
        "WEBHOOK_SECRET"
    )

    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=(
            secret
            if secret
            else None
        ),
    )

    handler.register(
        app,
        path=WEBHOOK_PATH
    )

    dp.startup.register(
        on_startup
    )

    dp.shutdown.register(
        on_shutdown
    )

    setup_application(
        app,
        dp,
        bot=bot
    )

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    print(
        f"Server started on port {PORT}"
    )

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
