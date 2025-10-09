import uuid
from yookassa import Configuration, Payment
from config import config


class YooKassaPayment:
    """Класс для работы с ЮKassa API"""
    
    def __init__(self):
        Configuration.account_id = config.YOOKASSA_SHOP_ID
        Configuration.secret_key = config.YOOKASSA_SECRET_KEY
    
    def create_payment(self, amount: float, description: str, return_url: str = None) -> dict:
        """
        Создание платежа
        
        Args:
            amount: Сумма платежа
            description: Описание платежа
            return_url: URL для возврата после оплаты
            
        Returns:
            dict: Данные созданного платежа
        """
        idempotence_key = str(uuid.uuid4())
        
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
            "metadata": {
                "order_id": idempotence_key
            }
        }
        
        try:
            payment = Payment.create(payment_data, idempotence_key)
            return {
                'id': payment.id,
                'status': payment.status,
                'confirmation_url': payment.confirmation.confirmation_url,
                'amount': float(payment.amount.value),
                'currency': payment.amount.currency
            }
        except Exception as e:
            print(f"Error creating payment: {e}")
            return None
    
    def get_payment_status(self, payment_id: str) -> dict:
        """
        Получение статуса платежа
        
        Args:
            payment_id: ID платежа в ЮKassa
            
        Returns:
            dict: Статус платежа
        """
        try:
            payment = Payment.find_one(payment_id)
            return {
                'id': payment.id,
                'status': payment.status,
                'paid': payment.paid,
                'amount': float(payment.amount.value),
                'currency': payment.amount.currency
            }
        except Exception as e:
            print(f"Error getting payment status: {e}")
            return None
    
    def cancel_payment(self, payment_id: str) -> bool:
        """
        Отмена платежа
        
        Args:
            payment_id: ID платежа в ЮKassa
            
        Returns:
            bool: Успешность отмены
        """
        try:
            Payment.cancel(payment_id)
            return True
        except Exception as e:
            print(f"Error canceling payment: {e}")
            return False

