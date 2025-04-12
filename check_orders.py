import requests
import json
import os
from datetime import datetime

# ============ Настройки ============
API_KEY = "reYvVnW1aGXS6v6ZuhPpZUDJFH4aISmGU5bHj3URhYbMMhe9hb9dxwvJ2QquEn0THDvWOedG3nIS8S7XYx2KoR"
ORDERS_FILE = os.path.join(os.path.dirname(__file__), "orders.json")


# ============ Работа с файлом ============
def load_orders():
    """Загружает ордера из файла"""
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_orders(orders):
    """Сохраняет ордера в файл"""
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)


# ============ Работа с API ============
def cancel_order(order_id):
    """Отменяет ордер через API"""
    url = f"https://api.ataix.kz/api/orders/{order_id}"
    headers = {"X-API-Key": API_KEY, "accept": "application/json"}
    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("status", False)
        print(f"Ошибка отмены ордера {order_id}: HTTP {response.status_code}")
        return False
    except Exception as e:
        print(f"Ошибка отмены ордера {order_id}: {str(e)}")
        return False

def create_order(symbol, price, quantity):
    """Создаёт новый ордер с наценкой +1%"""
    url = "https://api.ataix.kz/api/orders"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    new_price = round(price * 1.01, 2)
    payload = {
        "symbol": symbol,
        "side": "buy",
        "type": "limit",
        "quantity": quantity,
        "price": new_price,
        "subType": "gtc"
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            if data.get("status"):
                return data["result"]["id"], new_price
        print(f"Ошибка создания ордера: HTTP {response.status_code}")
        return None, None
    except Exception as e:
        print(f"Ошибка создания ордера: {str(e)}")
        return None, None


# ============ Обработка ордеров ============
def update_order_status():
    """Обновляет статусы и пересоздаёт ордера при необходимости"""
    orders = load_orders()
    updated = False

    for order in orders[:]:  # Копия списка
        order_id = order.get("id")
        current_status = order.get("status", "").upper()

        if current_status in ["CANCELLED", "FILLED"]:
            continue

        # Если ордер NEW — отменяем и создаём новый
        if current_status == "NEW":
            print(f"Обработка ордера {order_id} (статус NEW)")
            if cancel_order(order_id):
                new_order_id, new_price = create_order(
                    order["symbol"],
                    float(order["price"]),
                    float(order["quantity"])
                )
                if new_order_id:
                    # Обновляем старый
                    order["status"] = "CANCELLED"
                    order["updated_at"] = datetime.now().isoformat()

                    # Добавляем новый
                    orders.append({
                        "id": new_order_id,
                        "symbol": order["symbol"],
                        "side": "buy",
                        "price": new_price,
                        "quantity": order["quantity"],
                        "status": "NEW",
                        "created_at": datetime.now().isoformat(),
                        "parent_order": order_id
                    })
                    print(f"Отменён ордер {order_id}, создан новый {new_order_id} по цене {new_price}")
                    updated = True
                else:
                    print(f"Не удалось создать новый ордер после отмены {order_id}")

    if updated:
        save_orders(orders)
        print("Файл orders.json обновлён")
    else:
        print("Изменений не требуется")


# ============ Отладка ============
def debug_info():
    """Выводит текущие ордера и проверяет доступ к API"""
    orders = load_orders()
    print("\n[DEBUG] Текущие ордера:")
    for order in orders:
        print(f"ID: {order.get('id')}, Status: {order.get('status')}, Price: {order.get('price')}")

    # Проверка API-доступа
    test_url = "https://api.ataix.kz/api/account/balances"
    headers = {"X-API-Key": API_KEY}
    try:
        response = requests.get(test_url, headers=headers)
        print(f"\n[DEBUG] API доступен. HTTP статус: {response.status_code}")
    except Exception as e:
        print(f"\n[DEBUG] Ошибка доступа к API: {str(e)}")


# ============ Точка входа ============
if __name__ == "__main__":
    print("=" * 50)
    print("НАЧАЛО ОБРАБОТКИ ОРДЕРОВ")
    print("=" * 50)

    debug_info()
    update_order_status()

    print("=" * 50)
    print("ЗАВЕРШЕНО")
    print("=" * 50)
