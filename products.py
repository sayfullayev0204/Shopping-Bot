import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.utils.callback_data import CallbackData
import re
import admin
API_TOKEN = admin.bot_token
ADMIN_ID = admin.admin_token 
PRODUCTS_FILE = 'products.txt'
PRODUCTS_PER_PAGE = 10


logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

pagination_cb = CallbackData('page', 'number')
product_cb = CallbackData('product', 'index')
order_cb = CallbackData('order', 'index')

user_data = {}

def read_products(file_path=PRODUCTS_FILE):
    products = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = re.match(r"(.+?) (\d+ so'm) 'tarkibi': (.+)", line)
            if match:
                name = match.group(1)
                price = match.group(2)
                description = match.group(3)
                products.append({'name': name, 'price': price, 'description': description})
    return products

def generate_product_info(product):
    return f"{product['name']} {product['price']}\n\nTarkibi: {product['description']}"

def generate_pagination_markup(page, total_pages):
    markup = InlineKeyboardMarkup(row_width=2)
    if page > 0:
        markup.add(InlineKeyboardButton('Previous', callback_data=pagination_cb.new(number=page-1)))
    if page < total_pages - 1:
        markup.add(InlineKeyboardButton('Next', callback_data=pagination_cb.new(number=page+1)))
    return markup

def generate_products_markup(products, page):
    markup = InlineKeyboardMarkup(row_width=5)
    start = page * PRODUCTS_PER_PAGE
    end = start + PRODUCTS_PER_PAGE
    for index, product in enumerate(products[start:end]):
        markup.insert(InlineKeyboardButton(f"{index+1}", callback_data=product_cb.new(index=start + index)))
    return markup

async def send_product_list(chat_id, products, page, message_id=None):
    total_pages = (len(products) + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
    product_markup = generate_products_markup(products, page)
    pagination_markup = generate_pagination_markup(page, total_pages)
    product_text = "\n".join([f"{index+1}. {product['name']} {product['price']}" for index, product in enumerate(products[page*PRODUCTS_PER_PAGE:page*PRODUCTS_PER_PAGE+PRODUCTS_PER_PAGE])])
    text = f"Mahsulotlar ro'yxati:\n{product_text}"
    markup = product_markup.inline_keyboard + pagination_markup.inline_keyboard
    if message_id:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup))
    else:
        await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=markup))

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    button = KeyboardButton('Telefon raqamni yuboring', request_contact=True)
    keyboard.add(button)
    await message.answer("Iltimos, telefon raqamingizni yuboring", reply_markup=keyboard)

@dp.message_handler(content_types=['contact'])
async def contact_handler(message: types.Message):
    user_data[message.from_user.id] = {
        'phone_number': message.contact.phone_number,
        'username': message.from_user.username
    }
    products = read_products()
    await send_product_list(message.chat.id, products, 0)
    await message.answer(reply_markup=types.ReplyKeyboardRemove())

@dp.callback_query_handler(pagination_cb.filter())
async def paginate_products(callback_query: types.CallbackQuery, callback_data: dict):
    page = int(callback_data['number'])
    products = read_products()
    await send_product_list(callback_query.message.chat.id, products, page, callback_query.message.message_id)
    await callback_query.answer()

@dp.callback_query_handler(product_cb.filter())
async def show_product_detail(callback_query: types.CallbackQuery, callback_data: dict):
    index = int(callback_data['index'])
    products = read_products()
    product_info = generate_product_info(products[index])
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Buyurtma qilish', callback_data=order_cb.new(index=index)))
    await callback_query.message.edit_text(product_info, reply_markup=markup)
    await callback_query.answer()

@dp.callback_query_handler(order_cb.filter())
async def handle_order(callback_query: types.CallbackQuery, callback_data: dict):
    index = int(callback_data['index'])
    user_id = callback_query.from_user.id
    if user_id in user_data:
        user_info = user_data[user_id]
        products = read_products()
        product_name = products[index]['name']
        
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        button = KeyboardButton('Lokatsiyani yuboring', request_location=True)
        keyboard.add(button)
        await callback_query.message.answer("Iltimos, lokatsiyangizni yuboring", reply_markup=keyboard)
        
        user_data[user_id]['pending_order'] = {
            'product_name': product_name,
            'admin_message': f"Buyurtma:\n\nMahsulot: {product_name}\nUsername: @{user_info['username']}\nTelefon raqam: {user_info['phone_number']}"
        }
        await callback_query.answer()
    else:
        await callback_query.answer("Iltimos, telefon raqamingizni yuboring")

@dp.message_handler(content_types=['location'])
async def location_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_data and 'pending_order' in user_data[user_id]:
        order = user_data[user_id].pop('pending_order')
        location = message.location
        admin_message = f"{order['admin_message']}\nLokatsiya: https://www.google.com/maps?q={location.latitude},{location.longitude}"
        await bot.send_message(ADMIN_ID, admin_message)
        await message.answer("Buyurtmangiz qabul qilindi!", reply_markup=types.ReplyKeyboardRemove())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

# created by sayfullayev 