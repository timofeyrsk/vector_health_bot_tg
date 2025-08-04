# Исправление логики отчётов

## Проблема
В недельных и месячных отчётах ИИ давал неправильные рекомендации по калориям:
- **Недельный отчёт**: рекомендовал 4147 ккал в день (слишком много)
- **Месячный отчёт**: рекомендовал 504 ккал в день (слишком мало)

## Причина
ИИ самостоятельно пересчитывал среднюю дневную норму, игнорируя точные данные из системы.

## Решение

### 1. Добавлены точные расчёты в `health_service.py`

#### Новые поля для рекомендаций:
```python
# Calculate remaining targets for recommendations
remaining_calories = max(0, period_calorie_target - total_calories)
remaining_protein = max(0, period_protein_target - total_protein)
remaining_fat = max(0, period_fat_target - total_fat)
remaining_carbs = max(0, period_carbs_target - total_carbs)

# Calculate average daily targets for remaining days
avg_daily_calories_remaining = remaining_calories / remaining_days if remaining_days > 0 else 0
avg_daily_protein_remaining = remaining_protein / remaining_days if remaining_days > 0 else 0
avg_daily_fat_remaining = remaining_fat / remaining_days if remaining_days > 0 else 0
avg_daily_carbs_remaining = remaining_carbs / remaining_days if remaining_days > 0 else 0
```

#### Дополнительные поля в возвращаемых данных:
- `remaining_calories`, `remaining_protein`, `remaining_fat`, `remaining_carbs`
- `avg_daily_calories_remaining`, `avg_daily_protein_remaining`, `avg_daily_fat_remaining`, `avg_daily_carbs_remaining`

### 2. Обновлён промпт в `openai_service.py`

#### Добавлены точные значения в промпт:
```
Осталось до цели:
- Калории: {remaining_calories}
- Белки: {remaining_protein}г
- Жиры: {remaining_fat}г
- Углеводы: {remaining_carbs}г

Средняя дневная норма на оставшиеся дни:
- Калории: {avg_daily_calories_remaining:.0f}
- Белки: {avg_daily_protein_remaining:.1f}г
- Жиры: {avg_daily_fat_remaining:.1f}г
- Углеводы: {avg_daily_carbs_remaining:.1f}г
```

#### Обновлены рекомендации:
```
💡 РЕКОМЕНДАЦИИ НА ОСТАВШИЕСЯ ДНИ
• Средняя дневная норма калорий: {avg_daily_calories_remaining:.0f} ккал
• Белки: {avg_daily_protein_remaining:.1f}г, Жиры: {avg_daily_fat_remaining:.1f}г, Углеводы: {avg_daily_carbs_remaining:.1f}г
```

#### Добавлено важное указание:
```
ВАЖНО: Используй точные значения средней дневной нормы, которые уже рассчитаны! Не пересчитывай их самостоятельно.
```

## Примеры правильных расчётов

### Недельный отчёт (если сегодня понедельник):
- **Период**: 1 день
- **Осталось дней**: 6
- **Цель за неделю**: 532 × 7 = 3724 ккал
- **Потреблено**: 1256 ккал
- **Осталось**: 3724 - 1256 = 2468 ккал
- **Средняя дневная норма**: 2468 ÷ 6 = **412 ккал** (вместо 4147!)

### Месячный отчёт (если сегодня 4-е число):
- **Период**: 4 дня
- **Осталось дней**: 24
- **Цель за месяц**: 532 × 28 = 14896 ккал
- **Потреблено**: 1256 ккал
- **Осталось**: 14896 - 1256 = 13640 ккал
- **Средняя дневная норма**: 13640 ÷ 24 = **568 ккал** (вместо 504!)

## Результат

✅ **Точные расчёты**: Система теперь предоставляет ИИ точные значения
✅ **Правильные рекомендации**: ИИ использует готовые расчёты вместо собственных
✅ **Логичная логика**: Рекомендации соответствуют реальным потребностям
✅ **Масштабируемость**: Логика работает для любого количества дней в периоде

## Тестирование

Теперь отчёты должны показывать:
- **Недельный**: ~412 ккал в день (вместо 4147)
- **Месячный**: ~568 ккал в день (вместо 504)

Рекомендации станут реалистичными и выполнимыми для пользователей. 