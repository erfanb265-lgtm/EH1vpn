import os, sqlite3, asyncio, re
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None
ADMIN_ID = 1145626218
BUSINESS_CONNECTION_ID = os.getenv("BUSINESS_CONNECTION_ID")
DB_PATH = os.getenv("DB_PATH", "ehvpn.db")
AUTO_PROVIDER_PURCHASE = os.getenv("AUTO_PROVIDER_PURCHASE", "false").lower() == "true"
PROVIDER_DEBUG = os.getenv("PROVIDER_DEBUG", "false").lower() == "true"

PRODUCTS = {
    "hvpn": dict(name="👑 EH Premium", category="premium", provider="HVPN", provider_name="@H_VPNbot", mode="gb", provider_price=5000, sell_price=10000, min_gb=10, duration="30 روز",
                 details="بالاترین سطح سرعت و پایداری",
                 description='👑 EH Premium\\n\\n🚀 بالاترین سطح سرعت و پایداری در مجموعه\\n🛡️ مناسب استفاده سنگین و طولانی\u200cمدت\\n⚡ پایداری بسیار بالا در شرایط اختلال و محدودیت اینترنت\\n⭐ انتخاب پیشنهادی برای کسانی که کیفیت اولویت اولشان است'),
    "mx_limitless": dict(name="🌐 EH Normal", category="normal", provider="MXCloud", provider_name="@mxcloudbot", mode="fixed", provider_price=280000, sell_price=450000, duration="30 روز", details="حجم نامحدود، 1 کاربر",
                 description='🌐 EH Normal\\n\\n♾️ حجم نامحدود\\n📱 مناسب وب\u200cگردی، شبکه\u200cهای اجتماعی، پیام\u200cرسان\u200cها و استفاده روزمره\\n🌍 انتخاب مناسب برای مصرف معمولی\\nℹ️ پایداری آن در سطح EH Premium نیست'),
    "mx_tunnel": dict(name="🎮 EH Gaming", category="gaming", provider="MXCloud", provider_name="@mxcloudbot", mode="gb", provider_price=5000, sell_price=15000, min_gb=1, duration="نامحدود", details="کاربر نامحدود",
                 description='🎮 EH Gaming\\n\\n🎯 طراحی\u200cشده برای گیمرها و استفاده\u200cهایی که پینگ اهمیت دارد\\n⚡ تمرکز روی تأخیر پایین و اتصال روان\\n🎮 مناسب بازی\u200cهای آنلاین\\n📊 حجم بر اساس انتخاب شما'),
    "svn_direct_1": dict(name="💰 EH Economy — Direct 1M", category="economy", provider="SVN", provider_name="@SvnProBot", mode="fixed", provider_price=42000, sell_price=120000, duration="1 ماه", details="نامحدود",
                 description='🔹 EH Economy — Direct\\n\\n💵 اقتصادی\u200cترین انتخاب\\n📱 مناسب تلگرام، پیام\u200cرسان\u200cها و پلتفرم\u200cهای چت\\n🚀 سرعت قابل قبول برای مصرف روزمره\\n✅ مناسب وقتی قیمت اهمیت بیشتری دارد'),
    "svn_direct_2": dict(name="💰 EH Economy — Direct 2M", category="economy", provider="SVN", provider_name="@SvnProBot", mode="fixed", provider_price=62000, sell_price=260000, duration="2 ماه", details="نامحدود",
                 description='🔹 EH Economy — Direct\\n\\n💵 اقتصادی و دوماهه\\n📱 مناسب تلگرام، پیام\u200cرسان\u200cها و پلتفرم\u200cهای چت\\n🚀 سرعت قابل قبول برای مصرف روزمره'),
    "svn_tunnel_10": dict(name="💰 EH Economy — Tunnel 10GB", category="economy", provider="SVN", provider_name="@SvnProBot", mode="fixed", provider_price=59000, sell_price=160000, duration="1 ماه", details="10GB",
                 description='🔸 EH Economy — Tunnel\\n\\n💰 اقتصادی با پایداری بهتر\\n🛡️ مناسب استفاده روزمره و پیام\u200cرسان\u200cها\\n📊 حجم 10GB\\n✅ انتخاب مناسب برای سرویس اقتصادی و مطمئن\u200cتر'),
    "svn_tunnel_20": dict(name="💰 EH Economy — Tunnel 20GB", category="economy", provider="SVN", provider_name="@SvnProBot", mode="fixed", provider_price=122000, sell_price=260000, duration="1 ماه", details="20GB",
                 description='🔸 EH Economy — Tunnel\\n\\n💰 اقتصادی با پایداری بهتر\\n🛡️ مناسب استفاده روزمره و پیام\u200cرسان\u200cها\\n📊 حجم 20GB'),
    "svn_tunnel_30": dict(name="💰 EH Economy — Tunnel 30GB", category="economy", provider="SVN", provider_name="@SvnProBot", mode="fixed", provider_price=162000, sell_price=360000, duration="1 ماه", details="30GB",
                 description='🔸 EH Economy — Tunnel\\n\\n💰 اقتصادی با پایداری بهتر\\n🛡️ مناسب استفاده روزمره و پیام\u200cرسان\u200cها\\n📊 حجم 30GB'),
}
PROVIDER_CHAT_IDS = {"HVPN": 6683626212, "MXCloud": 8614664198, "SVN": 6606593549}
dp = Dispatcher()
states = {}

