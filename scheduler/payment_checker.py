"""
Периодическая проверка статуса платежей
Проверяет pending платежи и уведомляет админа при успешной оплате
"""
import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot

from database import get_db, PaymentRepository
from payments import YooKassaPayment
from handlers.webhook_handler import notify_user_payment_success, notify_admin_new_payment

logger = logging.getLogger(__name__)


class PaymentChecker:
    """Класс для периодической проверки статуса платежей"""
    
    def __init__(self, bot: Bot, check_interval: int = 60):
        """
        Args:
            bot: Экземпляр бота
            check_interval: Интервал проверки в секундах (по умолчанию 60)
        """
        self.bot = bot
        self.check_interval = check_interval
        self.yookassa = YooKassaPayment()
        self.is_running = False
        self._task = None
    
    async def start(self):
        """Запуск периодической проверки"""
        if self.is_running:
            logger.warning("Payment checker is already running")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info(f"Payment checker started (interval: {self.check_interval}s)")
    
    async def stop(self):
        """Остановка периодической проверки"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Payment checker stopped")
    
    async def _check_loop(self):
        """Основной цикл проверки"""
        while self.is_running:
            try:
                await self._check_pending_payments()
            except Exception as e:
                logger.error(f"Error in payment checker loop: {e}", exc_info=True)
            
            # Ждем до следующей проверки
            await asyncio.sleep(self.check_interval)
    
    async def _check_pending_payments(self):
        """Проверка всех pending платежей"""
        try:
            db = await get_db()
            payment_repo = PaymentRepository(db)
            
            # Получаем все pending платежи, которые были созданы не более 24 часов назад
            # (старые платежи уже не актуальны)
            day_ago = datetime.utcnow() - timedelta(hours=24)
            pending_payments = await payment_repo.get_pending_since(day_ago)
            
            if not pending_payments:
                return
            
            logger.info(f"Checking {len(pending_payments)} pending payments")
            
            for payment in pending_payments:
                # Пропускаем платежи без payment_id (еще не созданы в YooKassa)
                if not payment.get('payment_id'):
                    continue
                
                # Проверяем статус в YooKassa
                payment_status = self.yookassa.get_payment_status(payment['payment_id'])
                
                if not payment_status:
                    logger.warning(f"Failed to get status for payment {payment['payment_id']}")
                    continue
                
                # Если статус изменился
                if payment_status['status'] != payment['status']:
                    logger.info(
                        f"Payment {payment['payment_id']} status changed: "
                        f"{payment['status']} -> {payment_status['status']}"
                    )
                    
                    # Обновляем статус в БД
                    update_data = {"status": payment_status['status']}
                    
                    # Если платеж успешен
                    if payment_status['status'] == 'succeeded':
                        update_data["paid_at"] = datetime.utcnow()
                        
                        # Обновляем платеж
                        await payment_repo.update_by_payment_id(
                            payment['payment_id'],
                            update_data
                        )
                        
                        # Получаем обновленный платеж как dict
                        updated_payment_data = await self._get_payment_dict(payment_repo, payment['payment_id'])
                        
                        if updated_payment_data:
                            # Отправляем уведомления
                            await notify_user_payment_success(self.bot, updated_payment_data, db)
                            await notify_admin_new_payment(self.bot, updated_payment_data, db)
                        
                        logger.info(f"Payment {payment['payment_id']} processed successfully")
                    
                    # Если платеж отменен или не прошел
                    elif payment_status['status'] in ['canceled', 'failed']:
                        await payment_repo.update_by_payment_id(
                            payment['payment_id'],
                            update_data
                        )
                        logger.info(f"Payment {payment['payment_id']} marked as {payment_status['status']}")
        
        except Exception as e:
            logger.error(f"Error checking pending payments: {e}", exc_info=True)
    
    async def _get_payment_dict(self, payment_repo, payment_id: str) -> dict:
        """Получение платежа как dict"""
        try:
            # Получаем из коллекции напрямую как dict
            from database import get_db
            db = await get_db()
            payment_data = await db.payments.find_one({"payment_id": payment_id})
            return payment_data
        except Exception as e:
            logger.error(f"Error getting payment dict: {e}")
            return None


# Глобальный экземпляр
_payment_checker: PaymentChecker = None


async def start_payment_checker(bot: Bot, check_interval: int = 60):
    """
    Запуск проверки платежей
    
    Args:
        bot: Экземпляр бота
        check_interval: Интервал проверки в секундах
    """
    global _payment_checker
    
    if _payment_checker is None:
        _payment_checker = PaymentChecker(bot, check_interval)
    
    await _payment_checker.start()
    return _payment_checker


async def stop_payment_checker():
    """Остановка проверки платежей"""
    global _payment_checker
    
    if _payment_checker:
        await _payment_checker.stop()

