import asyncio
from g4f.client import Client
import sys
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from datetime import datetime


# Токен Telegram-бота
TOKEN = '7559134674:AAHzi6r8AZQ9xq_YqFIxMp-jVMzX5OM2v8g'

client = Client()
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)  # Диспетчер
router = Router()


# Функция для ручного открытия файла и записи логов
async def log_message(user_id, username, message_text):
    log_file_path = 'log.txt'  # Путь к файлу логов
    log_entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - User ID: {user_id}, Username: {username}, Message: {message_text}\n"
    print(log_entry)

    try:
        # Открываем файл в режиме добавления (append)
        with open(log_file_path, 'a', encoding='utf-8') as log_file:
            log_file.write(log_entry)
    except Exception as e:
        print(f"Ошибка при записи логов: {e}")


# Отправка промта в Flux
async def send_promt_to_flux(promt):
    response = await client.images.async_generate(  # Используйте правильный метод
        model="flux",
        prompt=f"{promt}",
        response_format="url"
    )
    return response


# Отправка промта в GPT-4
async def send_promt_to_gpt4(promt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": f"{promt}"}
        ],
    )
    return response.choices[0].message.content


# Состояния для FSM
class UserStatment(StatesGroup):
    Waiting_for_promt_gpt = State()
    Waiting_for_promt_flux = State()
    Waiting_for_choice_to_do = State()


# Клавиатура для главного меню
def get_main_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🤖Спросить Chat-gpt 4.🤖")
    builder.button(text="🖼Сгенерировать изображение.🖼")
    return builder.as_markup(resize_keyboard=True)


# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await log_message(message.from_user.id, message.from_user.username, message.text)
    await state.clear()
    await message.answer(
        "Привет! Я бот Chat-gpt 4! Вы можете спросить меня о чем угодно, или попросить сгенерировать изображение!")
    await message.answer("Выберите опцию:", reply_markup=get_main_keyboard())


# Обработчик для выбора из главного меню
@router.message(F.text.in_(["🤖Спросить Chat-gpt 4.🤖", "🖼Сгенерировать изображение.🖼"]))
async def handle_main_menu(message: types.Message, state: FSMContext):
    await log_message(message.from_user.id, message.from_user.username, message.text)
    if await state.get_state():
        return  # если в FSM — пропускаем

    if message.text == "🤖Спросить Chat-gpt 4.🤖":
        await message.answer(f"Введите свой промт: ")
        await state.set_state(UserStatment.Waiting_for_promt_gpt)
        await log_message(message.from_user.id, message.from_user.username, message.text)
    elif message.text == "🖼Сгенерировать изображение.🖼":
        await message.answer(f"Введите свой промт: ")
        await state.set_state(UserStatment.Waiting_for_promt_flux)
        await log_message(message.from_user.id, message.from_user.username, message.text)


# Обработчик для получения промта GPT-4
@router.message(UserStatment.Waiting_for_promt_gpt)
async def get_promt_gpt(message: types.Message, state: FSMContext):
    promt = message.text
    await log_message(message.from_user.id, message.from_user.username, message.text)
    await message.answer("⌛ Думаю...")

    try:
        reply = await send_promt_to_gpt4(promt)
        await message.answer(reply)
        await state.clear()
        await message.answer("Выберите опцию:", reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"⚠️ Произошла ошибка: {e}")


# Обработчик для получения промта Flux
@router.message(UserStatment.Waiting_for_promt_flux)
async def get_promt_flux(message: types.Message, state: FSMContext):
    promt = message.text
    await log_message(message.from_user.id, message.from_user.username, message.text)
    await message.answer("⌛ Генерирую...")

    try:
        response = await send_promt_to_flux(promt)
        if response and response.data:
            image_url = response.data[0].url
            await message.answer(f'<a href="{image_url}">Ссылка на изображение</a>', parse_mode="HTML")
        else:
            await message.answer("⚠️ Не удалось получить изображение.")
        await state.clear()
        await message.answer("Выберите опцию:", reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"⚠️ Произошла ошибка: {e}")


# Запуск бота
async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        # Получаем текущий event loop, если он уже есть
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Если нет активного event loop, создаем новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(main())  # Запуск бота
