from aiogram.types import Message

def remove_message_entities(message: Message, text: str | None) -> str | None:
    if not text: text = message.text

    if message.entities and text:
        # Сортируем entities в обратном порядке по offset
        sorted_entities = sorted(message.entities, key=lambda e: e.offset, reverse=True)
        
        for entity in sorted_entities:
            # Вырезаем текст entity
            text = text[:entity.offset] + text[entity.offset + entity.length:]
    
    if not text or not text.strip():
        return None
    
    return text
