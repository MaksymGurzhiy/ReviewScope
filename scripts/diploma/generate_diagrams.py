"""
Generate every figure required by the diploma in a single, consistent style.
All figures are saved into docs/diagrams/*.png at 200 dpi.

Numbering follows the doc:
  Розділ 2 (проєктування) -> 2.1 .. 2.12
  Розділ 3 (реалізація)    -> 3.1 .. 3.2 (architecture / class)
                              3.3 .. 3.10 (UI screenshots, captured separately)
"""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from diagrams_common import (
    new_canvas, ucase, actor, box, rect, arrow, line, diamond, save,
)


# ---------------------------------------------------------------------------
# 2.1  Use Case - загальна
# ---------------------------------------------------------------------------
def fig_2_1_usecase_general():
    fig, ax = new_canvas(11, 8.5)
    ax.set_xlim(0, 11); ax.set_ylim(0, 8.5)

    # system boundary
    rect(ax, 6.0, 4.25, 7.6, 7.4, "", ec="black")
    ax.text(6.0, 8.0, "Веб-платформа ReviewScope", ha="center", va="center",
            fontsize=11, fontweight="bold")

    user = actor(ax, 1.0, 4.5, "Користувач")
    admin = actor(ax, 10.3, 2.0, "Адміністратор")

    # six user-driven use cases (single column - prevents line crossings)
    uc = [
        ucase(ax, 5.6, 7.0, "Реєстрація / вхід", w=3.0),
        ucase(ax, 5.6, 6.1, "Створення проєкту", w=3.0),
        ucase(ax, 5.6, 5.2, "Завантаження файлу з відгуками", w=4.0),
        ucase(ax, 5.6, 4.3, "Запуск NLP-аналізу", w=3.0),
        ucase(ax, 5.6, 3.4, "Перегляд звіту", w=3.0),
        ucase(ax, 5.6, 2.5, "Експорт у PDF / CSV", w=3.0),
        ucase(ax, 5.6, 1.5, "Адміністрування RLS-політик", w=4.0),
    ]
    for u in uc[:6]:
        line(ax, user, u)
    line(ax, admin, uc[6])

    save(fig, "fig_2_1_usecase_general")


# ---------------------------------------------------------------------------
# 2.2  Use Case - Завантаження та парсинг відгуків
# ---------------------------------------------------------------------------
def fig_2_2_usecase_upload():
    fig, ax = new_canvas(10, 6.5)
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.5)

    rect(ax, 5.3, 3.25, 7.6, 5.6, "", ec="black")
    ax.text(5.3, 6.0, "Завантаження та парсинг відгуків", ha="center",
            fontsize=11, fontweight="bold")

    user = actor(ax, 0.9, 3.25, "Користувач")
    storage = actor(ax, 9.4, 3.25, "Supabase\nStorage")

    # 5 use cases, one column
    uc = [
        ucase(ax, 5.0, 5.0, "Вибір файлу (CSV / XLSX / JSON)", w=4.0),
        ucase(ax, 5.0, 4.0, "Перевірка формату", w=3.0),
        ucase(ax, 5.0, 3.0, "Авто-визначення колонок", w=3.5),
        ucase(ax, 5.0, 2.0, "Нормалізація рейтингу", w=3.5),
        ucase(ax, 5.0, 1.0, "Збереження у Storage", w=3.5),
    ]
    line(ax, user, uc[0])
    line(ax, uc[4], storage)
    # vertical chain
    for i in range(len(uc) - 1):
        arrow(ax, uc[i], uc[i + 1], style="->", lw=0.9)

    save(fig, "fig_2_2_usecase_upload")


