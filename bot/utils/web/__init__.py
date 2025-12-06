from playwright.async_api import async_playwright

async def screenshot(html_body: str, template: str, core_element_name: str) -> bytes:
    """Преобразует HTML в изображение(bytes) с помощью headless браузера."""
    # подставляем данные
    html_code = (
        template
        .replace("{{ data }}", html_body)
    )

    # Рендеринг через Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-gpu", "--no-sandbox"]
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2
        )
        page = await context.new_page()
        
        # Устанавливаем HTML
        await page.set_content(html_code)

        await page.wait_for_load_state('domcontentloaded')

        # Находим элемент и делаем скриншот
        element = page.locator(core_element_name)
        screenshot_bytes = await element.screenshot(omit_background=True)
        
        await browser.close()

    return screenshot_bytes