def conn():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row; return c

def init_db():
    c = conn()
    c.executescript("""CREATE TABLE IF NOT EXISTS users(telegram_id INTEGER PRIMARY KEY,username TEXT,first_name TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,telegram_id INTEGER,product_key TEXT,quantity_gb INTEGER,amount INTEGER,provider_cost INTEGER,profit INTEGER,status TEXT,receipt_file_id TEXT,provider TEXT,provider_service_id TEXT,subscription_url TEXT,config_text TEXT,created_at TEXT,approved_at TEXT);
    CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY AUTOINCREMENT,telegram_id INTEGER,order_id INTEGER,product_key TEXT,provider TEXT,provider_service_id TEXT,subscription_url TEXT,config_text TEXT,status TEXT,created_at TEXT,expires_at TEXT);
    CREATE INDEX IF NOT EXISTS idx_orders_provider_status ON orders(provider,status,id);""")
    c.commit(); c.close()

def save_user(m):
    u=m.from_user; c=conn()
    c.execute("""INSERT INTO users VALUES(?,?,?,?) ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name""",(u.id,u.username,u.first_name,datetime.utcnow().isoformat()))
    c.commit(); c.close()

def main_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="خرید سرویس جدید 🚀"),KeyboardButton(text="📱 سرویس‌های من")],[KeyboardButton(text="📊 استعلام وضعیت"),KeyboardButton(text="💰 کیف پول")],[KeyboardButton(text="🔄 تمدید سرویس"),KeyboardButton(text="🎫 پشتیبانی")]],resize_keyboard=True)

def category_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 EH Premium", callback_data="cat:premium")],
        [InlineKeyboardButton(text="🌐 EH Normal", callback_data="cat:normal")],
        [InlineKeyboardButton(text="🎮 EH Gaming", callback_data="cat:gaming")],
        [InlineKeyboardButton(text="💰 EH Economy", callback_data="cat:economy")],
    ])

def category_intro(category):
    return {
        "premium": "👑 EH Premium\n\n🚀 بالاترین سطح سرعت و پایداری\n🛡️ مناسب استفاده سنگین و طولانی‌مدت\n⚡ پایداری بسیار بالا در شرایط اختلال\n⭐ اگر کیفیت اولویت اول شماست، این گزینه را انتخاب کنید.",
        "normal": "🌐 EH Normal\n\n♾️ حجم نامحدود\n📱 مناسب وب‌گردی و استفاده روزمره\n💬 مناسب شبکه‌های اجتماعی و پیام‌رسان‌ها\nℹ️ پایداری آن از EH Premium کمتر است.",
        "gaming": "🎮 EH Gaming\n\n🎯 مناسب بازی‌های آنلاین\n⚡ تمرکز روی پینگ و تأخیر پایین\n🎮 مناسب کاربرانی که تجربه روان هنگام بازی می‌خواهند.",
        "economy": "💰 EH Economy\n\n💵 اقتصادی‌ترین خانواده سرویس‌ها\n📱 مناسب تلگرام و پلتفرم‌های چت\n🔸 Tunnel پایداری بیشتری نسبت به Direct دارد."
    }[category]

