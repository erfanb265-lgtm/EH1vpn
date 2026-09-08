import os
import asyncio
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", "10000"))

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

ADMIN_ID = 1145626218

dp = Dispatcher()

# اتصال Business
business_connections = {}


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


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "سلام 👋\n"
        "به پنل خدمات VPN خوش آمدید.\n\n"
        "از منوی زیر سرویس‌های خود را مدیریت کنید.",
        reply_markup=menu(),
    )


# دریافت Business Connection
@dp.business_connection()
async def business_connection_handler(
    business_connection: types.BusinessConnection,
):
    business_connections[business_connection.id] = business_connection

    print(
        "========== BUSINESS CONNECTION =========="
    )
    print("ID:", business_connection.id)
    print("USER ID:", business_connection.user.id)
    print("USERNAME:", business_connection.user.username)
    print("CAN REPLY:", business_connection.can_reply)
    print("IS ENABLED:", business_connection.is_enabled)
    print("=========================================")


@dp.message()
async def all_messages(message: types.Message):

    text = (message.text or "").strip()

    # Telegram ID
    if text == "/id":
        await message.answer(
            f"Telegram ID شما:\n{message.from_user.id}"
        )
        return

    # وضعیت Business
    if text in ["/business", "/business@Ehvpnonebot"]:

        if message.from_user.id != ADMIN_ID:
            return

        if not business_connections:
            await message.answer(
                "❌ هنوز هیچ Business Connection دریافت نشده.\n\n"
                "اگر اکانت دوم وصل شده، یک بار اتصال را قطع و دوباره وصل کن."
            )
            return

        result = []

        for connection_id, connection in business_connections.items():

            result.append(
                "✅ Business Connection\n\n"
                f"ID: {connection_id}\n"
                f"User ID: {connection.user.id}\n"
                f"Username: @{connection.user.username}\n"
                f"Can Reply: {connection.can_reply}\n"
                f"Enabled: {connection.is_enabled}"
            )

        await message.answer("\n\n".join(result))
        return

    # تست
    if text in ["/test_business", "/test_business@Ehvpnonebot"]:

        if message.from_user.id != ADMIN_ID:
            return

        if not business_connections:
            await message.answer(
                "❌ Business Connection هنوز دریافت نشده."
            )
            return

        connection_id = list(
            business_connections.keys()
        )[0]

        connection = business_connections[connection_id]

        await message.answer(
            "🟡 اتصال Business پیدا شد.\n\n"
            f"Connection ID:\n{connection_id}\n\n"
            f"Can Reply: {connection.can_reply}\n"
            f"Enabled: {connection.is_enabled}"
        )

        return

    # پیام‌های Business
    if message.business_connection_id:

        await message.bot.send_message(
            ADMIN_ID,
            "📥 پیام Business دریافت شد.\n\n"
            f"Connection ID:\n"
            f"{message.business_connection_id}\n\n"
            f"Chat ID: {message.chat.id}\n\n"
            f"{message.text or message.caption or 'بدون متن'}"
        )

        return

    # منوی اصلی
    if text == "📱 سرویس‌های من":

        await message.answer(
            "فعلاً سرویسی برای این حساب ثبت نشده است."
        )

    elif text == "📊 استعلام وضعیت":

        await message.answer(
            "سیستم استعلام در حال آماده‌سازی است."
        )

    elif text == "🛒 خرید سرویس":

        await message.answer(
            "بخش خرید به‌زودی فعال می‌شود."
        )

    elif text == "🔄 تمدید سرویس":

        await message.answer(
            "بخش تمدید به‌زودی فعال می‌شود."
        )

    elif text == "💰 کیف پول":

        await message.answer(
            "موجودی کیف پول: ۰ تومان"
        )

    elif text == "🎫 پشتیبانی":

        await message.answer(
            "پیام خود را ارسال کنید؛ پشتیبانی بررسی می‌کند."
        )

    else:

        await message.answer(
            "لطفاً یکی از گزینه‌های منو را انتخاب کنید.",
            reply_markup=menu(),
        )


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

    await bot.delete_webhook(
        drop_pending_updates=False
    )

    await bot.session.close()


async def health(request):

    return web.Response(
        text="OK"
    )


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

    from aiogram.webhook.aiohttp_server import (
        SimpleRequestHandler,
        setup_application,
    )

    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=secret if secret else None,
    )

    handler.register(
        app,
        path=WEBHOOK_PATH,
    )

    setup_application(
        app,
        dp,
        bot=bot,
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT,
    )

    await site.start()

    print(
        f"Server started on port {PORT}"
    )

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
