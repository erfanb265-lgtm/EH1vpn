import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

dp = Dispatcher()

def menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 سرویس‌های من"), KeyboardButton(text="📊 استعلام وضعیت")],
            [KeyboardButton(text="🛒 خرید سرویس"), KeyboardButton(text="🔄 تمدید سرویس")],
            [KeyboardButton(text="💰 کیف پول"), KeyboardButton(text="🎫 پشتیبانی")],
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

@dp.message()
async def menu_handler(message: types.Message):
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
        await message.answer("لطفاً یکی از گزینه‌های منو را انتخاب کنید.", reply_markup=menu())

async def main():
    bot = Bot(TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