def category_products_kb(category):
    keys = [k for k, p in PRODUCTS.items() if p["category"] == category]
    rows = [[InlineKeyboardButton(text=PRODUCTS[k]["name"], callback_data="p:"+k)] for k in keys]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت به دسته‌ها", callback_data="back:cats")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def product_kb():
    return category_kb()

def get_order(i):
    c=conn(); r=c.execute("SELECT * FROM orders WHERE id=?",(i,)).fetchone(); c.close(); return r

def create_order(uid,key,gb=None):
    p=PRODUCTS[key]; amount=p["sell_price"]*gb if p["mode"]=="gb" else p["sell_price"]; cost=p["provider_price"]*gb if p["mode"]=="gb" else p["provider_price"]
    c=conn(); cur=c.execute("INSERT INTO orders(telegram_id,product_key,quantity_gb,amount,provider_cost,profit,status,provider,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(uid,key,gb,amount,cost,amount-cost,"awaiting_receipt",p["provider"],datetime.utcnow().isoformat())); i=cur.lastrowid; c.commit(); c.close(); return get_order(i)

def summary(i):
    o=get_order(i); p=PRODUCTS[o["product_key"]]; q=f'{o["quantity_gb"]}GB' if o["quantity_gb"] else p.get("details","نامحدود")
    return f"🧾 سفارش #{i}\n\n📦 {p['name']}\n📊 حجم: {q}\n📆 مدت: {p['duration']}\n\n💰 مبلغ قابل پرداخت: {o['amount']:,} تومان\n\nپس از واریز، رسید را همینجا ارسال کنید."

@dp.message(CommandStart())
async def start(m:types.Message):
    save_user(m); await m.answer("سلام 👋\nبه پنل EhVPN خوش آمدید.",reply_markup=main_menu())

@dp.message(F.text=="🛒 خرید سرویس")
async def buy(m:types.Message):
    save_user(m)
    await m.answer(
        "🛒 انتخاب سرویس\n\n"
        "اول نوع سرویس مناسب خودت رو انتخاب کن 👇\n\n"
        "👑 Premium — بالاترین سرعت و پایداری\n"
        "🌐 Normal — استفاده روزمره و حجم نامحدود\n"
        "🎮 Gaming — مخصوص گیمینگ و پینگ پایین\n"
        "💰 Economy — اقتصادی و مناسب مصرف معمولی",
        reply_markup=category_kb()
    )

@dp.callback_query(F.data.startswith("cat:"))
async def category(cq:types.CallbackQuery):
    category_name = cq.data[4:]
    await cq.message.answer(category_intro(category_name), reply_markup=category_products_kb(category_name))
    await cq.answer()

@dp.callback_query(F.data=="back:cats")
async def back_categories(cq:types.CallbackQuery):
    await cq.message.answer("🛒 انتخاب دسته سرویس 👇", reply_markup=category_kb())
    await cq.answer()


def provider_chat(provider):
    return PROVIDER_CHAT_IDS[provider]

async def send_provider_text(bot: Bot, provider: str, text: str):
    """Send a text message to the provider through the connected Telegram Business account."""
    if not BUSINESS_CONNECTION_ID:
        raise RuntimeError("BUSINESS_CONNECTION_ID is not set")
    return await bot.send_message(
        chat_id=provider_chat(provider),
        text=text,
        business_connection_id=BUSINESS_CONNECTION_ID,
    )

def provider_steps(order):
    """Text-equivalent navigation. This is intentionally configurable because
    providers may use ReplyKeyboard or InlineKeyboard buttons."""
    p = PRODUCTS[order["product_key"]]
    gb = order["quantity_gb"]

    if order["product_key"] == "hvpn":
        return [
            "خرید سرویس جدید",
            "سرویس حجم دلخواه",
            "5000",
            str(gb),
            "پرداخت از اعتبار",
        ]

    if order["product_key"] == "mx_limitless":
        return [
            "خرید سرویس جدید",
            "Limitless",
            "30",
            "1",
            "پرداخت از موجودی",
        ]

    if order["product_key"] == "mx_tunnel":
        return [
            "خرید سرویس جدید",
            "Premium",
            str(gb),
            "پرداخت از موجودی",
        ]

    if order["product_key"] == "svn_direct_1":
        return ["اشتراک نا محدود مستقیم", "1 ماهه", "پرداخت از اعتبار"]

    if order["product_key"] == "svn_direct_2":
        return ["اشتراک نا محدود مستقیم", "2 ماهه", "پرداخت از اعتبار"]

    if order["product_key"].startswith("svn_tunnel_"):
        gb = order["quantity_gb"] or int(order["product_key"].split("_")[-1].replace("GB", ""))
        return ["اشتراک حجمی تانل شده", f"{gb}GB", "پرداخت از اعتبار"]

    return []

PROVIDER_LOCKS = {name: asyncio.Lock() for name in PROVIDER_CHAT_IDS}


def provider_has_active_order(provider: str, exclude_id: int | None = None):
    c = conn()
    if exclude_id is None:
        row = c.execute(
            "SELECT * FROM orders WHERE provider=? AND status='provider_pending' ORDER BY id ASC LIMIT 1",
            (provider,),
        ).fetchone()
    else:
        row = c.execute(
            "SELECT * FROM orders WHERE provider=? AND status='provider_pending' AND id<>? ORDER BY id ASC LIMIT 1",
            (provider, exclude_id),
        ).fetchone()
    c.close()
    return row


async def start_provider_purchase(bot: Bot, order_id: int):
    order = get_order(order_id)
    if not order:
        return
    if order["status"] not in ("approved", "provider_queued"):
        return

    provider = order["provider"]
    lock = PROVIDER_LOCKS[provider]
    async with lock:
        # Never allow two purchases through the same provider wallet at once.
        active = provider_has_active_order(provider, exclude_id=order_id)
        if active:
            c = conn()
            c.execute("UPDATE orders SET status='provider_queued' WHERE id=?", (order_id,))
            c.commit(); c.close()
            await bot.send_message(ADMIN_ID, f"⏳ سفارش #{order_id} در صف خرید {provider} قرار گرفت؛ سفارش #{active['id']} در حال انجام است.")
            return

        steps = provider_steps(order)
        if not steps:
            raise RuntimeError("No provider flow configured")

        c = conn()
        c.execute("UPDATE orders SET status='provider_pending' WHERE id=?", (order_id,))
        c.commit(); c.close()

        await bot.send_message(
            ADMIN_ID,
            f"🔄 خرید خودکار سفارش #{order_id} شروع شد.\n"
            f"📦 {PRODUCTS[order['product_key']]['name']}\n"
            f"💳 پرداخت Provider از موجودی داخلی انجام می‌شود."
        )

        try:
            for step_no, step in enumerate(steps, 1):
                await send_provider_text(bot, provider, step)
                if PROVIDER_DEBUG:
                    await bot.send_message(ADMIN_ID, f"🧪 {provider} | مرحله {step_no}/{len(steps)} ارسال شد.")
                await asyncio.sleep(1.8)
        except Exception:
            c = conn(); c.execute("UPDATE orders SET status='provider_error' WHERE id=?", (order_id,)); c.commit(); c.close()
            raise


async def finish_provider_order(bot: Bot, order_id: int, url: str, raw_body: str):
    order = get_order(order_id)
    if not order:
        return
    c = conn()
    cur = c.execute(
        "UPDATE orders SET subscription_url=?, config_text=?, status='completed' WHERE id=? AND status='provider_pending'",
        (url, raw_body, order_id),
    )
    if cur.rowcount != 1:
        c.close()
        return
    c.execute(
        "INSERT INTO services(telegram_id,order_id,product_key,provider,subscription_url,config_text,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (order["telegram_id"], order_id, order["product_key"], order["provider"], url, raw_body, "active", datetime.utcnow().isoformat()),
    )
    c.commit(); c.close()

    # White-label delivery: only EH VPN branding goes to the customer.
    await bot.send_message(
        order["telegram_id"],
        f"🎉 سرویس شما آماده شد!\n\n"
        f"📦 {PRODUCTS[order['product_key']]['name']}\n"
        f"🔗 لینک اشتراک:\n{url}\n\n"
        f"⚡ از دکمه «📱 سرویس‌های من» می‌توانید سرویس خود را مدیریت کنید."
    )
    await bot.send_message(ADMIN_ID, f"✅ سفارش #{order_id} با موفقیت از Provider دریافت و به مشتری تحویل شد.")

    # Start the oldest queued order for this provider, if any.
    c = conn()
    nxt = c.execute("SELECT id FROM orders WHERE provider=? AND status='provider_queued' ORDER BY id ASC LIMIT 1", (order["provider"],)).fetchone()
    c.close()
    if nxt:
        await start_provider_purchase(bot, nxt["id"])

@dp.message(Command("provider_send"))
async def provider_send(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    parts = m.text.split(maxsplit=2)
    if len(parts) < 3:
        await m.answer("فرمت: /provider_send HVPN متن")
        return
    provider, msg = parts[1].upper(), parts[2]
    if provider not in PROVIDER_CHAT_IDS:
        await m.answer("Provider نامعتبر است: HVPN / MXCLOUD / SVN")
        return
    try:
        await send_provider_text(m.bot, provider, msg)
        await m.answer(f"✅ ارسال شد به {provider}")
    except Exception as e:
        await m.answer(f"❌ خطا: {type(e).__name__}: {e}")

@dp.callback_query(F.data.startswith("p:"))
async def product(cq:types.CallbackQuery):
    k=cq.data[2:]; p=PRODUCTS[k]
    if p["mode"]=="gb":
        states[cq.from_user.id]={"key":k}
        await cq.message.answer(p["description"] + f"\n\n💰 قیمت: {p['sell_price']:,} تومان / GB\n📆 مدت: {p['duration']}\n🔢 حداقل خرید: {p['min_gb']}GB\n\nتعداد گیگابایت را با عدد لاتین وارد کنید.")
    else:
        o=create_order(cq.from_user.id,k)
        await cq.message.answer(
            p["description"] + "\n\n" + summary(o["id"]),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="📸 ارسال رسید",callback_data=f"help:{o['id']}"),
                InlineKeyboardButton(text="❌ لغو",callback_data=f"cancel:{o['id']}")
            ]])
        )
    await cq.answer()

