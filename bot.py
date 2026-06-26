#8843514549:AAHR0_hAFP1QiLLZUrAuCJ7otyafIXBp-do
#AQ.Ab8RN6I_W7QOXayaTJNOw-GzlQ5eqSaM4Tz7-hYxKZJYpd1hwA
import re
import os
import json
import random
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
import yt_dlp
from faster_whisper import WhisperModel
import google.generativeai as genai
import genanki
from aiogram import F
from dotenv import load_dotenv
#import requests
#import time

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("ОШИБКА: TELEGRAM_TOKEN или GEMINI_API_KEY не найдены в .env файле!")

genai.configure(api_key=GEMINI_API_KEY)

llm_model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    generation_config={"response_mime_type": "application/json"},
    system_instruction="You are a helpful assistant. Create flashcards from the provided text for Anki. Return ONLY a valid JSON list of objects: [{\"question\": \"...\", \"answer\": \"...\"}]. Do not include markdown formatting like ```json."
)
print("Загрузка модели Whisper...")
whisper_model = WhisperModel("turbo", device="cuda", compute_type="float16")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

class AnkiStates(StatesGroup):
    waiting_for_mp3 = State()
    waiting_for_text = State()


def main_menu():
    kb = [
        [KeyboardButton(text="🎵 Через MP3 / Аудио")],
        [KeyboardButton(text="📝 Через Текст ")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ 

async def process_text_to_anki(text, message, status_msg):#запасная функция для создания текста для карточки
    try:
        status_msg = await message.answer("Модел генерирует карточки")
        prompt = f"""
        Create flashcards from this text for Anki.
        Return ONLY a JSON list of objects: [{{ "question": "...", "answer": "..." }}]
        Text: {text[:30000]}
        """
        response = await asyncio.to_thread(llm_model.generate_content, prompt)
        json_str = extract_json(response.text)
        cards_data = json.loads(json_str)
        
        v_id = str(random.randint(1000, 9999))
        anki_path = create_anki_deck(cards_data, v_id)
        
        await message.answer_document(FSInputFile(anki_path), caption="Готово!")
        os.remove(anki_path)
        await status_msg.delete()
    except Exception as e:
        await message.answer(f"Ошибка ИИ: {e}")


def extract_json(text):
    """Вырезает JSON из текста, если Gemini добавила лишние слова"""
    try:
        # Ищем всё, что находится между [ и ]
        text = text.strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return match.group(0)
        return text
    except Exception as e:
        logging.error(f"Extract JSON error: {e}")
        return text

# def blocking_process(url):
#      # Извлекаем ID видео
#      video_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
    
#      # --- ШАГ 1: ПРОБУЕМ ЗАБРАТЬ ГОТОВЫЕ СУБТИТРЫ (БЫСТРО И БЕЗОПАСНО) ---
#      try:
#          print(f"--> Пробую достать субтитры для {video_id} через API...")
#          # Используем твой файл cookies.txt
#          transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies='cookies.txt')
        
#          # Пытаемся найти русский, потом английский
#          try:
#              transcript = transcript_list.find_transcript(['ru', 'en'])
#          except:
#              # Если нет ручных, берем любой первый доступный (автогенерируемый)
#              transcript = next(iter(transcript_list))
            
#          data = transcript.fetch()
#          full_text = " ".join([t['text'] for t in data])
#          print("✅ Субтитры успешно получены напрямую!")
#          return full_text, video_id

#      except Exception as e:
#          print(f"ℹ️ Прямые субтитры недоступны ({e}). Перехожу к скачиванию аудио...")

#      # --- ШАГ 2: ЕСЛИ СУБТИТРОВ НЕТ, КАЧАЕМ АУДИО И ШИПИМ (WHISPER) ---
#      audio_temp_path = os.path.join(os.getcwd(), f"audio_{video_id}")
    
#      ydl_opts = {
#          'format': 'bestaudio/best',
#          'ffmpeg_location': '.',
#          'outtmpl': audio_temp_path + '.%(ext)s',
#          'postprocessors': [{
#              'key': 'FFmpegExtractAudio',
#              'preferredcodec': 'mp3',
#              'preferredquality': '192',
#          }],
#          'cookiefile': 'cookies.txt',
#          'nocheckcertificate': True,
#          # Клиент 'tv' сейчас работает лучше всего, когда остальные падают
#          'extractor_args': {
#              'youtube': {
#                  'player_client': ['tv'],
#              }
#          },
#      }
    
#      try:
#          with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#              ydl.download([url])
        
#          full_audio_path = audio_temp_path + ".mp3"
#          # На всякий случай проверяем, если расширение другое
#          if not os.path.exists(full_audio_path):
#              for f in os.listdir('.'):
#                  if f.startswith(f"audio_{video_id}") and f.endswith(".mp3"):
#                     full_audio_path = f
#                     break

#          print(f"🎙 Запуск Whisper на твоей RTX...")
#          segments, _ = whisper_model.transcribe(full_audio_path, beam_size=5)
#          transcript_text = " ".join([s.text for s in segments])
        
#          if os.path.exists(full_audio_path):
#              os.remove(full_audio_path)
            
#          return transcript_text, video_id

#      except Exception as e:
#          print(f"❌ Ошибка даже через TV-клиент: {e}")
#          raise Exception("YouTube заблокировал все попытки скачивания. Попробуй обновить cookies.txt или сменить IP.")

def create_anki_deck(cards_data, video_id):
    model_id = random.randrange(1 << 30, 1 << 31)
    deck_id = random.randrange(1 << 30, 1 << 31)
    anki_model = genanki.Model(
        model_id, 'Simple Model',
        fields=[{'name': 'Question'}, {'name': 'Answer'}],
        templates=[{'name': 'Card 1', 'qfmt': '{{Question}}', 'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}'}]
    )
    anki_deck = genanki.Deck(deck_id, f'Lecture_{video_id}')
    for card in cards_data:
        # Проверка структуры данных
        q = card.get('question', 'No question')
        a = card.get('answer', 'No answer')
        note = genanki.Note(model=anki_model, fields=[q, a])
        anki_deck.add_note(note)
    filename = f"anki_{video_id}.apkg"
    genanki.Package(anki_deck).write_to_file(filename)
    return filename

# ХЕНДЛЕРЫ
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    photo = FSInputFile("ezgif-163c4f5fb9a11ca7.gif")
    await message.answer_photo(
        photo = photo,
        caption= ("Привет! Я помогу тебе превратить лекцию в карточки Anki.\n\n"
        "Выбери способ загрузки:"),
        reply_markup=main_menu()
    )

@dp.message(F.text == "🎵 Через MP3 / Аудио")
async def press_mp3(message: types.Message, state: FSMContext):
    await state.set_state(AnkiStates.waiting_for_mp3)
    photo_patriot = FSInputFile("ezgif-1a99a20986d230ba.gif")
    await message.answer_photo(
        photo = photo_patriot,
        caption = ("Пришли мне аудиофайл (mp3, m4a) или голосовое сообщение."))

@dp.message(F.text == "📝 Через Текст / Транскрипт")
async def press_text(message: types.Message, state: FSMContext):
    await state.set_state(AnkiStates.waiting_for_text)
    await message.answer("Вставь сюда текст лекции или транскрипт с YouTube.")

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_text(message: types.Message):
    status_msg = await message.answer("Понял, это текст. Делаю из него карточки...")
    await process_text_to_anki(message.text, message, status_msg)


@dp.message(F.audio | F.voice | F.document)
async def handle_file(message: types.Message):
    succ = FSInputFile("ezgif-14d248b938b5069c.gif")
    if message.audio: file = message.audio
    elif message.voice: file = message.voice
    elif message.document and message.document.mime_type.startswith('audio'):
        file = message.document
    else: return

    status_msg = await message.answer("Качаю файл и запускаю Whisper")
    
    file_id = file.file_id
    file_info = await bot.get_file(file_id)
    file_path = f"temp_{file_id}.mp3"
    

    await bot.download_file(file_info.file_path, file_path)
    
    try:
        segments, _ = whisper_model.transcribe(file_path, beam_size=5)
        transcript = " ".join([s.text for s in segments])
        os.remove(file_path)
        await message.answer_photo(photo = succ, caption = "Даме онгр")
        await status_msg.edit_text("Текст распознан. Генерирую карточки...")
        await process_text_to_anki(
            transcript, message, status_msg)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


# @dp.message(F.audio | F.voice | F.document)
# async def handle_audio_file(message: types.Message):
#     succ = FSInputFile("ezgif-14d248b938b5069c.gif")
#     file = None
#     if message.audio:
#         file = message.audio
#     elif message.voice:
#         file = message.voice
#     elif message.document and (message.document.mime_type.startswith('audio') or message.document.file_name.endswith(('.mp3', '.m4a', '.wav'))):
#         file = message.document
    
#     if not file:
#         return # Если это не аудио, игнорируем

#     status_msg = await message.answer("Получил файл. Запускаю Whisper")

#     # 2. Скачиваем файл из Telegram
#     file_id = file.file_id
#     file_info = await bot.get_file(file_id)
#     ext = file.file_name.split('.')[-1] if hasattr(file, 'file_name') else "mp3"
#     local_filename = f"temp_{random.randint(1000,9999)}.{ext}"
    
#     await bot.download_file(file_info.file_path, local_filename)

#     try:
#         # 3. Транскрибация (Whisper GPU)
#         # Запускаем в потоке, чтобы бот не завис
#         def transcribe():
#             print(f"--> Whisper обрабатывает файл: {local_filename}")
#             segments, _ = whisper_model.transcribe(local_filename, beam_size=5)
#             return " ".join([s.text for s in segments])

#         transcript = await asyncio.to_thread(transcribe)
        
#         # Удаляем временный аудиофайл
#         if os.path.exists(local_filename):
#             os.remove(local_filename)

#         if not transcript.strip():
#             await status_msg.edit_text(" Не удалось распознать речь в файле.")
#             return
#         await status_msg.edit_text(" Текст готов. Gemini составляет карточки...")
        
#         prompt = f"""
#         Analyze this text and create Anki cards. 
#         Return ONLY a JSON list of objects.
#         Format: [{{ "question": "term", "answer": "definition" }}]
#         Text: {transcript[:30000]}
#         """
        
#         # Используем твою логику Gemini
#         response = await asyncio.to_thread(llm_model.generate_content, prompt)
        
#         # Очистка и парсинг JSON (используй свою функцию extract_json)
#         json_str = extract_json(response.text)
#         cards_data = json.loads(json_str)
        
#         # 5. Создание Anki файла
#         v_id = str(random.randint(1000, 9999))
#         anki_path = create_anki_deck(cards_data, v_id)
#         await message.answer_photo(photo = succ, caption = "Даме онгр")
#         # 6. Отправка результата
#         await message.answer_document(FSInputFile(anki_path), caption="✅ Карточки из твоего файла готовы!")
        
#         if os.path.exists(anki_path):
#             os.remove(anki_path)
#         await status_msg.delete()

#     except Exception as e:
#         print(f"Ошибка: {e}")
#         await message.answer(f"❌ Произошла ошибка: {str(e)}")
#         if os.path.exists(local_filename):
#             os.remove(local_filename)



# @dp.message(Command("start"))
# async def cmd_start(message: types.Message):
#     await message.answer("Пришли ссылку на YouTube. Я создам карточки Anki.")

# @dp.message(F.text.contains("youtube.com") | F.text.contains("youtu.be"))
# async def handle_video(message: types.Message):
#     url = message.text
#     status_msg = await message.answer("📽 Начинаю обработку... Это может занять 1-3 минуты.")
    
#     try:
#         # 1. Whisper
#         transcript, v_id = await asyncio.to_thread(blocking_process, url)
#         await status_msg.edit_text("🎙 Речь распознана. Составляю карточки...")
        
#         # 2. Gemini
#         await process_text_to_anki(transcript, message, status_msg)
        
#         # Вызываем Gemini
#         #response = await asyncio.to_thread(llm_model.generate_content, prompt)
        
#         # Парсинг JSON с защитой
#         json_str = extract_json(response.text)
#         cards_data = json.loads(json_str)
        
#         # 3. Anki файл
#         anki_path = create_anki_deck(cards_data, v_id)
        
#         # 4. Отправка
#         await message.answer_document(FSInputFile(anki_path), caption="Готово! Импортируй этот файл в Anki.")
        
#         if os.path.exists(anki_path):
#             os.remove(anki_path)
#         await status_msg.delete()

#     except Exception as e:
#         logging.error(f"Error: {e}")
#         await message.answer(f"❌ Ошибка: {str(e)}\nПопробуй еще раз через минуту.")

@dp.message()
async def unknown_message(message: types.Message):
    await message.answer(
        "Я тебя не совсем понял. Пожалуйста, используй кнопки меню:\n\n"
        "1. Нажми '🎵 Через MP3', чтобы скинуть файл.\n"
        "2. Нажми '📝 Через Текст', чтобы просто вставить текст лекции.",
        reply_markup=main_menu()
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())