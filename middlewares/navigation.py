"""Middleware для управления навигационной историей"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Update
from aiogram.fsm.context import FSMContext


class NavigationMiddleware(BaseMiddleware):
    """Middleware для автоматического сохранения истории навигации"""
    
    # Максимальная длина истории навигации
    MAX_HISTORY_SIZE = 20
    
    # Callback data, которые не нужно сохранять в историю
    SKIP_CALLBACKS = {
        'back_navigation',  # Сама кнопка назад
        'main_menu',  # Главное меню - всегда доступно
    }
    
    # Callback data, которые очищают историю (начало нового flow)
    CLEAR_HISTORY_CALLBACKS = {
        'main_menu',
        'start_back',
    }
    
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка события"""
        state: FSMContext = data.get('state')
        
        # Обрабатываем только callback queries с state
        if isinstance(event, CallbackQuery) and state and event.data:
            callback_query = event
            callback_data = callback_query.data
            
            # Если это кнопка "Назад", восстанавливаем предыдущую страницу
            if callback_data == 'back_navigation':
                await self._navigate_back(state, data)
                # Продолжаем обработку - handler покажет предыдущую страницу
            
            # Если это команда очистки истории
            elif callback_data in self.CLEAR_HISTORY_CALLBACKS:
                await self._clear_history(state)
            
            # Если это обычная навигация - сохраняем в историю
            elif callback_data not in self.SKIP_CALLBACKS and not callback_data.startswith('download_'):
                await self._save_to_history(state, callback_data)
        
        # Вызываем оригинальный handler
        return await handler(event, data)
    
    async def _save_to_history(self, state: FSMContext, callback_data: str) -> None:
        """Сохранить текущий callback в историю"""
        data = await state.get_data()
        history = data.get('navigation_history', [])
        
        # Добавляем в историю только если это не дубликат последнего элемента
        if not history or history[-1] != callback_data:
            history.append(callback_data)
            
            # Ограничиваем размер истории
            if len(history) > self.MAX_HISTORY_SIZE:
                history = history[-self.MAX_HISTORY_SIZE:]
            
            await state.update_data(navigation_history=history)
    
    async def _navigate_back(self, state: FSMContext, data: Dict[str, Any]) -> None:
        """Вернуться на предыдущую страницу"""
        fsm_data = await state.get_data()
        history = fsm_data.get('navigation_history', [])
        
        if len(history) > 1:
            # Удаляем текущую страницу и берем предыдущую
            history.pop()  # Удаляем текущую
            previous_callback = history[-1] if history else 'main_menu'
            
            # Сохраняем обновленную историю
            await state.update_data(
                navigation_history=history,
                back_target=previous_callback
            )
        else:
            # Если истории нет - идем в главное меню
            await state.update_data(
                navigation_history=[],
                back_target='main_menu'
            )
    
    async def _clear_history(self, state: FSMContext) -> None:
        """Очистить историю навигации"""
        await state.update_data(navigation_history=[])

