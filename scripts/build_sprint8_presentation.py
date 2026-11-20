"""Сборка презентации спринта 8 для StudyMate.

Скрипт разовый: генерирует docs/sprint-8/presentation.pptx.
Запуск: .venv/bin/python scripts/build_sprint8_presentation.py
"""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

DARK = RGBColor(0x14, 0x14, 0x16)
BLUE = RGBColor(0x25, 0x57, 0xE8)
GREY = RGBColor(0x6B, 0x72, 0x80)
LIGHT = RGBColor(0xF4, 0xF6, 0xFB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x2C, 0x6E, 0x18)
RED = RGBColor(0xA5, 0x21, 0x21)
LINE = RGBColor(0xDD, 0xE2, 0xEA)

W, H = Inches(13.333), Inches(7.5)


def add_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def textbox(slide, left, top, width, height, text, size=18, bold=False,
            color=DARK, align=PP_ALIGN.LEFT, spacing=6, font="Calibri"):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    lines = text if isinstance(text, list) else [text]
    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.alignment = align
        paragraph.space_after = Pt(spacing)
        run = paragraph.runs[0]
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = font
    return box


def bullets(slide, left, top, width, height, items, size=17, color=DARK, spacing=10):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    for index, item in enumerate(items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.space_after = Pt(spacing)
        run = paragraph.add_run()
        run.text = "•  " + item
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = "Calibri"
    return box


def header(slide, title, kicker=None):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = DARK
    bar.line.fill.background()
    top = Inches(0.55)
    if kicker:
        textbox(slide, Inches(0.9), Inches(0.42), Inches(11.5), Inches(0.35),
                kicker.upper(), size=12, bold=True, color=BLUE)
        top = Inches(0.78)
    textbox(slide, Inches(0.9), top, Inches(11.5), Inches(0.8), title, size=32, bold=True)


def card(slide, left, top, width, height, fill=LIGHT, line=LINE):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.adjustments[0] = 0.06
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(1)
    shape.shadow.inherit = False
    return shape


def table(slide, left, top, width, height, rows, widths, header_fill=DARK, size=13):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), left, top, width, height)
    table_obj = shape.table
    for index, column_width in enumerate(widths):
        table_obj.columns[index].width = Emu(int(column_width))
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            cell = table_obj.cell(row_index, column_index)
            cell.text = str(value)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            paragraph = cell.text_frame.paragraphs[0]
            run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
            run.font.size = Pt(size)
            run.font.name = "Calibri"
            if row_index == 0:
                run.font.bold = True
                run.font.color.rgb = WHITE
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_fill
            else:
                run.font.color.rgb = DARK
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE if row_index % 2 else LIGHT
    return table_obj


def footer(slide, number):
    textbox(slide, Inches(0.9), Inches(6.95), Inches(6), Inches(0.3),
            "StudyMate · Sprint 8", size=11, color=GREY)
    textbox(slide, Inches(11.9), Inches(6.95), Inches(0.8), Inches(0.3),
            str(number), size=11, color=GREY, align=PP_ALIGN.RIGHT)


