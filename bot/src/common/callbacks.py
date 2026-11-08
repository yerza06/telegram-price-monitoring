from aiogram.types import CallbackQuery, Message


async def finish_callback(callback: CallbackQuery, text: str) -> None:
    """Заменяет сообщение с кнопками на `text` и закрывает «часики» на кнопке."""
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text)
        await callback.answer()
    else:  # сообщение с кнопками слишком старое, редактировать нельзя
        await callback.answer(text, show_alert=True)
