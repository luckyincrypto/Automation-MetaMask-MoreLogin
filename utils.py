

def calculate_percentage(number: float, percent: float) -> float:
    try:
        return round((number * percent) / 100, 4)  # Округляем до двух знаков после запятой
    except Exception as e:
        print(f"Ошибка: {e}")
        return 0.0


