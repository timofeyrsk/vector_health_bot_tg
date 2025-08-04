# Обновление: Пересчёт КБЖУ при изменении веса еды

## Проблема
При изменении веса еды в функции "Изменить приём пищи" калории и БЖУ (белки, жиры, углеводы) не пересчитывались пропорционально новому весу.

## Решение
Добавлена автоматическая пересчётка питательной ценности при изменении веса еды.

## Изменения

### 1. Обновлён метод `update_food_log` в `health_service.py`
- **Добавлена логика пересчёта**: При изменении `estimated_weight_g` автоматически пересчитываются все питательные значения
- **Пропорциональный расчёт**: Новые значения = старые значения × (новый вес / старый вес)
- **Логирование**: Добавлено логирование процесса пересчёта

```python
# Check if weight is being updated and we need to recalculate nutrition
if 'estimated_weight_g' in updates and food_log.estimated_weight_g:
    old_weight = food_log.estimated_weight_g
    new_weight = updates['estimated_weight_g']
    
    # Calculate ratio for proportional recalculation
    if old_weight > 0:
        ratio = new_weight / old_weight
        
        # Recalculate nutrition values proportionally
        updates['calories'] = round(food_log.calories * ratio, 1)
        updates['protein_g'] = round(food_log.protein_g * ratio, 1)
        updates['fat_g'] = round(food_log.fat_g * ratio, 1)
        updates['carbs_g'] = round(food_log.carbs_g * ratio, 1)
```

### 2. Добавлен метод `recalculate_food_nutrition`
- **Отдельный метод**: Для случаев, когда нужен только пересчёт без других обновлений
- **Безопасность**: Проверка существования записи и валидности веса

### 3. Обновлён обработчик `_handle_food_edit_input` в `telegram_service.py`
- **Улучшенное сообщение**: При изменении веса показывается сравнение старых и новых значений
- **Информативность**: Пользователь видит, что произошёл пересчёт

```python
if field == 'estimated_weight_g':
    message = f"""✅ *Вес успешно обновлен!*

📊 *Новые значения:*
• Вес: {new_value}г (было {current_food_log.estimated_weight_g}г)
• Калории: {updated_food_log.calories} ккал (было {current_food_log.calories} ккал)
• Белки: {updated_food_log.protein_g}г (было {current_food_log.protein_g}г)
• Жиры: {updated_food_log.fat_g}г (было {current_food_log.fat_g}г)
• Углеводы: {updated_food_log.carbs_g}г (было {current_food_log.carbs_g}г)

🔄 *Значения пересчитаны пропорционально новому весу*"""
```

## Пример работы

### До изменений:
- Вес: 250г
- Калории: 400 ккал
- Белки: 15г
- Жиры: 20г
- Углеводы: 30г

### После изменения веса на 350г:
- Вес: 350г (+40%)
- Калории: 560 ккал (+40%)
- Белки: 21г (+40%)
- Жиры: 28г (+40%)
- Углеводы: 42г (+40%)

## Результат
✅ **Автоматический пересчёт**: При изменении веса еды все питательные значения пересчитываются пропорционально
✅ **Информативность**: Пользователь видит старые и новые значения
✅ **Точность**: Сохранение пропорций питательной ценности
✅ **Логирование**: Отслеживание процесса пересчёта в логах

## Тестирование
Теперь при изменении веса еды через "Изменить приём пищи" → "Изменить" → "Вес (г)" все значения КБЖУ будут автоматически пересчитаны и показаны пользователю. 