def build():
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    # 1 — титул
    slide = add_slide(prs)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = DARK
    bg.line.fill.background()
    textbox(slide, Inches(0.9), Inches(2.1), Inches(11), Inches(0.5),
            "SPRINT 8", size=16, bold=True, color=RGBColor(0x8F, 0xA8, 0xFF))
    textbox(slide, Inches(0.9), Inches(2.6), Inches(11.4), Inches(1.8),
            "Совместимость кандидата\nс требованиями роли", size=44, bold=True, color=WHITE)
    textbox(slide, Inches(0.9), Inches(4.6), Inches(11), Inches(0.9),
            "Бизнес-правила и формула расчёта · экран входящих заявок · "
            "требования к роли · статус обучения в профиле",
            size=16, color=RGBColor(0xB4, 0xB8, 0xC4))
    textbox(slide, Inches(0.9), Inches(5.9), Inches(11), Inches(0.5),
            "StudyMate · 2026", size=13, color=RGBColor(0x6B, 0x72, 0x80))

    # 2 — проблема и решение
    slide = add_slide(prs)
    header(slide, "Зачем это нужно", "Контекст")
    card(slide, Inches(0.9), Inches(1.9), Inches(5.5), Inches(4.2), WHITE, LINE)
    textbox(slide, Inches(1.2), Inches(2.15), Inches(4.9), Inches(0.5),
            "Было", size=20, bold=True, color=RED)
    bullets(slide, Inches(1.2), Inches(2.75), Inches(4.9), Inches(3.1), [
        "Руководитель видит только текст заявки",
        "Навыки кандидата и требования роли никак не сопоставлены",
        "Решение «принять / отклонить» принимается вручную и на глаз",
        "Роль в проекте нельзя описать: ни требований, ни навыков",
    ], size=15, spacing=12)
    card(slide, Inches(6.9), Inches(1.9), Inches(5.5), Inches(4.2), WHITE, LINE)
    textbox(slide, Inches(7.2), Inches(2.15), Inches(4.9), Inches(0.5),
            "Стало", size=20, bold=True, color=GREEN)
    bullets(slide, Inches(7.2), Inches(2.75), Inches(4.9), Inches(3.1), [
        "В карточке заявки — процент совместимости",
        "Совпавшие, недостающие и дополнительные навыки",
        "Требования к роли задаёт автор проекта",
        "Навыки раскрываются по требованию, по умолчанию — только процент",
    ], size=15, spacing=12)

    # 3 — схема расчёта
    slide = add_slide(prs)
    header(slide, "Как считается совместимость", "Схема")
    textbox(slide, Inches(0.9), Inches(1.85), Inches(11.5), Inches(0.5),
            "Навыки кандидата сопоставляются с обязательными навыками конкретной роли "
            "по уникальным идентификаторам (UUID):", size=16, color=GREY)
    steps = [
        ("Профиль кандидата", "навыки пользователя\nиз карточки профиля", Inches(0.9)),
        ("Требования роли", "обязательные навыки\nвыбранной роли", Inches(3.82)),
        ("Пересечение", "совпавшие /\nнедостающие /\nдополнительные", Inches(6.74)),
        ("Процент", "100 × совпавших\n/ обязательных", Inches(9.66)),
    ]
    for title, subtitle, left in steps:
        card(slide, left, Inches(2.75), Inches(2.75), Inches(1.7), WHITE, BLUE)
        textbox(slide, left + Inches(0.2), Inches(2.92), Inches(2.35), Inches(0.4),
                title, size=15, bold=True)
        textbox(slide, left + Inches(0.2), Inches(3.35), Inches(2.35), Inches(1.0),
                subtitle.split("\n"), size=12, color=GREY, spacing=2)
    for arrow_left in (Inches(3.68), Inches(6.6), Inches(9.52)):
        textbox(slide, arrow_left, Inches(3.35), Inches(0.2), Inches(0.4), "→", size=18, color=BLUE)
    card(slide, Inches(0.9), Inches(4.85), Inches(11.5), Inches(1.5), LIGHT, LINE)
    textbox(slide, Inches(1.15), Inches(5.0), Inches(11), Inches(0.4),
            "Результат в контексте заявки — application.skill_match", size=15, bold=True)
    textbox(slide, Inches(1.15), Inches(5.4), Inches(11), Inches(0.9),
            [("match_percent · matched_count / required_count · "
              "matched_skills · missing_skills · extra_skills")],
            size=13, color=GREY)
    footer(slide, 3)

    # 4 — формула
    slide = add_slide(prs)
    header(slide, "Формула", "Расчёт")
    card(slide, Inches(0.9), Inches(1.85), Inches(11.5), Inches(1.5), DARK, DARK)
    textbox(slide, Inches(1.2), Inches(2.15), Inches(11), Inches(0.9),
            "процент = 100 × (совпавших навыков) / (обязательных навыков роли)",
            size=24, bold=True, color=WHITE)
    textbox(slide, Inches(0.9), Inches(3.55), Inches(11.5), Inches(0.5),
            "Округление только итогового значения, до целого; половина — вверх. "
            "Реализация в коде:", size=15, color=GREY)
    card(slide, Inches(0.9), Inches(4.05), Inches(11.5), Inches(0.8), LIGHT, LINE)
    textbox(slide, Inches(1.15), Inches(4.2), Inches(11), Inches(0.5),
            "(200 × matched + required) // (2 × required)", size=18, bold=True, color=BLUE)
    bullets(slide, Inches(0.9), Inches(5.05), Inches(11.5), Inches(1.6), [
        "Целочисленная арифметика без плавающей точки — результат детерминирован",
        "Профессиональные (hard) и гибкие (soft) навыки весят одинаково",
        "Дополнительные навыки кандидата в числитель не входят",
        "Нет требований у роли → match_percent = None («Нет данных»), а не 0%",
    ], size=15, spacing=8)
    footer(slide, 4)

    # 5 — бизнес-правила
    slide = add_slide(prs)
    header(slide, "Бизнес-правила расчёта", "Правила")
    rules = [
        ("01", "Сравнение по UUID", "Один и тот же навык из справочника считается один раз; дубли невозможны."),
        ("02", "База — требования роли", "Знаменатель всегда число обязательных навыков роли, а не профиля."),
        ("03", "Ровно три группы", "Совпадают = пересечение, Не хватает = роль − профиль, Дополнительные = профиль − роль."),
        ("04", "Одинаковый вес", "Hard и soft требования не имеют приоритета друг перед другом."),
        ("05", "Доп. навыки не влияют", "Лишние навыки не повышают и не понижают процент."),
        ("06", "Только своя роль", "Требования соседних ролей проекта в расчёт не попадают."),
    ]
    for index, (num, title, text) in enumerate(rules):
        column = index % 2
        row = index // 2
        left = Inches(0.9) + column * Inches(5.85)
        top = Inches(1.85) + row * Inches(1.55)
        card(slide, left, top, Inches(5.55), Inches(1.35), WHITE, LINE)
        textbox(slide, left + Inches(0.25), top + Inches(0.18), Inches(0.5), Inches(0.4),
                num, size=16, bold=True, color=BLUE)
        textbox(slide, left + Inches(0.85), top + Inches(0.15), Inches(4.5), Inches(0.4),
                title, size=15, bold=True)
        textbox(slide, left + Inches(0.85), top + Inches(0.55), Inches(4.5), Inches(0.7),
                text, size=12, color=GREY)
    footer(slide, 5)

    # 6 — бизнес-правила: состояния
    slide = add_slide(prs)
    header(slide, "Граничные состояния и правила обновления", "Правила")
    rows = [
        ["Ситуация", "Поведение"],
        ["Требований у роли нет", "«Нет данных» и пояснение «У роли не заданы требуемые навыки» (процент не 0)"],
        ["Профиль кандидата пуст", "0% и «Кандидат пока не указал навыки»"],
        ["Требования совпали полностью", "100%, группа «Не хватает» не выводится"],
        ["Заявка принята или отклонена", "Процент сохраняется, добавляется «По текущим навыкам и требованиям роли»"],
        ["Навыки или требования изменились", "Пересчёт при следующей загрузке страницы, данные не кэшируются"],
        ["Сбой загрузки данных", "Ошибка страницы — процент по неполным данным не показывается"],
        ["Совместимость и статус заявки", "Процент не меняет статус и не блокирует действия руководителя"],
    ]
    table(slide, Inches(0.9), Inches(1.85), Inches(11.5), Inches(4.3), rows,
          [Inches(4.0), Inches(7.5)])
    footer(slide, 6)

    # 7 — примеры
    slide = add_slide(prs)
    header(slide, "Формула на числах", "Примеры")
    rows = [
        ["Совпало", "Обязательных", "Точный результат", "На экране"],
        ["0", "5", "0,00", "0%"],
        ["1", "8", "12,50 → вверх", "13%"],
        ["2", "5", "40,00", "40%"],
        ["3", "5", "60,00", "60%"],
        ["3", "4", "75,00", "75%"],
        ["5", "8", "62,50 → вверх", "63%"],
        ["4", "4", "100,00", "100%"],
        ["—", "0", "деление невозможно", "«Нет данных»"],
    ]
    table(slide, Inches(0.9), Inches(1.85), Inches(6.6), Inches(4.4), rows,
          [Inches(1.3), Inches(1.7), Inches(1.9), Inches(1.7)])
    card(slide, Inches(7.9), Inches(1.85), Inches(4.5), Inches(4.4), LIGHT, LINE)
    textbox(slide, Inches(8.2), Inches(2.1), Inches(4.0), Inches(0.4),
            "Что это значит для руководителя", size=15, bold=True)
    bullets(slide, Inches(8.2), Inches(2.6), Inches(4.0), Inches(3.4), [
        "Процент — не оценка «качества» студента, а покрытие требований роли",
        "1 из 8 = 13%: кандидат почти не покрывает требования",
        "Дополнительные навыки видны отдельно и на процент не влияют",
        "Отсутствие требований — не 0%, а «нет данных»",
    ], size=13, spacing=10)
    footer(slide, 7)

    # 8 — демо на реальных данных
    slide = add_slide(prs)
    header(slide, "Проверка на реальных данных", "Демо")
    demo_rows = [
        ["Кандидат", "Роль", "Совпало", "Процент"],
        ["Артём Смирнов", "ML-инженер", "3 из 5", "60%"],
        ["Дарья Волкова", "ML-инженер", "2 из 5", "40%"],
        ["Максим Кузнецов", "UX/UI-дизайнер", "4 из 4", "100%"],
    ]
    table(slide, Inches(0.9), Inches(1.85), Inches(6.6), Inches(2.2), demo_rows,
          [Inches(2.2), Inches(2.0), Inches(1.2), Inches(1.2)])
    textbox(slide, Inches(0.9), Inches(4.3), Inches(6.6), Inches(1.9), [
        "Артём: совпали NLP, PyTorch, Python; не хватает FastAPI и машинного обучения → 3 / 5 = 60%",
        "Дарья: совпали Python и машинное обучение; не хватает FastAPI, NLP, PyTorch → 2 / 5 = 40%",
        "Максим: совпали все четыре требования UX/UI-роли → 100%",
    ], size=13, color=GREY, spacing=8)
    card(slide, Inches(7.9), Inches(1.85), Inches(4.5), Inches(4.35), WHITE, LINE)
    textbox(slide, Inches(8.2), Inches(2.1), Inches(4.0), Inches(0.4),
            "Как это выглядит", size=15, bold=True)
    card(slide, Inches(8.2), Inches(2.6), Inches(3.9), Inches(1.15), LIGHT, LINE)
    textbox(slide, Inches(8.4), Inches(2.72), Inches(3.5), Inches(0.4),
            "Совместимость по навыкам", size=12, bold=True)
    textbox(slide, Inches(8.4), Inches(3.05), Inches(3.5), Inches(0.5),
            "60% · совпало 3 из 5 навыков", size=13, bold=True, color=BLUE)
    textbox(slide, Inches(8.2), Inches(3.95), Inches(3.9), Inches(0.4),
            "Подробности  ⊕", size=13, bold=True, color=BLUE)
    textbox(slide, Inches(8.4), Inches(4.35), Inches(3.6), Inches(0.4),
            "Совпадают 3 · Не хватает 2", size=12, color=GREY)
    textbox(slide, Inches(8.4), Inches(4.8), Inches(3.6), Inches(0.4),
            "Дополнительные навыки  ⊕", size=12, color=GREY)
    textbox(slide, Inches(8.2), Inches(5.35), Inches(3.6), Inches(0.7),
            "По умолчанию — только процент и количество", size=12, color=GREY)
    footer(slide, 8)

    # 9 — где считается
    slide = add_slide(prs)
    header(slide, "Где живёт расчёт", "Реализация")
    bullets(slide, Inches(0.9), Inches(1.9), Inches(11.5), Inches(4.2), [
        "applications/services.py → skill_match(candidate_skills, required_skills) — чистый расчёт, без БД и без побочных эффектов",
        "list_project_applications() заполняет application.skill_match для каждой заявки при загрузке страницы",
        "Навыки кандидатов и требования ролей загружаются пакетно (prefetch_related): число запросов не зависит от числа заявок",
        "Процент, счётчики и списки строятся из одного и того же набора данных — расхождений быть не может",
        "Списки сортируются по названию и UUID: порядок навыков не «прыгает» между запросами",
        "Доступ — только автору проекта: GET /projects/<project_id>/applications/",
    ], size=16, spacing=14)
    footer(slide, 9)

    # 10 — UI
    slide = add_slide(prs)
    header(slide, "Карточка заявки: как видит руководитель", "Интерфейс")
    bullets(slide, Inches(0.9), Inches(1.9), Inches(6.2), Inches(3.0), [
        "Вкладки со счётчиками: Все / На рассмотрении / Приняты / Отклонены",
        "Фильтр по статусу через query-параметр, неизвестное значение → «Все»",
        "Порядок — «новые сначала»",
        "Процент, роль, дата и сопроводительное письмо",
        "Кнопки «Принять» / «Отклонить» только для заявок на рассмотрении",
    ], size=15, spacing=12)
    card(slide, Inches(7.4), Inches(1.9), Inches(5.0), Inches(4.4), LIGHT, LINE)
    textbox(slide, Inches(7.65), Inches(2.15), Inches(4.5), Inches(0.4),
            "Раскрытие навыков в два уровня", size=15, bold=True)
    steps_ui = [
        ("1. По умолчанию", "только процент и количество"),
        ("2. «Подробности»", "совпадают и не хватает"),
        ("3. «Дополнительные навыки»", "вторая ступень, внутри подробностей"),
    ]
    for index, (title, text) in enumerate(steps_ui):
        top = Inches(2.7) + index * Inches(1.15)
        card(slide, Inches(7.65), top, Inches(4.5), Inches(0.95), WHITE, LINE)
        textbox(slide, Inches(7.9), top + Inches(0.12), Inches(4.0), Inches(0.35),
                title, size=13, bold=True)
        textbox(slide, Inches(7.9), top + Inches(0.47), Inches(4.0), Inches(0.35),
                text, size=12, color=GREY)
    textbox(slide, Inches(7.65), Inches(6.1), Inches(4.5), Inches(0.4),
            "Нативные <details> — работает без JS и с клавиатуры", size=11, color=GREY)
    footer(slide, 10)

    # 11 — требования к роли и профиль
    slide = add_slide(prs)
    header(slide, "Что ещё входит в спринт", "Смежные задачи")
    card(slide, Inches(0.9), Inches(1.85), Inches(5.55), Inches(4.4), WHITE, LINE)
    textbox(slide, Inches(1.2), Inches(2.1), Inches(5.0), Inches(0.4),
            "Требования к роли", size=18, bold=True)
    bullets(slide, Inches(1.2), Inches(2.6), Inches(5.0), Inches(3.4), [
        "Автор задаёт требования при создании проекта",
        "На странице проекта они раскрываются рядом с названием роли",
        "Внутри: описание требований + обязательные навыки",
        "Нет требований — блок не выводится",
        "Требования роли — источник данных для расчёта совместимости",
    ], size=14, spacing=10)
    card(slide, Inches(6.9), Inches(1.85), Inches(5.5), Inches(4.4), WHITE, LINE)
    textbox(slide, Inches(7.2), Inches(2.1), Inches(4.9), Inches(0.4),
            "Статус обучения в профиле", size=18, bold=True)
    bullets(slide, Inches(7.2), Inches(2.6), Inches(4.9), Inches(3.4), [
        "Обучаюсь / Закончил обучение",
        "Уровень: бакалавриат, специалитет, магистратура, аспирантура",
        "Курс доступен только после выбора уровня",
        "Свой набор курсов: 1–4 / 1–5 / 1–2 / 1–3",
        "При выпуске курс очищается",
    ], size=14, spacing=10)
    footer(slide, 11)

    # 12 — итоги
    slide = add_slide(prs)
    header(slide, "Итоги и что дальше", "Заключение")
    card(slide, Inches(0.9), Inches(1.85), Inches(5.55), Inches(3.6), LIGHT, LINE)
    textbox(slide, Inches(1.2), Inches(2.1), Inches(5.0), Inches(0.4),
            "Сделано", size=18, bold=True, color=GREEN)
    bullets(slide, Inches(1.2), Inches(2.6), Inches(5.0), Inches(2.7), [
        "Расчёт совместимости с покрытием всех граничных случаев",
        "Экран входящих заявок с вкладками и счётчиками",
        "Требования к роли и раскрытие навыков в два уровня",
        "Статус обучения и уровень образования в профиле",
    ], size=14, spacing=9)
    card(slide, Inches(6.9), Inches(1.85), Inches(5.5), Inches(3.6), WHITE, LINE)
    textbox(slide, Inches(7.2), Inches(2.1), Inches(4.9), Inches(0.4),
            "Дальше", size=18, bold=True, color=BLUE)
    bullets(slide, Inches(7.2), Inches(2.6), Inches(4.9), Inches(2.7), [
        "Сортировка заявок по проценту совместимости",
        "Фильтр по роли в общем контракте US-10",
        "Описание skill_match в openapi.yaml",
        "Прогон на целевых версиях Python 3.13 и PostgreSQL 17",
    ], size=14, spacing=9)
    textbox(slide, Inches(0.9), Inches(5.7), Inches(11.5), Inches(0.8),
            "Процент отвечает на один вопрос: насколько кандидат покрывает требования "
            "конкретной роли. Всё остальное — контекст для решения руководителя.",
            size=15, color=GREY)
    footer(slide, 12)

    notes = {1: 'Тема: спринт 8 StudyMate. Две части — блок совместимости кандидата с требованиями роли и сопутствующие изменения интерфейса.', 2: 'Проблема: руководитель принимал решение по заявке, видя только текст письма. Требований к ролям в проекте не было вообще. Решение: требования задаются при создании проекта, карточка заявки считает процент покрытия.', 3: 'Сопоставление идёт по UUID навыков из общего справочника. На входе два множества — навыки профиля кандидата и обязательные навыки конкретной роли. На выходе три группы и процент.', 4: 'Формула: 100 × совпавших / обязательных. Округление только итога, половина вверх; в коде это целочисленная формула (200*m + r) // (2*r). Пустые требования — None, а не 0.', 5: 'Шесть ключевых правил расчёта. Главное: знаменатель — требования роли, а не профиль; hard и soft весят одинаково; дополнительные навыки в числитель не входят.', 6: 'Граничные случаи: нет требований, пустой профиль, полное совпадение, принятые и отклонённые заявки, изменение данных после отклика, сбой загрузки. Пересчёт всегда при загрузке страницы.', 7: 'Таблица примеров: 0 из 5 — 0%, 1 из 8 — 12,5% → 13%, 3 из 4 — 75%, 4 из 4 — 100%, нет требований — «Нет данных».', 8: 'Реальные заявки из демо-базы: 60%, 40% и 100%. Справа — как блок выглядит: по умолчанию только процент, дальше два уровня раскрытия.', 9: 'Расчёт изолирован в сервисном слое. Загрузка пакетная, поэтому число запросов не растёт с числом заявок. Доступ — только автору проекта.', 10: 'Экран входящих: вкладки со счётчиками, фильтр по статусу. Навыки раскрываются в два уровня: «Подробности» → совпадают и не хватает, внутри — дополнительные.', 11: 'Смежные задачи спринта: требования к роли задаются автором и раскрываются на странице проекта; в профиле появился статус обучения с уровнем и зависимым выбором курса.', 12: 'Итоги и следующий шаг: сортировка по проценту, фильтр по роли, описание в openapi, прогон на целевых версиях Python и PostgreSQL.'}
    for index, slide in enumerate(prs.slides, 1):
        if index in notes:
            slide.notes_slide.notes_text_frame.text = notes[index]

    prs.save("docs/sprint-8/presentation.pptx")


if __name__ == "__main__":
    build()
    print("saved docs/sprint-8/presentation.pptx")
