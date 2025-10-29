import uuid
import logging
from typing import Optional, Dict, Any
from yookassa import Configuration, Payment, Webhook
from yookassa.domain.notification import WebhookNotificationFactory
from config import config

logger = logging.getLogger(__name__)


class YooKassaPayment:
    """Класс для работы с ЮKassa API"""
    
    def __init__(self):
        """Инициализация YooKassa с настройками из конфига"""
        Configuration.account_id = config.YOOKASSA_SHOP_ID
        Configuration.secret_key = config.YOOKASSA_SECRET_KEY
        
        if not config.YOOKASSA_SHOP_ID or not config.YOOKASSA_SECRET_KEY:
            logger.error("YooKassa credentials not configured!")
            raise ValueError("YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY must be set in .env file")
        
        logger.info(f"YooKassa initialized with Shop ID: {config.YOOKASSA_SHOP_ID}")
    
    def create_payment(
        self, 
        amount: float, 
        description: str, 
        return_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        customer_email: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Создание платежа в YooKassa
        
        Args:
            amount: Сумма платежа в рублях
            description: Описание платежа
            return_url: URL для возврата после оплаты
            metadata: Дополнительные метаданные для платежа
            customer_email: Email покупателя для чека
            
        Returns:
            dict: Данные созданного платежа или None при ошибке
        """
        idempotence_key = str(uuid.uuid4())
        
        payment_metadata = {"order_id": idempotence_key}
        if metadata:
            payment_metadata.update(metadata)
        
        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or "https://t.me/your_bot"
            },
            "capture": True,
            "description": description,
            "metadata": payment_metadata,
            # Не указываем payment_method_data - ЮKassa покажет все доступные методы:
            # банковские карты, СБП (SberPay), ЮMoney, Google Pay, Apple Pay и др.
            "receipt": {
                "customer": {
                    "email": customer_email or config.RECEIPT_EMAIL
                },
                "items": [
                    {
                        "description": description[:128],  # Максимум 128 символов
                        "quantity": "1.00",
                        "amount": {
                            "value": f"{amount:.2f}",
                            "currency": "RUB"
                        },
                        "vat_code": 1,  # НДС не облагается
                        "payment_mode": "full_payment",
                        "payment_subject": "service"
                    }
                ]
            }
        }
        
        try:
            logger.info(f"Creating payment: amount={amount}, description={description}, email={customer_email or config.RECEIPT_EMAIL}")
            payment = Payment.create(payment_data, idempotence_key)
            
            result = {
                'id': payment.id,
                'status': payment.status,
                'confirmation_url': payment.confirmation.confirmation_url,
                'amount': float(payment.amount.value),
                'currency': payment.amount.currency
            }
            
            logger.info(f"Payment created successfully: {payment.id}, receipt will be sent to: {customer_email or config.RECEIPT_EMAIL}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating payment: {e}", exc_info=True)
            return None
    
    def get_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение статуса платежа из YooKassa
        
        Args:
            payment_id: ID платежа в ЮKassa
            
        Returns:
            dict: Статус платежа или None при ошибке
        """
        try:
            logger.info(f"Getting payment status for: {payment_id}")
            payment = Payment.find_one(payment_id)
            
            result = {
                'id': payment.id,
                'status': payment.status,
                'paid': payment.paid,
                'amount': float(payment.amount.value),
                'currency': payment.amount.currency,
                'metadata': payment.metadata if hasattr(payment, 'metadata') else {}
            }
            
            logger.info(f"Payment status retrieved: {payment_id} - {payment.status}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting payment status for {payment_id}: {e}", exc_info=True)
            return None
    
    def cancel_payment(self, payment_id: str) -> bool:
        """
        Отмена платежа в YooKassa
        
        Args:
            payment_id: ID платежа в ЮKassa
            
        Returns:
            bool: Успешность отмены
        """
        try:
            logger.info(f"Canceling payment: {payment_id}")
            Payment.cancel(payment_id)
            logger.info(f"Payment canceled successfully: {payment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error canceling payment {payment_id}: {e}", exc_info=True)
            return False
    
    @staticmethod
    def parse_webhook_notification(request_body: Dict[str, Any]) -> Optional[Any]:
        """
        Парсинг уведомления от YooKassa webhook
        
        Args:
            request_body: JSON тело запроса от YooKassa
            
        Returns:
            Объект уведомления или None при ошибке
        """
        try:
            logger.info("Parsing webhook notification")
            notification = WebhookNotificationFactory().create(request_body)
            logger.info(f"Webhook notification parsed: type={notification.event}, payment_id={notification.object.id}")
            return notification
            
        except Exception as e:
            logger.error(f"Error parsing webhook notification: {e}", exc_info=True)
            return None
    
    def setup_webhook(self, webhook_url: str) -> bool:
        """
        Настройка webhook для получения уведомлений от YooKassa
        
        Args:
            webhook_url: URL для получения уведомлений
            
        Returns:
            bool: Успешность настройки
        """
        try:
            logger.info(f"Setting up webhook: {webhook_url}")
            
            # Получаем список существующих вебхуков
            webhooks = Webhook.list()
            
            # Удаляем старые вебхуки, если есть
            for webhook in webhooks.items:
                if webhook.url == webhook_url:
                    logger.info(f"Webhook already exists: {webhook_url}")
                    return True
            
            # Создаем новый вебхук
            Webhook.add({
                "event": "payment.succeeded",
                "url": webhook_url
            })
            
            logger.info(f"Webhook created successfully: {webhook_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up webhook: {e}", exc_info=True)
            return False

