# Исправление ошибки типов данных в пересчёте веса еды

## Проблема
Ошибка `unsupported operand type(s) for /: 'float' and 'decimal.Decimal'` при попытке изменить вес еды.

## Причина
В базе данных поля `estimated_weight_g`, `protein_g`, `fat_g`, `carbs_g` имеют тип `Numeric` (Decimal), а `calories` - `Integer`. Код пытался выполнить математические операции между `float` и `Decimal` без явного преобразования типов.

## Решение
Добавлено явное преобразование типов данных перед математическими операциями.

## Изменения

### 1. Обновлён метод `update_food_log` в `health_service.py`
```python
# Было:
old_weight = food_log.estimated_weight_g
updates['calories'] = round(food_log.calories * ratio, 1)

# Стало:
old_weight = float(food_log.estimated_weight_g)
updates['calories'] = int(round(float(food_log.calories) * ratio))
updates['protein_g'] = round(float(food_log.protein_g) * ratio, 2)
```

### 2. Обновлён метод `recalculate_food_nutrition`
```python
# Было:
old_weight = food_log.estimated_weight_g
updates['calories'] = round(food_log.calories * ratio, 1)

# Стало:
old_weight = float(food_log.estimated_weight_g)
updates['calories'] = int(round(float(food_log.calories) * ratio))
updates['protein_g'] = round(float(food_log.protein_g) * ratio, 2)
```

### 3. Обновлён обработчик `_handle_food_edit_input` в `telegram_service.py`
```python
# Было:
• Вес: {new_value}г (было {current_food_log.estimated_weight_g}г)

# Стало:
• Вес: {new_value}г (было {float(current_food_log.estimated_weight_g)}г)
• Калории: {int(updated_food_log.calories)} ккал (было {int(current_food_log.calories)} ккал)
```

## Типы данных в модели FoodLog
- `estimated_weight_g`: `Numeric(7, 2)` → `Decimal`
- `calories`: `Integer` → `int`
- `protein_g`: `Numeric(6, 2)` → `Decimal`
- `fat_g`: `Numeric(6, 2)` → `Decimal`
- `carbs_g`: `Numeric(6, 2)` → `Decimal`

## Результат
✅ **Исправлена ошибка типов**: Все математические операции теперь выполняются с правильными типами данных
✅ **Сохранена точность**: Decimal значения корректно преобразуются в float для вычислений
✅ **Правильное отображение**: Значения корректно отображаются в сообщениях пользователю

## Тестирование
Теперь изменение веса еды должно работать без ошибок и корректно пересчитывать все питательные значения. 