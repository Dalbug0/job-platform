import asyncio
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import settings

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Привет! Я JobBot. Я помогу тебе работать с вакансиями и резюме.")


@dp.message(Command("resumes"))
async def resumes_handler(message: types.Message):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.API_URL}/hh/resumes")
        if response.status_code == 200:
            resumes = response.json()
            text = "\n".join([f"{r['title']} — {r['id']}" for r in resumes.get("items", [])])
            await message.answer(f"Твои резюме:\n{text}")
        else:
            await message.answer("Не удалось получить резюме. Авторизуйся через API.")


# 📋 Получение списка вакансий
@dp.message(Command("vacancies"))
async def vacancies_handler(message: types.Message):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.API_URL}/vacancies/")
        if response.status_code == 200:
            vacancies = response.json()
            if vacancies:
                text = "\n".join([f"{v['id']}: {v['title']} ({v['company']}, {v['location']})"
                                  for v in vacancies])
                await message.answer(f"Список вакансий:\n{text}")
            else:
                await message.answer("Вакансий пока нет.")
        else:
            await message.answer(
                f"Ошибка при получении списка вакансий. "
                f"Код: {response.status_code}, тело: {response.text}"
            )


# ➕ Добавление вакансии
@dp.message(Command("add_vacancy"))
async def add_vacancy_handler(message: types.Message):
    # Ожидаем формат: /add_vacancy Название;Компания;Локация;Описание
    try:
        _, data = message.text.split(" ", 1)
        title, company, location, description = data.split(";")
    except ValueError:
        await message.answer("Используй формат: /add_vacancy Название;Компания;Локация;Описание")
        return

    payload = {
        "title": title,
        "company": company,
        "location": location,
        "description": description,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{settings.API_URL}/vacancies/", json=payload)
        if response.status_code == 200:
            vacancy = response.json()
            await message.answer(f"Вакансия добавлена: {vacancy['id']} — {vacancy['title']}")
        else:
            await message.answer("Ошибка при добавлении вакансии.")


# ✏️ Обновление вакансии
@dp.message(Command("update_vacancy"))
async def update_vacancy_handler(message: types.Message):
    # Ожидаем формат: /update_vacancy ID;Название;Компания;Локация;Описание
    try:
        _, data = message.text.split(" ", 1)
        vacancy_id, title, company, location, description = data.split(";")
    except ValueError:
        await message.answer("Используй формат: /update_vacancy ID;Название;Компания;Локация;Описание")
        return

    payload = {
        "title": title,
        "company": company,
        "location": location,
        "description": description,
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{settings.API_URL}/vacancies/{vacancy_id}/", json=payload)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
