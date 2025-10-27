"""
Сервис для работы с платежами подписок через YooKassa
"""
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from yookassa import Configuration, Payment

from config import config

logger = logging.getLogger(__name__)


class SubscriptionPaymentService:
    """Сервис для работы с платежами подписок через YooKassa"""
    
    def __init__(self):
        """Инициализация сервиса"""
        # Настройка YooKassa
        Configuration.account_id = config.YOOKASSA_SHOP_ID
        Configuration.secret_key = config.YOOKASSA_SECRET_KEY
        
        self.price = config.SUBSCRIPTION_PRICE
        self.currency = config.SUBSCRIPTION_CURRENCY
        self.days = config.SUBSCRIPTION_DAYS
        
        logger.info(f"SubscriptionPaymentService initialized: {self.price} {self.currency} for {self.days} days")
    
    def create_payment(self, user_id: int, return_url: str = None, customer_email: str = None) -> Dict[str, Any]:
        """
        Создание платежа для подписки на канал
        
        Args:
            user_id: Telegram ID пользователя
            return_url: URL для возврата после оплаты
            customer_email: Email покупателя для чека
            
        Returns:
            Dict с информацией о платеже
        """
        try:
            # Генерируем уникальный ключ идемпотентности
            idempotence_key = str(uuid.uuid4())
            
            # URL возврата по умолчанию
            if not return_url:
                return_url = "https://t.me/your_bot"
            
            # Формируем данные платежа
            payment_data = {
                "amount": {
                    "value": f"{self.price:.2f}",
                    "currency": self.currency
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url
                },
                "capture": True,
                "description": f"Подписка на канал на {self.days} дней",
                "metadata": {
                    "user_id": str(user_id),
                    "product_type": "channel_subscription"
                },
                "receipt": {
                    "customer": {
                        "email": customer_email or config.RECEIPT_EMAIL
                    },
                    "items": [
                        {
                            "description": f"Подписка на канал на {self.days} дней",
                            "quantity": "1.00",
                            "amount": {
                                "value": f"{self.price:.2f}",
                                "currency": self.currency
                            },
                            "vat_code": 1,  # НДС не облагается
                            "payment_mode": "full_payment",
                            "payment_subject": "service"
                        }
                    ]
                }
            }
            
            # Создаем платеж
            payment = Payment.create(payment_data, idempotence_key)
            
            logger.info(f"Payment created: {payment.id} for user {user_id}, email: {customer_email or config.RECEIPT_EMAIL}")
            
            return {
                "payment_id": payment.id,
                "confirmation_url": payment.confirmation.confirmation_url,
                "status": payment.status,
                "amount": float(payment.amount.value),
                "currency": payment.amount.currency
            }
            
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise
    
    def check_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Проверка статуса платежа
        
        Args:
            payment_id: ID платежа в YooKassa
            
        Returns:
            Dict с информацией о статусе платежа
        """
        try:
            payment = Payment.find_one(payment_id)
            
            return {
                "payment_id": payment.id,
                "status": payment.status,
                "paid": payment.paid,
                "amount": float(payment.amount.value),
                "currency": payment.amount.currency,
                "created_at": payment.created_at,
                "captured_at": getattr(payment, 'captured_at', None)
            }
            
        except Exception as e:
            logger.error(f"Error checking payment {payment_id}: {e}")
            raise
    
    def get_payment_status_message(self, status: str, paid: bool) -> str:
        """
        Получить сообщение о статусе платежа для пользователя
        
        Args:
            status: Статус платежа из YooKassa
            paid: Оплачен ли платеж
            
        Returns:
            Текст сообщения для пользователя
        """
        if status == "succeeded" and paid:
            return "✅ Оплата успешно завершена!"
        
        elif status == "pending":
            return """⏳ Платеж еще не завершен

💡 Возможные причины:
• Вы не завершили оплату на странице YooKassa
• Платеж находится в обработке

📌 Что делать:
1. Завершите оплату, если не сделали этого
2. Подождите 1-2 минуты
3. Нажмите 'Проверить оплату' снова"""
        
        elif status == "waiting_for_capture":
            return """⏳ Платеж в обработке

Пожалуйста, подождите несколько минут и нажмите 'Проверить оплату' снова."""
        
        elif status == "canceled":
            return """❌ Платеж отменен

Вы можете создать новый платеж, нажав кнопку 'Купить доступ'."""
        
        else:
            return f"ℹ️ Статус платежа: {status}"

