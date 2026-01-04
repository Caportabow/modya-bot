import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates  # Импортируем модуль для работы с датами
import pandas as pd

from db.messages import plot_user_activity

async def make_activity_chart(chat_id: int, user_id: int):
    user_activity = await plot_user_activity(chat_id=chat_id, user_id=user_id)

    df = pd.DataFrame(user_activity, columns=["date", "count"])
    df["date"] = pd.to_datetime(df["date"])

    # Заполняем пропущенные дни нулями
    df = df.set_index("date").asfreq("D", fill_value=0).reset_index()

    # Рисуем график
    plt.figure(figsize=(10, 5))
    
    # ВАЖНО: Передаем df["date"] (datetime), а не строки.
    # width=0.8 означает ширину столбца в 0.8 дня (чтобы были небольшие отступы)
    plt.bar(df["date"], df["count"], color="#1d74e6", width=0.8)
    
    plt.title("Статистика активности", fontsize=12)
    plt.ylabel("Кол-во сообщений")

    # --- Настройка оси X ---
    ax = plt.gca() # Получаем текущие оси (Get Current Axes)

    # 1. Настраиваем частоту меток (Locator)
    # AutoDateLocator сам подберет оптимальный интервал, чтобы текст не слипался.
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    # 2. Настраиваем формат отображения (Formatter)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

    # Вращаем подписи, чтобы они выглядели аккуратно
    plt.xticks(rotation=45)
    # -----------------------

    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)

    return buffer.getvalue()