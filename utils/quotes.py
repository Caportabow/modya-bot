import base64
import random
from playwright.async_api import async_playwright

async def make_quote(materials: list) -> bytes:
    """Создаёт цитату из сообщения."""
    # Необходимые html-элементы
    content = """
    <div class="chat-message">
      <div class="avatar" {{letter-styling}}>{{avatar}}</div>
      <div class="message-content">
        <div class="chat-bubble">
          <div class="username">{{name}}</div>
          {{media}}
          <div class="message">{{text}}</div>
        </div>
      </div>
    </div>
    """
    additional_content = """
    <div class="chat-message consecutive">
      <div class="avatar"></div> <div class="message-content">
        {{bubbles}}
      </div>
    </div>
    """
    additional_content_bubble = """
    <div class="chat-bubble">
        {{media}}
        <div class="message">{{text}}</div>
    </div>
    """
    media_content = """
    <img
        class="message-media"
        src="{{source}}"
    >
    </img>
    """

    quote_content = ""
    i = 0
    while i < len(materials):
        m = materials[i]
        avatar = m.get("avatar", "")
        name = m["name"]
        text = m["text"]
        media = m["media"] if m["media"] else ""

        # Формируем аватарку
        if avatar:
            html_avatar = f'<img src="data:image/jpeg;base64,{base64.b64encode(avatar).decode("utf-8")}" />'
        else:
            html_avatar = name[0].upper()
        
        # Формируем медиа
        if media:
            encoded_media = f"data:{media['type']};base64,{base64.b64encode(media['source']).decode('utf-8')}"
            media = media_content.replace("{{source}}", encoded_media)

        # Обрезаем текст, если он слишком длинный
        text = text[:710] + ("..." if len(text) > 710 else "")

        # Начинаем формировать контент для текущей группы
        random_color = 'style="{{style}}"'.replace(
                "{{style}}",
                random.choice(
                    [
                        'background-image: linear-gradient(45deg, #4facfe, #00f2fe);',
                        'background-image: linear-gradient(45deg, #ff6f61, #ff8c7a);',
                        'background-image: linear-gradient(45deg, #43e97b, #39ffb2);',
                    ]
                )
            )
        
        group_content = content.replace("{{avatar}}", html_avatar).replace("{{letter-styling}}", random_color).replace("{{name}}", name).replace("{{text}}", text).replace("{{media}}", media)

        # Проверяем следующие элементы на совпадение
        j = i + 1
        group_additional_content = ""
        while j < len(materials):
            next_m = materials[j]
            next_text = next_m["text"]
            next_text = next_text[:710] + ("..." if len(next_text) > 710 else "")
            next_name = next_m["name"]

            if next_name == name:
                # Добавляем HTML следующего элемента в текущую группу
                next_media = next_m["media"] if next_m["media"] else ""
                if next_media:
                    encoded_media = f"data:{next_media["type"]};base64,{base64.b64encode(next_media["source"]).decode("utf-8")}"
                    next_media = media_content.replace("{{source}}", encoded_media)
                group_additional_content += additional_content_bubble.replace("{{text}}", next_text).replace("{{media}}", next_media)
                j += 1
            else:
                break

        if group_additional_content:
            quote_content += group_content + additional_content.replace("{{bubbles}}", group_additional_content)
        else:
            quote_content += group_content

        # Переходим к следующему уникальному элементу
        i = j

    # Читаем HTML-шаблон
    with open("resources/quote_template.html", "r", encoding="utf-8") as f:
        template = f.read()

    # подставляем данные
    html_code = (
        template
        .replace("{{messages}}", quote_content)
    )

    # Рендеринг через Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-gpu", "--no-sandbox"]
        )
        page = await browser.new_page()
        
        # Устанавливаем HTML
        await page.set_content(html_code)

        element = page.locator(".chat-container")
        # Получаем координаты элемента
        box = await element.bounding_box()

        # Размер страницы
        viewport_size = page.viewport_size
        w, page_height = viewport_size["width"], viewport_size["height"]

        # Расширяем область на 20px со всех сторон, не выходя за границы
        padding = 20
        clip = {
            "x": box["x"],  # без отступа слева
            "y": max(box["y"] - padding, 0),  # padding сверху
            "width": box["width"],  # уменьшаем ширину справа
            "height": min(box["height"] + 2 * padding, page_height - max(box["y"] - padding, 0))  # padding сверху и снизу
        }

        # Скриншот с учетом расширенной области
        screenshot_bytes = await page.screenshot(clip=clip, omit_background=True)
        
        await browser.close()

    return screenshot_bytes