# ---------------------------------------------------------------------------
# 2.3  Use Case - NLP-аналіз
# ---------------------------------------------------------------------------
def fig_2_3_usecase_nlp():
    fig, ax = new_canvas(11, 7.5)
    ax.set_xlim(0, 11); ax.set_ylim(0, 7.5)

    rect(ax, 5.5, 3.75, 7.6, 6.6, "", ec="black")
    ax.text(5.5, 7.2, "NLP-аналіз клієнтських відгуків", ha="center",
            fontsize=11, fontweight="bold")

    user = actor(ax, 1.0, 3.75, "Користувач")
    gpu = actor(ax, 10.3, 3.75, "GPU /\nML-моделі")

    # central pipeline (single column)
    uc = [
        ucase(ax, 5.5, 6.2, "Запуск аналізу", w=3.0),
        ucase(ax, 5.5, 5.2, "Визначення мови", w=3.0),
        ucase(ax, 5.5, 4.2, "Аналіз тональності (BERT)", w=4.0),
        ucase(ax, 5.5, 3.2, "Аспектно-орієнтований аналіз (spaCy)", w=4.5),
        ucase(ax, 5.5, 2.2, "Тематичне моделювання (BERTopic)", w=4.5),
        ucase(ax, 5.5, 1.2, "Виділення ключових фраз (KeyBERT)", w=4.5),
    ]
    line(ax, user, uc[0])
    for i in range(len(uc) - 1):
        arrow(ax, uc[i], uc[i + 1], style="->", lw=0.9)
    # ML-models actor connects to all model-using use cases
    for u in uc[2:]:
        line(ax, u, gpu)

    save(fig, "fig_2_3_usecase_nlp")


# ---------------------------------------------------------------------------
# 2.4  Use Case - Перегляд та експорт результатів
# ---------------------------------------------------------------------------
def fig_2_4_usecase_results():
    fig, ax = new_canvas(10, 6.5)
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.5)

    rect(ax, 5.3, 3.25, 7.6, 5.6, "", ec="black")
    ax.text(5.3, 6.0, "Перегляд та експорт результатів", ha="center",
            fontsize=11, fontweight="bold")

    user = actor(ax, 0.9, 3.25, "Користувач")

    uc = [
        ucase(ax, 5.0, 5.2, "Перегляд висновку (Conclusion)", w=4.0),
        ucase(ax, 5.0, 4.3, "Перегляд тональності", w=3.5),
        ucase(ax, 5.0, 3.4, "Перегляд аспектів (ABSA)", w=3.5),
        ucase(ax, 5.0, 2.5, "Перегляд тем та ключових фраз", w=4.0),
        ucase(ax, 5.0, 1.6, "Перегляд прикладів відгуків", w=4.0),
        ucase(ax, 5.0, 0.7, "Експорт у PDF / CSV", w=3.5),
    ]
    for u in uc:
        line(ax, user, u)

    save(fig, "fig_2_4_usecase_results")


# ---------------------------------------------------------------------------
# 2.5  Use Case - Реєстрація та автентифікація
# ---------------------------------------------------------------------------
def fig_2_5_usecase_auth():
    fig, ax = new_canvas(10, 5.5)
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.5)

    rect(ax, 5.3, 2.75, 7.6, 4.6, "", ec="black")
    ax.text(5.3, 5.0, "Реєстрація та автентифікація", ha="center",
            fontsize=11, fontweight="bold")

    user = actor(ax, 0.9, 2.75, "Користувач")
    sb = actor(ax, 9.4, 2.75, "Supabase Auth")

    uc = [
        ucase(ax, 5.0, 4.2, "Реєстрація (e-mail + пароль)", w=4.0),
        ucase(ax, 5.0, 3.2, "Підтвердження e-mail", w=3.5),
        ucase(ax, 5.0, 2.2, "Вхід у систему", w=3.5),
        ucase(ax, 5.0, 1.2, "Перевірка JWT (ES256, JWKS)", w=4.0),
    ]
    for u in uc:
        line(ax, user, u)
        line(ax, u, sb)

    save(fig, "fig_2_5_usecase_auth")


# ---------------------------------------------------------------------------
# 2.6  Use Case - Керування проєктами
# ---------------------------------------------------------------------------
def fig_2_6_usecase_projects():
    fig, ax = new_canvas(10, 5.5)
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.5)

    rect(ax, 5.3, 2.75, 7.6, 4.6, "", ec="black")
    ax.text(5.3, 5.0, "Керування проєктами", ha="center",
            fontsize=11, fontweight="bold")

    user = actor(ax, 0.9, 2.75, "Користувач")
    db = actor(ax, 9.4, 2.75, "Supabase\nPostgreSQL")

    uc = [
        ucase(ax, 5.0, 4.2, "Створення проєкту", w=3.5),
        ucase(ax, 5.0, 3.2, "Перегляд списку проєктів", w=4.0),
        ucase(ax, 5.0, 2.2, "Перегляд аналізів в проєкті", w=4.0),
        ucase(ax, 5.0, 1.2, "Видалення проєкту", w=3.5),
    ]
    for u in uc:
        line(ax, user, u)
        line(ax, u, db)

    save(fig, "fig_2_6_usecase_projects")


