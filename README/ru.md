# Идея проекта и мой вклад в него

«Cyber‑Referent» — мой дипломный проект, цель которого — сократить время и повысить точность оформления библиографических списков. Я разработал систему «под ключ»: от анализа предметной области до полноценного веб‑приложения и Telegram‑бота

[english](https://github.com/idonix21/CyberReferent/blob/main/README.md) [русский](https://github.com/idonix21/CyberReferent/blob/main/README/ru.md)

Моими главными задачами было:
* Архитектура (чистая, модульная, с API‑шлюзом на FastAPI)
* Backend‑разработка всех микросервисов (парсер PDF/DOCX, валидатор ссылок, конвертер стилей, веб‑скрапер, экспорт BibTeX/CSV)
* Интеграция AI‑сервисов — DeepSeek для NLP‑разметки и Tavily для поиска недостающих метаданных
* Frontend на Streamlit и Telegram‑бот с python‑telegram‑bot
* CI‑тестирование (150 pytest‑кейсов, 100 % прохождение)

![Static Badge](https://img.shields.io/badge/python-3.11.9-green?link=https%3A%2F%2Fwww.python.org%2Fdownloads%2Frelease%2Fpython-3119%2F) ![Static Badge](https://img.shields.io/badge/streamlit-1.47.1-red?link=https%3A%2F%2Fstreamlit.io%2F) ![Static Badge](https://img.shields.io/badge/telegram_bot-22.3-blue?link=https%3A%2F%2Fpython-telegram-bot.org%2F) ![Static Badge](https://img.shields.io/badge/FastAPI-0.115.12-green?link=https%3A%2F%2Fpython-telegram-bot.org%2F) ![Static Badge](https://img.shields.io/badge/deepseek-reasoner-blue?link=https%3A%2F%2Fplatform.deepseek.com%2Fusage) ![Static Badge](https://img.shields.io/badge/tavily-0.7.10-orange?link=https%3A%2F%2Fwww.tavily.com%2F)

## Концепция проекта
Пользователь загружает статью (PDF/DOCX), URL или просто вставляет список литературы. Система:
1. Извлекает текст и находит секцию «Литература»
2. Разбивает её на отдельные записи
3. Проверяет каждую запись на ГОСТ Р 7.0.100‑2018, APA‑7 или MLA‑9
4. Автоматически исправляет ошибки и дополняет пропущенные поля (автор, год, страницы) через Tavily
5. Конвертирует ссылки между стилями и экспортирует в BibTeX/CSV
6. Отображает результат во веб‑интерфейсе или в чате Telegram

## Демонстрация проекта

Стартовая страница сразу после запуска пользователь видит простую форму: загрузка PDF/DOCX, вставка списка или URL‑ссылки и быстрый выбор стиля (ГОСТ, APA, MLA). Также пользователь может сразу переключится на нужныую ему задачу Проверку/Конвертер/Веб-скрапинг. Система моментально задаёт контекст и показывает, какие действия доступны дальше

<img width="1864" height="876" alt="q1" src="https://github.com/user-attachments/assets/c5733558-18b4-42d4-b2b9-55e95a463e87" />

Для ситуаций, когда ноутбука/пк нет под рукой, предусмотрен Telegram‑бот. Он повторяет логику веб‑версии, но адаптирован под чат: команды /check, /convert, /export выводятся в клавиатуре, а бот реагирует на отправку документов так же, как и веб‑сервис. Это превращает оформление библиографии в привычную переписку, позволяя работать «на ходу»—например, проверить ссылку прямо в читальном зале

<img width="1194" height="1012" alt="q2" src="https://github.com/user-attachments/assets/d5b38750-96be-4ff0-8c96-e353ddc216ae" />

Загрузив статью в PDF, пользователь наблюдает, как система извлекает секцию «Литература», разбивает её на элементы и подсвечивает ошибки. Алгоритмы pdfplumber + DeepSeek находят авторов, заголовки и годы даже в много‑колоночных макетах; результат мгновенно появляется в интерфейсе с маркировкой «валидно / нужно исправить»

<img width="1827" height="670" alt="q3" src="https://github.com/user-attachments/assets/e9435883-e340-494e-96aa-0a508fb6bdd1" />

Когда в ссылке отсутствуют обязательные поля — скажем, пропущены автор, год и страницы—модуль валидации сигнализирует о проблеме, а встроенный поиск Tavily пытается оперативно найти недостающие данные в открытых источниках. Пользователь видит подсказку «Найдено: Иванов И. И., 2022» и может одним кликом принять исправление или внести правку вручную

<img width="1533" height="819" alt="q4" src="https://github.com/user-attachments/assets/5ccb21ca-b93a-4958-beb6-500fc71176a9" />

После проверки достаточно нажать «Export → BibTeX» , чтобы получить готовый .bib‑файл. Система автоматически формирует уникальные ключи (Ivanov2022a и т. д.) и сохраняет корректную кодировку—файл можно сразу подключать к LaTeX‑рукописи или импортировать в Zotero

<img width="1428" height="1185" alt="q5" src="https://github.com/user-attachments/assets/ddda0e08-a0a4-49c6-aa57-4637da5bafbd" />

Если у вас есть только URL, «Cyber‑Referent» соберёт метаданные сам. Введите ссылку на статью, и модуль web‑scraper извлечёт автора, название, DOI и сформирует полноформатную запись. Таким образом, оформление литературы по интернет‑ресурсам сводится к одной операции «вставить ссылку → получить готовую ссылку»

<img width="1789" height="875" alt="q6" src="https://github.com/user-attachments/assets/82e63966-afa6-4adc-82a6-ac76ef643c5d" />

# Руководство по настройке и запуску

Добро пожаловать! Ниже — краткая инструкция по локальному развертыванию Cyber‑Referent.
Стек проекта: **Python 3.11** + **FastAPI**, **Streamlit**, **python‑telegram‑bot** 

---

## Настройка перед запуском
* Клонирование репозитория и установка зависимостей
```
git clone https://github.com/idonix21/CyberReferent
cd CyberReferent
python -m venv env           # создаём виртуальное окружение
env\Scripts\activate      # активируем виртуальное окружение
pip install -r requirements.txt      # backend + frontend + bot
```
* Настройка среды
Создайте ```.env``` и включите туда эти переменные:
```
TELEGRAM_BOT_TOKEN=
DEEPSEEK_API_KEY = 
TAVILY_API_KEY = 
```
* Запуск приложения
1. Запуск серверной части
```
uvicorn backend.main:app
```
2. Запуск веб-интерфейса
```
streamlit run frontend_streamlit/app.py
```
3. Запуск телеграм бота
```
python -m bot.bot_main
```

Проект готов к работе — загружайте PDF или DOCX через веб‑форму либо отправляйте их боту и получите оформленный библиографический список!
