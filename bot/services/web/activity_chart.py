from config import ACTIVITY_CHART_TEMPLATE
from services.web import screenshot


async def make_activity_chart(stats):
    total_messages = sum(item['count'] for item in stats)
    max_count = max(item['count'] for item in stats) if stats else 1
    
    # Генерация ячеек (Logic)
    cells_html = ""
    for item in stats:
        count = item['count']
        date_str = item['date'].strftime("%d.%m.%y")
        
        # Расчет уровня яркости (от 1 до 4)
        ratio = count / max_count
        if ratio > 0.75: lvl = 4
        elif ratio > 0.4: lvl = 3
        elif ratio > 0.15: lvl = 2
        else: lvl = 1
        
        cells_html += f"""
        <div class="day-cell lvl-{lvl}">
            <span class="count">{count}</span>
            <span class="date">{date_str}</span>
        </div>"""
    
    html_body = f"""
    <div class="screenshot-wrapper" style="padding: 20px;">
        <div class="card">
            <div class="header">
                <div class="title">Статистика активности</div>
                <div class="total">Всего {total_messages} сообщ.</div>
            </div>
            <div class="grid">
                {cells_html}
            </div>
            <div class="footer">
                <span>Меньше</span>
                <div class="leg" style="background:var(--l0)"></div>
                <div class="leg" style="background:var(--l1)"></div>
                <div class="leg" style="background:var(--l2)"></div>
                <div class="leg" style="background:var(--l3)"></div>
                <div class="leg" style="background:var(--l4)"></div>
                <span>Больше</span>
            </div>
        </div>
    </div>
    """

    return await screenshot(html_body, ACTIVITY_CHART_TEMPLATE, ".screenshot-wrapper")
