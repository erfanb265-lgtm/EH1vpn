import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None
ADMIN_ID = 1145626218
PROVIDERS = [
    "@H_VPNbot",
    "@mxcloudbot",
    "@SvnProBot",
]
dp = Dispatcher()
# آخرین Business Connection
BUSINESS_CONNECTION_ID = None
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
# -----------------------------------------
# دریافت Business Connection
# -----------------------------------------
@dp.business_connection()
async def business_connection_handler(
    business_connection: types.BusinessConnection,
):
    global BUSINESS_CONNECTION_ID
    BUSINESS_CONNECTION_ID = business_connection.id
    print(
        "BUSINESS CONNECTION:",
        business_connection.id,
        "USER:",
        business_connection.user.id,
        "CAN REPLY:",
        business_connection.can_reply,
    )
# -----------------------------------------
# تست Business Connection
# -----------------------------------------
@dp.message()
async def all_messages(message: types.Message):
    global BUSINESS_CONNECTION_ID
    text = (message.text or "").strip()
    # نمایش ID
    if text == "/id":
        await message.answer(
            f"Telegram ID شما:\n{message.from_user.id}"
        )
        return
    # -----------------------------------------
    # نمایش وضعیت Business Connection
    # -----------------------------------------
    if text in ["/business", "/business@Ehvpnonebot"]:
        if message.from_user.id != ADMIN_ID:
            return
        if not BUSINESS_CONNECTION_ID:
            await message.answer(
                "❌ Business Connection هنوز به بات ارسال نشده.\n\n"
                "لطفاً اتصال Business را یک بار قطع و دوباره وصل کن."
            )
            return
        await message.answer(
            "✅ Business Connection فعال است.\n\n"
            f"Connection ID:\n{BUSINESS_CONNECTION_ID}"
        )
        return
    # -----------------------------------------
    # تست ارسال به H_VPNbot از طرف Business
    # -----------------------------------------
    if text in ["/test_business", "/test_business@Ehvpnonebot"]:
        if message.from_user.id != ADMIN_ID:
            return
        if not BUSINESS_CONNECTION_ID:
            await message.answer(
                "❌ Business Connection پیدا نشد.\n\n"
                "اول اتصال Business را قطع و دوباره وصل کن."
            )
            return
        await message.answer(
            "🟡 تست Business شروع شد...\n\n"
            "دارم /start را از طرف اکانت Business به "
            "@H_VPNbot می‌فرستم."
        )
        try:
            sent = await message.bot.send_message(
                business_connection_id=BUSINESS_CONNECTION_ID,
                chat_id="@H_VPNbot",
                text="/start",
            )
            await message.answer(
                "✅ ارسال موفق بود!\n\n"
                f"Provider: @H_VPNbot\n"
                f"Message ID: {sent.message_id}"
            )
        except Exception as e:
            await message.answer(
                "❌ ارسال ناموفق بود.\n\n"
                f"{type(e).__name__}:\n{e}"
            )
        return
    # -----------------------------------------
    # دریافت پیام‌های Business
    # -----------------------------------------
    if message.business_connection_id:
        response = (
            message.text
            or message.caption
            or "پیام بدون متن"
        )
        await message.bot.send_message(
            ADMIN_ID,
            "📥 Business Message\n\n"
            f"Chat ID: {message.chat.id}\n"
            f"Connection ID: {message.business_connection_id}\n\n"
            f"{response}",
        )
        return
    # -----------------------------------------
    # تست قدیمی Bot-to-Bot
    # -----------------------------------------
    if text in ["/test_all", "/test_all@Ehvpnonebot"]:
        if message.from_user.id != ADMIN_ID:
            return
        await message.answer(
            "🟡 تست ارتباط مستقیم با هر سه ربات..."
        )
        results = []
        for provider in PROVIDERS:
            try:
                sent = await message.bot.send_message(
                    chat_id=provider,
                    text="/start",
                )
                results.append(
                    f"✅ {provider}\n"
                    f"Message ID: {sent.message_id}"
                )
            except Exception as e:
                results.append(
                    f"❌ {provider}\n"
                    f"{type(e).__name__}: {e}"
                )
        await message.answer(
            "📊 نتیجه:\n\n"
            + "\n\n".join(results)
        )
        return
    # -----------------------------------------
    # منوی اصلی
    # -----------------------------------------
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
    await bot.set_webhook(WEBHOOK_URL)
async def on_shutdown(bot: Bot):
    await bot.delete_webhook(
        drop_pending_updates=False
    )
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
    handler.register(
        app,
        path=WEBHOOK_PATH,
    )
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
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
    await asyncio.Event().wait()
if __name__ == "__main__":
    asyncio.run(main())
