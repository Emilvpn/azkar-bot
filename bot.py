import asyncio
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8022750372:AAFRB0z-KWtvrhOpg6hVBGYNLz0dFyALP3c"

# Загрузка утренних азкаров (объект с ключом "morning")
def load_morning_azkar(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["morning"]

# Загрузка вечерних азкаров (список)
def load_evening_azkar(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data  # data — уже список

MORNING_AZKAR = load_morning_azkar("morning_azkar.json")
EVENING_AZKAR = load_evening_azkar("evening_azkar.json")

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_data = {}  # хранит для каждого user_id: {"type": "morning" или "evening", "index": 0}

async def send_azkar(chat_id: int, azkar_list: list, index: int):
    azkar = azkar_list[index]
    kb = InlineKeyboardBuilder()
    kb.button(text="📘 Показать перевод", callback_data=f"translate_{index}")
    # Сообщение: текст + арабский
    msg_text = f"Азкар {index + 1}:\n\n{azkar['text']}\n\n" \
               f"Арабский:\n{azkar.get('arabic', '')}"
    await bot.send_message(chat_id, msg_text, reply_markup=kb.as_markup())
    # Отправляем аудио
    try:
        audio_file = FSInputFile(azkar["audio_path"])
        await bot.send_audio(chat_id, audio=audio_file)
    except FileNotFoundError:
        await bot.send_message(chat_id, f"❗️ Файл не найден: {azkar['audio_path']}")
    except Exception as e:
        await bot.send_message(chat_id, f"⚠️ Ошибка при отправке аудио:\n{type(e).__name__}: {e}")

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🌅 Утренние азкары", callback_data="choose_morning")
    kb.button(text="🌃 Вечерние азкары", callback_data="choose_evening")
    await message.answer("Выберите, какие азкары хотите читать:", reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data in ["choose_morning", "choose_evening"])
async def choose_azkar(callback: CallbackQuery):
    user_id = callback.from_user.id
    if callback.data == "choose_morning":
        user_data[user_id] = {"type": "morning", "index": 0}
        await callback.message.edit_text("🕊 Начнем читать утренние азкары.")
        await send_azkar(callback.message.chat.id, MORNING_AZKAR, 0)
    else:
        user_data[user_id] = {"type": "evening", "index": 0}
        await callback.message.edit_text("🌙 Начнем читать вечерние азкары.")
        await send_azkar(callback.message.chat.id, EVENING_AZKAR, 0)
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("translate_"))
async def show_translation(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_data:
        await callback.answer("Сначала выберите тип азкаров командой /start", show_alert=True)
        return
    index = int(callback.data.split("_")[1])
    azkar_type = user_data[user_id]["type"]
    azkar_list = MORNING_AZKAR if azkar_type == "morning" else EVENING_AZKAR
    azkar = azkar_list[index]

    kb = InlineKeyboardBuilder()
    next_index = index + 1
    if next_index < len(azkar_list):
        kb.button(text="➡️ Следующий азкар", callback_data=f"next_{next_index}")
    else:
        kb.button(text="✅ Все азкары прочитаны", callback_data="done", )
    await callback.message.edit_text(
        f"{azkar['text']}\n\nАрабский:\n{azkar.get('arabic', '')}\n\n"
        f"📘 Перевод:\n{azkar['translation']}",
        reply_markup=kb.as_markup()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("next_"))
async def next_azkar(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_data:
        await callback.answer("Сначала выберите тип азкаров командой /start", show_alert=True)
        return
    next_index = int(callback.data.split("_")[1])
    azkar_type = user_data[user_id]["type"]
    azkar_list = MORNING_AZKAR if azkar_type == "morning" else EVENING_AZKAR

    if next_index >= len(azkar_list):
        # При последнем азкаре не удаляем сообщение и не вызываем send_azkar
        await callback.message.edit_text("✅ Все азкары прочитаны. Да вознаградит тебя Аллах!")
        await callback.answer()
        return

    user_data[user_id]["index"] = next_index
    await send_azkar(callback.message.chat.id, azkar_list, next_index)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "done")
async def done_callback(callback: CallbackQuery):
    await callback.answer("Вы завершили чтение азкаров. Спасибо!", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
