# The idea of the project and my contribution to it

"Cyber‑Referent" is my graduation project, the purpose of which is to reduce time and improve the accuracy of bibliographic lists. I have developed a turnkey system: from domain analysis to a full‑fledged web application and a Telegram bot

[english](https://github.com/winipux21/CyberReferent/blob/main/README.md) [русский](https://github.com/winipux21/CyberReferent/blob/main/README/ru.md)

In my area of responsibility were:
* Frchitecture (clean, modular, with API gateway on FastAPI)
* Backend‑development of all microservices (PDF/DOCX parser, link validator, style converter, web scraper, BibTeX/CSV export)
* Integration of AI services ‑ DeepSeek for NLP markup and Tavily for searching for missing metadata
* Frontend on Streamlit and Telegram bot with python‑telegram‑bot
* CI testing (150 pytest cases, 100% completion)

## Project concept
The user uploads an article (PDF/DOCX), URL, or simply inserts a list of references. The system:
1. Extracts the text and finds the "Literature" section
2. Breaks it down into separate entries
3. Checks each entry for GOST R 7.0.100‑2018, APA‑7 or MLA‑9
4. Automatically corrects errors and adds missing fields (author, year, pages) via Tavily
5. Converts links between styles and exports them to BibTeX/CSV
6. Displays the result in the web interface or in the Telegram chat

## Deconstruction of the project
The start page immediately after launch, the user sees a simple form: uploading a PDF/DOCX, inserting a list or URL link, and quickly choosing a style (GOST, APA, MLA). The user can also immediately switch to the task he needs./Converter/Web scraping. The system instantly sets the context and shows which actions are available next

<img width="1864" height="876" alt="q1" src="https://github.com/user-attachments/assets/c5733558-18b4-42d4-b2b9-55e95a463e87" />

For situations where a laptop/PC is not at hand, a Telegram bot is provided. It repeats the logic of the web version, but is adapted to the chat: the commands /check, /convert, /export are displayed on the keyboard, and the bot reacts to sending documents in the same way as the web service. This turns the design of the bibliography into a familiar correspondence, allowing you to work "on the go"—for example, check the link directly in the reading room

<img width="1194" height="1012" alt="q2" src="https://github.com/user-attachments/assets/d5b38750-96be-4ff0-8c96-e353ddc216ae" />

By uploading an article to PDF, the user watches as the system extracts the "Literature" section, breaks it down into elements, and highlights errors. pdfplumber algorithms + DeepSeek finds authors, titles, and years even in multi‑column layouts; the result instantly appears in the interface labeled "valid/needs to be fixed."

<img width="1827" height="670" alt="q3" src="https://github.com/user-attachments/assets/e9435883-e340-494e-96aa-0a508fb6bdd1" />

When the required fields are missing in the link — say, the author, year, and pages are missing—the validation module signals a problem, and the built-in Tavily search tries to quickly find the missing data in open sources. The user sees the prompt "Found: Ivanov I. I., 2022" and can accept the correction with one click or make an edit manually

<img width="1533" height="819" alt="q4" src="https://github.com/user-attachments/assets/5ccb21ca-b93a-4958-beb6-500fc71176a9" />

After checking, just click "Export → BibTeX" to get ready.bib file. The system automatically generates unique keys (Ivanov2022a, etc.) and saves the correct encoding—the file can be immediately connected to a LaTeX manuscript or imported into Zotero

<img width="1428" height="1185" alt="q5" src="https://github.com/user-attachments/assets/ddda0e08-a0a4-49c6-aa57-4637da5bafbd" />

If you only have the URL, Cyber‑Referent will collect the metadata itself. Enter the link to the article, and the web‑scraper module extracts the author, title, DOI and generates a full-length entry. Thus, the design of literature on Internet resources is reduced to a single operation "insert link → get ready link"

<img width="1789" height="875" alt="q6" src="https://github.com/user-attachments/assets/82e63966-afa6-4adc-82a6-ac76ef643c5d" />














