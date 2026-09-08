import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

ADMIN_ID = 8702341067
HVPN_BOT = "@H_VPNbot"

dp = Dispatcher()


def menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📱 سرویس‌های من"),
                KeyboardButton(text="📊 استعلام وضعیت")
            ],
            [
                KeyboardButton(text="🛒 خرید سرویس"),
                KeyboardButton(text="🔄 تمدید سرویس")
            ],
            [
                KeyboardButton(text="💰 کیف پول"),
                KeyboardButton(text="🎫 پشتیبانی")
            ],
        ],
        resize_keyboard=True
    )


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "سلام 👋\n"
        "به پنل خدمات VPN خوش آمدید.\n\n"
        "از منوی زیر سرویس‌های خود را مدیریت کنید.",
        reply_markup=menu()
    )


@dp.message(Command("id"))
async def get_id(message: types.Message):
    await message.answer(f"Telegram ID شما:\n{message.from_user.id}")


@dp.message(Command("test_hvpn"))
async def test_hvpn(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    bot = message.bot

    try:
        sent = await bot.send_message(
            chat_id=HVPN_BOT,
            text="/start"
        )

        await message.answer(
            "✅ پیام تست به @H_VPNbot ارسال شد.\n"
            f"Message ID: {sent.message_id}\n\n"
            "منتظر پاسخ ربات هستیم..."
        )

    except Exception as e:
        await message.answer(
            "❌ ارسال به @H_VPNbot ناموفق بود:\n\n"
            f"{type(e).__name__}: {e}"
        )


@dp.message()
async def all_messages(message: types.Message):
    # دریافت پاسخ ربات H VPN
    if (
        message.from_user
        and message.from_user.username
        and message.from_user.username.lower() == "h_vpnbot"
    ):
        bot = message.bot

        if message.text:
            await bot.send_message(
                ADMIN_ID,
                "📥 پاسخ @H_VPNbot:\n\n" + message.text
            )

        if message.caption:
            await bot.send_message(
                ADMIN_ID,
                "📥 پاسخ @H_VPNbot:\n\n" + message.caption
            )

        return

    text = message.text or ""

    if text == "📱 سرویس‌های من":
        await message.answer("فعلاً سرویسی برای این حساب ثبت نشده است.")

    elif text == "📊 استعلام وضعیت":
        await message.answer("سیستم استعلام در حال آماده‌سازی است.")

    elif text == "🛒 خرید سرویس":
        await message.answer("بخش خرید به‌زودی فعال می‌شود.")

    elif text == "🔄 تمدید سرویس":
        await message.answer("بخش تمدید به‌زودی فعال می‌شود.")

    elif text == "💰 کیف پول":
        await message.answer("موجودی کیف پول: ۰ تومان")

    elif text == "🎫 پشتیبانی":
        await message.answer("پیام خود را ارسال کنید؛ پشتیبانی بررسی می‌کند.")

    else:
        await message.answer(
            "لطفاً یکی از گزینه‌های منو را انتخاب کنید.",
            reply_markup=menu()
        )


async def on_startup(bot: Bot):
    if not WEBHOOK_URL:
        raise RuntimeError("RENDER_EXTERNAL_URL is not available")

    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown(bot: Bot):
    await bot.delete_webhook(drop_pending_updates=False)
    await bot.session.close()


async def health(request):
    return web.Response(text="OK")


async def main():
    bot = Bot(TOKEN)

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    secret = os.getenv("WEBHOOK_SECRET")

    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=secret if secret else None,
    )

    handler.register(app, path=WEBHOOK_PATH)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