# ---------------------------------------------------------------------------
# 2.7  Архітектура веб-платформи (block diagram)
# ---------------------------------------------------------------------------
def fig_2_7_architecture():
    """Strict 4-tier layered architecture, only vertical arrows."""
    fig, ax = new_canvas(12, 9.5)
    ax.set_xlim(0, 12); ax.set_ylim(0, 9.5)

    # ----- tier 1: client -----
    rect(ax, 6.0, 8.6, 11.0, 1.0, "", fc="white", ec="black")
    ax.text(0.6, 8.6, "Клієнтський\nрівень", ha="left", va="center",
            fontsize=9, style="italic")
    box(ax, 6.0, 8.6, 6.0, 0.7,
        "Frontend  (React 18  ·  Vite  ·  TailwindCSS  ·  Recharts)",
        bold=True, fs=10)

    # ----- tier 2: API gateway -----
    rect(ax, 6.0, 7.1, 11.0, 1.0, "", fc="white", ec="black")
    ax.text(0.6, 7.1, "API\nрівень", ha="left", va="center",
            fontsize=9, style="italic")
    box(ax, 6.0, 7.1, 6.0, 0.7,
        "FastAPI  ·  uvicorn  ·  Pydantic  ·  JWT-middleware",
        bold=True, fs=10)

    # ----- tier 3: services -----
    rect(ax, 6.0, 5.4, 11.0, 1.4, "", fc="white", ec="black")
    ax.text(0.6, 5.4, "Сервісний\nрівень", ha="left", va="center",
            fontsize=9, style="italic")
    box(ax, 2.5, 5.4, 2.6, 0.8, "AuthService\n(JWKS / ES256)", fs=9)
    box(ax, 5.5, 5.4, 2.6, 0.8, "ProjectService", fs=9)
    box(ax, 8.5, 5.4, 2.6, 0.8, "AnalysisService", fs=9)
    box(ax, 11.0, 5.4, 1.6, 0.8, "ExportService\n(PDF / CSV)", fs=9)

    # ----- tier 4: NLP pipeline -----
    rect(ax, 6.0, 3.7, 11.0, 1.4, "", fc="white", ec="black")
    ax.text(0.6, 3.7, "NLP\nрівень", ha="left", va="center",
            fontsize=9, style="italic")
    box(ax, 2.3, 3.7, 2.0, 0.8, "Sentiment\nAnalyzer\n(BERT)", fs=8)
    box(ax, 4.5, 3.7, 2.0, 0.8, "Aspect\nAnalyzer\n(spaCy)", fs=8)
    box(ax, 6.7, 3.7, 2.0, 0.8, "Topic\nExtractor\n(BERTopic)", fs=8)
    box(ax, 8.9, 3.7, 2.0, 0.8, "Keyword\nExtractor\n(KeyBERT)", fs=8)
    box(ax, 11.0, 3.7, 1.7, 0.8, "Summary\nGenerator", fs=8)

    # ----- tier 5: data + GPU -----
    rect(ax, 6.0, 1.6, 11.0, 1.6, "", fc="white", ec="black")
    ax.text(0.6, 1.6, "Рівень\nданих", ha="left", va="center",
            fontsize=9, style="italic")
    box(ax, 3.0, 1.6, 3.6, 1.0,
        "Supabase PostgreSQL\nusers · projects · analyses ·\nanalysis_results",
        fs=9)
    box(ax, 7.0, 1.6, 3.0, 1.0,
        "Supabase Storage\n(завантажені файли)", fs=9)
    box(ax, 10.6, 1.6, 2.4, 1.0, "GPU  ·  CUDA\n(NVIDIA)", fs=9, bold=True)

    # arrows between tiers (only vertical, no crossings)
    arrow(ax, (6.0, 8.10), (6.0, 7.55), style="<->", label="HTTPS / JSON")
    arrow(ax, (6.0, 6.65), (6.0, 6.10), style="<->", label="DI / function call")
    arrow(ax, (6.0, 4.70), (6.0, 4.20), style="<->",
          label="pipeline.run(reviews, options)")
    arrow(ax, (6.0, 3.20), (6.0, 2.20), style="<->",
          label="SQL / Storage API / CUDA")

    save(fig, "fig_2_7_architecture")