@dp.message(F.photo)
async def receipt(m:types.Message):
    save_user(m); c=conn(); o=c.execute("SELECT * FROM orders WHERE telegram_id=? AND status='awaiting_receipt' ORDER BY id DESC LIMIT 1",(m.from_user.id,)).fetchone()
    if not o: c.close(); await m.answer("❌ سفارش فعالی برای این حساب پیدا نشد."); return
    fid=m.photo[-1].file_id; c.execute("UPDATE orders SET status='receipt_submitted',receipt_file_id=? WHERE id=?",(fid,o["id"])); c.commit(); c.close()
    p=PRODUCTS[o["product_key"]]
    await m.answer(f"✅ رسید سفارش #{o['id']} دریافت شد.\nدر انتظار تأیید مدیریت هستید.")
    text=f"🧾 سفارش #{o['id']}\n👤 {m.from_user.full_name}\n🆔 {m.from_user.id}\n📦 {p['name']}\n💰 فروش: {o['amount']:,}\n💸 هزینه: {o['provider_cost']:,}\n📈 سود: {o['profit']:,}\n🏪 {p['provider_name']}"
    await m.bot.send_photo(ADMIN_ID,fid,caption=text,reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ تأیید",callback_data=f"ok:{o['id']}"),InlineKeyboardButton(text="❌ رد",callback_data=f"no:{o['id']}")]]))

@dp.callback_query(F.data.startswith("help:"))
async def help_receipt(cq): await cq.message.answer("📸 تصویر رسید را همینجا ارسال کنید."); await cq.answer()

@dp.callback_query(F.data.startswith("cancel:"))
async def cancel(cq):
    i=int(cq.data[7:]); o=get_order(i)
    if not o or o["telegram_id"]!=cq.from_user.id: await cq.answer("دسترسی ندارید.",show_alert=True); return
    c=conn(); c.execute("UPDATE orders SET status='cancelled' WHERE id=? AND status='awaiting_receipt'",(i,)); c.commit(); c.close(); await cq.message.answer("❌ سفارش لغو شد."); await cq.answer()

@dp.callback_query(F.data.startswith("ok:"))
async def approve(cq: types.CallbackQuery):
    if cq.from_user.id != ADMIN_ID:
        await cq.answer("دسترسی ندارید.", show_alert=True)
        return
    i = int(cq.data[3:])
    o = get_order(i)
    if not o or o["status"] != "receipt_submitted":
        await cq.answer("این سفارش قبلاً بررسی شده.", show_alert=True)
        return

    c = conn()
    c.execute(
        "UPDATE orders SET status='approved',approved_at=? WHERE id=?",
        (datetime.utcnow().isoformat(), i)
    )
    c.commit()
    c.close()

    await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(f"✅ سفارش #{i} تأیید شد.")
    await cq.bot.send_message(
        o["telegram_id"],
        f"✅ پرداخت سفارش #{i} تأیید شد.\n⏳ سرویس شما در حال آماده‌سازی است."
    )

    if AUTO_PROVIDER_PURCHASE:
        try:
            await start_provider_purchase(cq.bot, i)
        except Exception as e:
            c = conn()
            c.execute("UPDATE orders SET status='provider_error' WHERE id=?", (i,))
            c.commit()
            c.close()
            await cq.bot.send_message(
                ADMIN_ID,
                f"❌ خرید خودکار سفارش #{i} با خطا متوقف شد:\n"
                f"{type(e).__name__}: {e}"
            )
    else:
        await cq.bot.send_message(
            ADMIN_ID,
            f"ℹ️ سفارش #{i} تأیید شد ولی AUTO_PROVIDER_PURCHASE خاموش است."
        )

@dp.callback_query(F.data.startswith("no:"))
async def reject(cq):
    if cq.from_user.id!=ADMIN_ID: await cq.answer("دسترسی ندارید.",show_alert=True); return
    i=int(cq.data[3:]); o=get_order(i); c=conn(); c.execute("UPDATE orders SET status='rejected' WHERE id=?",(i,)); c.commit(); c.close()
    await cq.message.edit_reply_markup(reply_markup=None); await cq.message.answer(f"❌ رسید سفارش #{i} رد شد."); await cq.bot.send_message(o["telegram_id"],f"❌ رسید سفارش #{i} رد شد.")

@dp.message(Command("status"))
async def status_cmd(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    await m.answer(
        "🛠 وضعیت ربات\n\n"
        f"AUTO_PROVIDER_PURCHASE: {'ON' if AUTO_PROVIDER_PURCHASE else 'OFF'}\n"
        f"PROVIDER_DEBUG: {'ON' if PROVIDER_DEBUG else 'OFF'}\n"
        f"Business Connection: {'SET' if BUSINESS_CONNECTION_ID else 'NOT SET'}\n"
        f"DB: {DB_PATH}"
    )

@dp.message(Command("provider_queue"))
async def provider_queue(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    c = conn()
    rows = c.execute(
        "SELECT id,provider,status,product_key,amount FROM orders WHERE status IN ('provider_pending','provider_queued') ORDER BY id ASC"
    ).fetchall(); c.close()
    if not rows:
        await m.answer("📭 صف خرید Provider خالی است."); return
    lines = [f"#{r['id']} | {r['provider']} | {PRODUCTS[r['product_key']]['name']} | {r['status']} | {r['amount']:,}" for r in rows]
    await m.answer("📋 صف خرید Provider:\n\n" + "\n".join(lines))

@dp.message(Command("provider_retry"))
async def provider_retry(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    parts = m.text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await m.answer("فرمت: /provider_retry ORDER_ID"); return
    oid = int(parts[1]); o = get_order(oid)
    if not o or o["status"] not in ("provider_error", "provider_queued", "approved"):
        await m.answer("❌ سفارش قابل تلاش مجدد نیست."); return
    c = conn(); c.execute("UPDATE orders SET status='approved' WHERE id=?", (oid,)); c.commit(); c.close()
    try:
        await start_provider_purchase(m.bot, oid)
        await m.answer(f"🔄 تلاش مجدد سفارش #{oid} شروع شد.")
    except Exception as e:
        await m.answer(f"❌ خطا: {type(e).__name__}: {e}")

@dp.message(Command("orders"))
async def orders(m:types.Message):
    if m.from_user.id!=ADMIN_ID:return
    c=conn(); rows=c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 20").fetchall(); c.close()
    await m.answer("📋 سفارش‌ها:\n\n"+("\n".join(f"#{r['id']} | {PRODUCTS[r['product_key']]['name']} | {r['amount']:,} | {r['status']}" for r in rows) if rows else "موردی نیست."))

@dp.message(F.text)
async def text(m:types.Message):
    save_user(m); s=states.get(m.from_user.id)
    if s and m.text.isdigit():
        p=PRODUCTS[s["key"]]; gb=int(m.text)
        if gb<p["min_gb"]: await m.answer(f"❌ حداقل {p['min_gb']}GB است."); return
        o=create_order(m.from_user.id,s["key"],gb); states.pop(m.from_user.id,None); await m.answer(summary(o["id"]),reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📸 ارسال رسید",callback_data=f"help:{o['id']}"),InlineKeyboardButton(text="❌ لغو",callback_data=f"cancel:{o['id']}")]])); return
    if m.text == "خرید سرویس جدید 🚀":
        await m.answer("نوع سرویس را انتخاب کنید:", reply_markup=category_kb())
        return
    if m.text in ("📱 سرویس‌های من","📊 استعلام وضعیت"):
        c=conn(); rows=c.execute("SELECT * FROM services WHERE telegram_id=? ORDER BY id DESC",(m.from_user.id,)).fetchall(); c.close()
        if not rows:
            await m.answer("📱 هنوز سرویسی ثبت نشده است.")
        else:
            parts=[]
            for r in rows:
                parts.append(f"#{r['id']} — {PRODUCTS.get(r['product_key'], {'name': r['product_key']})['name']} — {r['status']}\n🔗 {r['subscription_url'] or 'در حال آماده‌سازی'}")
            await m.answer("📱 سرویس‌های شما:\n\n" + "\n\n".join(parts))
    elif m.text=="💰 کیف پول": await m.answer("💰 موجودی کیف پول EhVPN: ۰ تومان")
    elif m.text=="🔄 تمدید سرویس": await m.answer("🔄 تمدید بعد از فعال شدن استعلام سرویس‌ها فعال می‌شود.")
    elif m.text=="🎫 پشتیبانی": await m.answer("🎫 پیام خود را ارسال کنید.")
    elif m.text.startswith("/"):
        # Do not let the catch-all text handler swallow admin commands.
        return
    elif m.text in ("🛒 خرید سرویس", "خرید سرویس جدید"):
        await m.answer("نوع سرویس را انتخاب کنید:", reply_markup=category_kb())
    else:
        await m.answer("لطفاً یکی از گزینه‌های منو را انتخاب کنید.",reply_markup=main_menu())

@dp.business_message()
async def business(m: types.Message):
    """Receives provider replies through the connected Business account.
    Provider messages are never forwarded to customers.
    """
    body = m.text or m.caption or ""
    provider = next((p for p, chat_id in PROVIDER_CHAT_IDS.items() if m.chat.id == chat_id), None)
    if not provider:
        if PROVIDER_DEBUG:
            await m.bot.send_message(ADMIN_ID, f"📥 پیام Business ناشناس از chat_id={m.chat.id}\n{body[:3000]}")
        return

    if PROVIDER_DEBUG:
        await m.bot.send_message(ADMIN_ID, f"📥 {provider}\nChat ID: {m.chat.id}\n\n{body[:3000]}")

    # A purchase is considered delivered only when a URL is returned.
    urls = re.findall(r'https?://[^\s<>]+', body)
    if not urls:
        return

    url = urls[0].rstrip(").,]>")
    c = conn()
    row = c.execute(
        "SELECT * FROM orders WHERE provider=? AND status='provider_pending' ORDER BY id ASC LIMIT 1",
        (provider,),
    ).fetchone()
    c.close()
    if not row:
        if PROVIDER_DEBUG:
            await m.bot.send_message(ADMIN_ID, f"⚠️ لینک از {provider} دریافت شد ولی سفارش provider_pending پیدا نشد.\n{url}")
        return

    await finish_provider_order(m.bot, row["id"], url, body)


async def health(req): return web.Response(text="OK")
async def startup(bot:Bot):
    init_db()
    if not WEBHOOK_URL: raise RuntimeError("RENDER_EXTERNAL_URL is not available")
    await bot.set_webhook(WEBHOOK_URL)
async def shutdown(bot:Bot):
    try: await bot.delete_webhook(drop_pending_updates=False)
    finally: await bot.session.close()

async def main():
    init_db(); bot=Bot(TOKEN); app=web.Application(); app.router.add_get("/",health); app.router.add_get("/health",health)
    handler=SimpleRequestHandler(dispatcher=dp,bot=bot,secret_token=os.getenv("WEBHOOK_SECRET") or None); handler.register(app,path=WEBHOOK_PATH)
    dp.startup.register(startup); dp.shutdown.register(shutdown); setup_application(app,dp,bot=bot)
    runner=web.AppRunner(app); await runner.setup(); await web.TCPSite(runner,"0.0.0.0",PORT).start(); await asyncio.Event().wait()

if __name__=="__main__": asyncio.run(main())
