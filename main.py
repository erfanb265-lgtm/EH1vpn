import os, sqlite3, asyncio
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

PRODUCTS = {
    "hvpn": dict(name="H_VPN حجم دلخواه", provider="HVPN", provider_name="@H_VPNbot", mode="gb", provider_price=5000, sell_price=10000, min_gb=10, duration="30 روز"),
    "mx_limitless": dict(name="MXCloud Limitless", provider="MXCloud", provider_name="@mxcloudbot", mode="fixed", provider_price=280000, sell_price=450000, duration="30 روز", details="حجم نامحدود، 1 کاربر"),
    "mx_tunnel": dict(name="MXCloud Tunnel Gaming", provider="MXCloud", provider_name="@mxcloudbot", mode="gb", provider_price=5000, sell_price=15000, min_gb=1, duration="نامحدود", details="کاربر نامحدود"),
    "svn_direct_1": dict(name="SVN Direct یک ماهه", provider="SVN", provider_name="@SvnProBot", mode="fixed", provider_price=42000, sell_price=120000, duration="1 ماه", details="نامحدود"),
    "svn_direct_2": dict(name="SVN Direct دو ماهه", provider="SVN", provider_name="@SvnProBot", mode="fixed", provider_price=62000, sell_price=260000, duration="2 ماه", details="نامحدود"),
    "svn_tunnel_10": dict(name="SVN Tunnel 10GB", provider="SVN", provider_name="@SvnProBot", mode="fixed", provider_price=59000, sell_price=160000, duration="1 ماه", details="10GB"),
    "svn_tunnel_20": dict(name="SVN Tunnel 20GB", provider="SVN", provider_name="@SvnProBot", mode="fixed", provider_price=122000, sell_price=260000, duration="1 ماه", details="20GB"),
    "svn_tunnel_30": dict(name="SVN Tunnel 30GB", provider="SVN", provider_name="@SvnProBot", mode="fixed", provider_price=162000, sell_price=360000, duration="1 ماه", details="30GB"),
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
    CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY AUTOINCREMENT,telegram_id INTEGER,order_id INTEGER,product_key TEXT,provider TEXT,provider_service_id TEXT,subscription_url TEXT,config_text TEXT,status TEXT,created_at TEXT,expires_at TEXT);""")
    c.commit(); c.close()

def save_user(m):
    u=m.from_user; c=conn()
    c.execute("""INSERT INTO users VALUES(?,?,?,?) ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name""",(u.id,u.username,u.first_name,datetime.utcnow().isoformat()))
    c.commit(); c.close()

def main_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛒 خرید سرویس"),KeyboardButton(text="📱 سرویس‌های من")],[KeyboardButton(text="📊 استعلام وضعیت"),KeyboardButton(text="💰 کیف پول")],[KeyboardButton(text="🔄 تمدید سرویس"),KeyboardButton(text="🎫 پشتیبانی")]],resize_keyboard=True)

def product_kb():
    names=[("hvpn","H_VPN حجم دلخواه"),("mx_limitless","MXCloud Limitless"),("mx_tunnel","MXCloud Tunnel Gaming"),("svn_direct_1","SVN Direct یک ماهه"),("svn_direct_2","SVN Direct دو ماهه"),("svn_tunnel_10","SVN Tunnel 10GB"),("svn_tunnel_20","SVN Tunnel 20GB"),("svn_tunnel_30","SVN Tunnel 30GB")]
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=n,callback_data="p:"+k)] for k,n in names])

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
    save_user(m); await m.answer("🛒 محصول موردنظر را انتخاب کنید:",reply_markup=product_kb())

@dp.callback_query(F.data.startswith("p:"))
async def product(cq:types.CallbackQuery):
    k=cq.data[2:]; p=PRODUCTS[k]
    if p["mode"]=="gb":
        states[cq.from_user.id]={"key":k}
        await cq.message.answer(f"📦 {p['name']}\n💰 قیمت فروش: {p['sell_price']:,} تومان/GB\n📆 {p['duration']}\n🔢 حداقل: {p['min_gb']}GB\n\nتعداد گیگابایت را با عدد لاتین وارد کنید.")
    else:
        o=create_order(cq.from_user.id,k); await cq.message.answer(summary(o["id"]),reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📸 ارسال رسید",callback_data=f"help:{o['id']}"),InlineKeyboardButton(text="❌ لغو",callback_data=f"cancel:{o['id']}")]]))
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
async def approve(cq):
    if cq.from_user.id!=ADMIN_ID: await cq.answer("دسترسی ندارید.",show_alert=True); return
    i=int(cq.data[3:]); o=get_order(i)
    if not o or o["status"]!="receipt_submitted": await cq.answer("این سفارش قبلاً بررسی شده.",show_alert=True); return
    c=conn(); c.execute("UPDATE orders SET status='approved',approved_at=? WHERE id=?",(datetime.utcnow().isoformat(),i)); c.commit(); c.close()
    await cq.message.edit_reply_markup(reply_markup=None); await cq.message.answer(f"✅ سفارش #{i} تأیید شد.")
    await cq.bot.send_message(o["telegram_id"],f"✅ پرداخت سفارش #{i} تأیید شد.\n⏳ سرویس شما در حال آماده‌سازی است.")
    # خرید خودکار Provider بعد از تست و ثبت دقیق دکمه‌های خرید هر Provider به این قسمت متصل می‌شود.

@dp.callback_query(F.data.startswith("no:"))
async def reject(cq):
    if cq.from_user.id!=ADMIN_ID: await cq.answer("دسترسی ندارید.",show_alert=True); return
    i=int(cq.data[3:]); o=get_order(i); c=conn(); c.execute("UPDATE orders SET status='rejected' WHERE id=?",(i,)); c.commit(); c.close()
    await cq.message.edit_reply_markup(reply_markup=None); await cq.message.answer(f"❌ رسید سفارش #{i} رد شد."); await cq.bot.send_message(o["telegram_id"],f"❌ رسید سفارش #{i} رد شد.")

@dp.message(F.text)
async def text(m:types.Message):
    save_user(m); s=states.get(m.from_user.id)
    if s and m.text.isdigit():
        p=PRODUCTS[s["key"]]; gb=int(m.text)
        if gb<p["min_gb"]: await m.answer(f"❌ حداقل {p['min_gb']}GB است."); return
        o=create_order(m.from_user.id,s["key"],gb); states.pop(m.from_user.id,None); await m.answer(summary(o["id"]),reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📸 ارسال رسید",callback_data=f"help:{o['id']}"),InlineKeyboardButton(text="❌ لغو",callback_data=f"cancel:{o['id']}")]])); return
    if m.text in ("📱 سرویس‌های من","📊 استعلام وضعیت"):
        c=conn(); rows=c.execute("SELECT * FROM services WHERE telegram_id=? ORDER BY id DESC",(m.from_user.id,)).fetchall(); c.close()
        await m.answer("📱 هنوز سرویسی ثبت نشده است." if not rows else "📱 سرویس‌های شما:\n\n" + "\n".join(f"#{r['id']} — {PRODUCTS.get(r['product_key'],{'name':r['product_key']})['name']} — {r['status']}" for r in rows))
    elif m.text=="💰 کیف پول": await m.answer("💰 موجودی کیف پول EhVPN: ۰ تومان")
    elif m.text=="🔄 تمدید سرویس": await m.answer("🔄 تمدید بعد از فعال شدن استعلام سرویس‌ها فعال می‌شود.")
    elif m.text=="🎫 پشتیبانی": await m.answer("🎫 پیام خود را ارسال کنید.")
    else: await m.answer("لطفاً یکی از گزینه‌های منو را انتخاب کنید.",reply_markup=main_menu())

@dp.business_message()
async def business(m:types.Message):
    print("BUSINESS",m.business_connection_id,m.chat.id,m.chat.username,m.text)
    await m.bot.send_message(ADMIN_ID,f"📥 پیام Business\n\nConnection ID: {m.business_connection_id}\nChat ID: {m.chat.id}\nUsername: @{m.chat.username if m.chat.username else 'ندارد'}\n\nمتن:\n{m.text or m.caption or 'بدون متن'}")

@dp.message(Command("orders"))
async def orders(m:types.Message):
    if m.from_user.id!=ADMIN_ID:return
    c=conn(); rows=c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 20").fetchall(); c.close()
    await m.answer("📋 سفارش‌ها:\n\n"+("\n".join(f"#{r['id']} | {PRODUCTS[r['product_key']]['name']} | {r['amount']:,} | {r['status']}" for r in rows) if rows else "موردی نیست."))

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