# ---------------------------------------------------------------------------
# 2.8  Diagram of deployment
# ---------------------------------------------------------------------------
def fig_2_8_deployment():
    fig, ax = new_canvas(11, 6.5)
    ax.set_xlim(0, 11); ax.set_ylim(0, 6.5)

    # nodes (drawn as rectangles with shifted shadow to mimic 3D node)
    def node(cx, cy, w, h, title, content, fs=9):
        # back
        rect(ax, cx + 0.10, cy - 0.10, w, h, "", fc="white", ec="black")
        # front
        rect(ax, cx, cy, w, h, "", fc="white", ec="black")
        ax.text(cx, cy + h / 2 - 0.25, f"<<{title}>>",
                ha="center", va="top", fontsize=fs - 1, style="italic")
        ax.text(cx, cy - 0.05, content, ha="center", va="center", fontsize=fs)

    node(2.2, 5.0, 3.4, 1.6, "device",
         "Клієнтський пристрій\nБраузер  →  React SPA", fs=9)
    node(6.0, 5.0, 3.4, 1.6, "device",
         "Сервер додатку\nFastAPI (uvicorn) :8000\nPython 3.10  ·  CUDA", fs=9)
    node(9.6, 5.0, 1.8, 1.6, "device",
         "GPU\nNVIDIA / CUDA", fs=9)

    node(2.2, 2.4, 3.4, 1.4, "cloud",
         "Supabase\nPostgreSQL  ·  Auth", fs=9)
    node(6.0, 2.4, 3.4, 1.4, "cloud",
         "Supabase Storage\n(відгуки користувачів)", fs=9)
    node(9.6, 2.4, 1.8, 1.4, "cloud",
         "Hugging Face\n(моделі)", fs=9)

    arrow(ax, (2.2, 4.2), (6.0, 4.2), label="HTTPS", style="<->")
    arrow(ax, (6.0, 4.2), (9.6, 4.2), label="PCI-Express", style="<->")
    arrow(ax, (6.0, 4.2), (2.2, 3.1), label="JDBC / REST", style="<->")
    arrow(ax, (6.0, 4.2), (6.0, 3.1), label="HTTPS", style="<->")
    arrow(ax, (6.0, 4.2), (9.6, 3.1), label="HTTPS\n(одноразово)", style="->")

    save(fig, "fig_2_8_deployment")


# ---------------------------------------------------------------------------
# 2.9  Layered architecture
# ---------------------------------------------------------------------------
def fig_2_9_layers():
    fig, ax = new_canvas(8, 7)
    ax.set_xlim(0, 8); ax.set_ylim(0, 7)

    layers = [
        ("Шар представлення (UI)", "React  ·  TailwindCSS  ·  Recharts", 6.0),
        ("Шар REST API",  "FastAPI  ·  Pydantic  ·  Auth middleware", 4.8),
        ("Сервісний шар", "AnalysisService · ProjectService · ExportService", 3.6),
        ("Шар NLP-моделей", "BERT · BERTopic · KeyBERT · spaCy",   2.4),
        ("Шар даних", "Supabase PostgreSQL  ·  Supabase Storage", 1.2),
    ]
    for title, content, y in layers:
        rect(ax, 4.0, y, 7.0, 1.0, "", fc="white", ec="black")
        ax.text(0.7, y + 0.22, title, ha="left", va="center",
                fontsize=11, fontweight="bold")
        ax.text(0.7, y - 0.22, content, ha="left", va="center", fontsize=10)

    # arrows between layers (downward)
    for y0, y1 in [(6.0, 5.3), (4.8, 4.1), (3.6, 2.9), (2.4, 1.7)]:
        arrow(ax, (4.0, y0 - 0.5), (4.0, y1 + 0.5), style="->")

    save(fig, "fig_2_9_layers")


