import os
import json
from groq import Groq

# В проде сюда приходит текст от Whisper/другого STT после обработки звонка.
# Для демо берём готовую расшифровку одного звонка отдела продаж.
TRANSCRIPT = """
Менеджер: Добрый день! CityCar, меня зовут Ирина. Вы оставляли заявку на аренду авто.
Клиент: Да, интересует кроссовер на выходные, но смущает цена за доп. страховку.
Менеджер: Понимаю. Могу предложить тариф без франшизы за дополнительные 800 руб/сутки.
Клиент: Хорошо, но мне нужно согласовать с женой, перезвоните завтра вечером.
Менеджер: Договорились, перезвоню завтра после 18:00. Хорошего дня!
"""

client = Groq(api_key=os.environ["GROQ_API_KEY"])

PROMPT = f"""Проанализируй расшифровку звонка менеджера отдела продаж.
Верни строго JSON без пояснений, со следующими полями:
- topic: тема обращения клиента
- objections: список возражений клиента
- agreed_next_step: что и когда следующим шагом должен сделать менеджер
- sentiment: тональность клиента (positive/neutral/negative)
- risk_flag: true/false — есть ли риск потери сделки (например, нет чёткой договорённости)

Расшифровка звонка:
{TRANSCRIPT}
"""

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    max_tokens=500,
    response_format={"type": "json_object"},
    messages=[{"role": "user", "content": PROMPT}],
)

raw = response.choices[0].message.content
print("RAW MODEL OUTPUT:\n", raw)

try:
    insight = json.loads(raw)
    print("\nPARSED:\n", json.dumps(insight, ensure_ascii=False, indent=2))
except json.JSONDecodeError:
    print("\n(модель вернула не чистый JSON — в проде тут нужен retry/strict JSON mode)")
