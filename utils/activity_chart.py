import io
import matplotlib.pyplot as plt
import pandas as pd

from db.messages import plot_user_activity


async def make_activity_chart(chat_id: int, user_id: int):
    user_activity = await plot_user_activity(chat_id=chat_id, user_id=user_id)

    # Конвертируем в DataFrame
    df = pd.DataFrame(user_activity, columns=["date", "count"])
    df["date"] = pd.to_datetime(df["date"])  # оставляем datetime для корректного порядка

    # Заполняем пропущенные дни нулями
    df = df.set_index("date").asfreq("D", fill_value=0).reset_index()

    # Создаём подписи для оси X
    df["date_str"] = df["date"].dt.strftime("%d.%m")

    # Рисуем график
    plt.figure(figsize=(10, 5))
    plt.bar(df["date_str"], df["count"], color="#1d74e6")
    plt.title("Статистика активности", fontsize=12)
    plt.ylabel("Кол-во сообщений")
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)

    return buffer.getvalue()