# ---------------------------------------------------------------------------
# 2.10  Sequence diagram - повний цикл аналізу
# ---------------------------------------------------------------------------
def fig_2_10_sequence():
    fig, ax = new_canvas(11, 8)
    ax.set_xlim(0, 11); ax.set_ylim(0, 8)

    # lifelines
    actors = [
        ("Користувач\n(браузер)", 0.8),
        ("React SPA",            2.6),
        ("FastAPI",              4.4),
        ("Storage\n(Supabase)",  6.2),
        ("AnalysisService",      8.0),
        ("NLPPipeline + GPU",    10.0),
    ]
    for name, x in actors:
        rect(ax, x, 7.4, 1.6, 0.6, name, fs=9, bold=True)
        ax.add_line(plt.Line2D([x, x], [7.0, 0.4],
                               linestyle="--", color="black", lw=0.7))

    # messages
    msgs = [
        (0.8, 2.6, 6.7, "POST /upload (file)"),
        (2.6, 4.4, 6.4, "POST /upload"),
        (4.4, 6.2, 6.1, "putObject(file)"),
        (6.2, 4.4, 5.8, "url"),
        (4.4, 2.6, 5.5, "201 {analysis_id}"),
        (2.6, 4.4, 5.0, "POST /analyses/{id}/run"),
        (4.4, 8.0, 4.7, "run_and_store(id)"),
        (8.0, 6.2, 4.4, "getObject(file)"),
        (6.2, 8.0, 4.1, "bytes"),
        (8.0, 10.0, 3.7, "pipeline.run(reviews)"),
        (10.0, 8.0, 3.0, "results"),
        (8.0, 4.4, 2.6, "save(results)"),
        (2.6, 4.4, 2.0, "GET /analyses/{id}"),
        (4.4, 2.6, 1.7, "results JSON"),
        (2.6, 0.8, 1.4, "render UI"),
    ]
    for x1, x2, y, lbl in msgs:
        arrow(ax, (x1, y), (x2, y), label=lbl, style="->", fs=8,
              offset=(0, 0.18))

    save(fig, "fig_2_10_sequence")


# ---------------------------------------------------------------------------
# 2.11  Activity - NLP pipeline
# ---------------------------------------------------------------------------
def fig_2_11_activity():
    fig, ax = new_canvas(7.5, 11)
    ax.set_xlim(0, 7.5); ax.set_ylim(0, 11)

    # start
    ax.add_patch(plt.Circle((3.75, 10.6), 0.18, color="black"))
    steps = [
        (3.75, 9.8, 3.4, 0.6, "Завантаження файлу"),
        (3.75, 8.9, 3.4, 0.6, "Парсинг + автодетект колонок"),
        (3.75, 8.0, 3.4, 0.6, "Фільтрація порожніх / NaN"),
    ]
    for x, y, w, h, t in steps:
        rect(ax, x, y, w, h, t, fs=10)

    # decision: language
    diamond(ax, 3.75, 7.0, 2.6, 0.8,
            "Багатомовний?", fs=9)
    rect(ax, 1.6, 6.1, 2.0, 0.6, "Detect_lang", fs=9)
    rect(ax, 5.9, 6.1, 2.0, 0.6, "skip", fs=9)

    # parallel fork
    rect(ax, 3.75, 5.0, 4.6, 0.6, "Sentiment Analysis (BERT)", fs=10)

    rect(ax, 3.75, 4.0, 4.6, 0.6, "Aspect Analysis (spaCy + lemma)", fs=10)
    rect(ax, 3.75, 3.0, 4.6, 0.6, "Topic Modeling (BERTopic)", fs=10)
    rect(ax, 3.75, 2.0, 4.6, 0.6, "Keyword Extraction (KeyBERT)", fs=10)

    rect(ax, 3.75, 1.0, 4.6, 0.6, "Generate Conclusion + Summary", fs=10)
    ax.add_patch(plt.Circle((3.75, 0.3), 0.18, color="black"))
    ax.add_patch(plt.Circle((3.75, 0.3), 0.10, color="white"))

    # arrows
    arrow(ax, (3.75, 10.42), (3.75, 10.10))
    arrow(ax, (3.75, 9.50), (3.75, 9.20))
    arrow(ax, (3.75, 8.60), (3.75, 8.30))
    arrow(ax, (3.75, 7.70), (3.75, 7.40))
    arrow(ax, (3.10, 6.85), (1.6, 6.45), label="так", fs=9)
    arrow(ax, (4.40, 6.85), (5.9, 6.45), label="ні", fs=9)
    arrow(ax, (1.6, 5.80), (3.4, 5.30))
    arrow(ax, (5.9, 5.80), (4.1, 5.30))
    arrow(ax, (3.75, 4.70), (3.75, 4.30))
    arrow(ax, (3.75, 3.70), (3.75, 3.30))
    arrow(ax, (3.75, 2.70), (3.75, 2.30))
    arrow(ax, (3.75, 1.70), (3.75, 1.30))
    arrow(ax, (3.75, 0.70), (3.75, 0.50))

    save(fig, "fig_2_11_activity")


# ---------------------------------------------------------------------------
# 2.12  DB schema (Supabase)
# ---------------------------------------------------------------------------
def fig_2_12_db():
    fig, ax = new_canvas(11, 7)
    ax.set_xlim(0, 11); ax.set_ylim(0, 7)

    def table(cx, cy, name, cols, w=3.0):
        h = 0.45 + len(cols) * 0.32
        rect(ax, cx, cy, w, h, "", fc="white", ec="black")
        ax.text(cx, cy + h / 2 - 0.22, name, ha="center", va="center",
                fontsize=11, fontweight="bold")
        ax.add_line(plt.Line2D([cx - w / 2 + 0.05, cx + w / 2 - 0.05],
                               [cy + h / 2 - 0.40, cy + h / 2 - 0.40],
                               color="black", lw=0.7))
        for i, c in enumerate(cols):
            ax.text(cx - w / 2 + 0.15, cy + h / 2 - 0.65 - i * 0.32,
                    c, ha="left", va="center", fontsize=9)
        return (cx, cy, w, h)

    t_users = table(2.0, 5.2, "auth.users (Supabase)", [
        "PK  id : uuid",
        "    email : text",
        "    encrypted_password : text",
        "    created_at : timestamptz",
    ])
    t_proj = table(6.0, 5.2, "projects", [
        "PK  id : uuid",
        "FK  user_id : uuid",
        "    name : text",
        "    description : text",
        "    created_at : timestamptz",
    ])
    t_ana = table(9.5, 5.2, "analyses", [
        "PK  id : uuid",
        "FK  project_id : uuid",
        "FK  user_id : uuid",
        "    file_name : text",
        "    storage_path : text",
        "    status : text",
        "    progress_pct : int",
        "    progress_stage : text",
        "    created_at : timestamptz",
    ])
    t_res = table(6.0, 1.6, "analysis_results", [
        "PK  id : uuid",
        "FK  analysis_id : uuid",
        "    sentiment_pos : int",
        "    sentiment_neu : int",
        "    sentiment_neg : int",
        "    summary_text : text",
        "    payload : jsonb",
    ])

    arrow(ax, (3.5, 5.2), (4.5, 5.2), label="1 .. *", style="-")
    arrow(ax, (7.5, 5.2), (8.0, 5.2), label="1 .. *", style="-")
    arrow(ax, (9.5, 4.2), (6.0, 2.7), label="1 .. 1", style="-")

    save(fig, "fig_2_12_db")


# ---------------------------------------------------------------------------
# 3.1  Project structure
# ---------------------------------------------------------------------------
def fig_3_1_structure():
    fig, ax = new_canvas(8, 9)
    ax.set_xlim(0, 8); ax.set_ylim(0, 9)
    ax.text(4.0, 8.7, "Структура проєкту", ha="center", va="center",
            fontsize=12, fontweight="bold")

    tree = [
        (0.3, 8.1, "ReviewScope/", True),
        (0.6, 7.7, "├── frontend/", True),
        (1.1, 7.4, "│    ├── src/components/   – React-компоненти UI"),
        (1.1, 7.1, "│    ├── src/pages/        – сторінки SPA"),
        (1.1, 6.8, "│    └── vite.config.js"),
        (0.6, 6.4, "├── src/", True),
        (1.1, 6.1, "│    ├── api/              – FastAPI: routes, auth, main"),
        (1.1, 5.8, "│    ├── services/         – AnalysisService, ProjectService"),
        (1.1, 5.5, "│    ├── models/           – BERT / BERTopic / KeyBERT обгортки"),
        (1.1, 5.2, "│    ├── nlp/              – pipeline, aspect, summary"),
        (1.1, 4.9, "│    ├── parsers/          – csv_parser (auto-detect)"),
        (1.1, 4.6, "│    ├── schemas/          – Pydantic-моделі"),
        (1.1, 4.3, "│    └── database/         – клієнт Supabase"),
        (0.6, 3.9, "├── config/                – env + конфігурація", True),
        (0.6, 3.6, "├── scripts/               – допоміжні утиліти", True),
        (0.6, 3.3, "├── docs/                  – діаграми, документація", True),
        (0.6, 3.0, "├── docker-compose.yml"),
        (0.6, 2.7, "├── requirements.txt"),
        (0.6, 2.4, "└── README.md"),
    ]
    for x, y, t, *bold in tree:
        weight = "bold" if bold and bold[0] else "normal"
        ax.text(x, y, t, ha="left", va="center", fontsize=10,
                fontweight=weight, family="DejaVu Sans Mono")

    save(fig, "fig_3_1_structure")


# ---------------------------------------------------------------------------
# 3.2  Class diagram (NLP core)
# ---------------------------------------------------------------------------
def fig_3_2_classes():
    fig, ax = new_canvas(11, 8)
    ax.set_xlim(0, 11); ax.set_ylim(0, 8)

    def cls(cx, cy, name, attrs, methods, w=3.0):
        rows = ["+" + a for a in attrs] + ["+" + m for m in methods]
        h = 0.6 + 0.32 * (len(rows) + 1) + 0.25
        rect(ax, cx, cy, w, h, "", fc="white", ec="black")
        ax.text(cx, cy + h / 2 - 0.22, name, ha="center", va="center",
                fontsize=11, fontweight="bold")
        y_attr = cy + h / 2 - 0.55
        ax.add_line(plt.Line2D([cx - w / 2 + 0.05, cx + w / 2 - 0.05],
                               [y_attr + 0.18, y_attr + 0.18],
                               color="black", lw=0.7))
        for i, a in enumerate(attrs):
            ax.text(cx - w / 2 + 0.10, y_attr - i * 0.30,
                    "+ " + a, ha="left", va="center", fontsize=9)
        y_method = y_attr - len(attrs) * 0.30 - 0.10
        ax.add_line(plt.Line2D([cx - w / 2 + 0.05, cx + w / 2 - 0.05],
                               [y_method + 0.18, y_method + 0.18],
                               color="black", lw=0.7))
        for i, m in enumerate(methods):
            ax.text(cx - w / 2 + 0.10, y_method - i * 0.30,
                    "+ " + m, ha="left", va="center", fontsize=9)
        return (cx, cy, w, h)

    pl = cls(5.5, 6.5, "NLPPipeline",
             ["sentiment", "aspects", "topics", "keywords", "summary"],
             ["run(reviews, options) : dict"], w=3.6)

    sa = cls(1.5, 3.0, "SentimentAnalyzer",
             ["model : BertModel", "device : str"],
             ["predict(text) : Sentiment"])
    aa = cls(4.2, 3.0, "AspectAnalyzer",
             ["nlp : spacy.Language", "extra_blocklist : list"],
             ["fit(reviews)", "aggregate() : list"], w=3.0)
    te = cls(7.4, 3.0, "TopicExtractor",
             ["topic_model : BERTopic"],
             ["fit_transform(texts)", "get_topic_info() : list"])
    ke = cls(10.0, 3.0, "KeywordExtractor",
             ["model : KeyBERT"],
             ["extract(texts) : list"])

    sg = cls(5.5, 0.5, "SummaryGenerator",
             ["templates"],
             ["build(results) : str"], w=3.0)

    arrow(ax, pl, sa, style="-|>")
    arrow(ax, pl, aa, style="-|>")
    arrow(ax, pl, te, style="-|>")
    arrow(ax, pl, ke, style="-|>")
    arrow(ax, pl, sg, style="-|>")

    save(fig, "fig_3_2_classes")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    print("Generating diagrams ...")
    fig_2_1_usecase_general()
    fig_2_2_usecase_upload()
    fig_2_3_usecase_nlp()
    fig_2_4_usecase_results()
    fig_2_5_usecase_auth()
    fig_2_6_usecase_projects()
    fig_2_7_architecture()
    fig_2_8_deployment()
    fig_2_9_layers()
    fig_2_10_sequence()
    fig_2_11_activity()
    fig_2_12_db()
    fig_3_1_structure()
    fig_3_2_classes()
    print("Done.")


if __name__ == "__main__":
    main()
