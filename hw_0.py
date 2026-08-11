
import pandas as pd
import requests
import time
import matplotlib.pyplot as plt

# Подготовка датасета 
# Ниже представлен код, которым я сделал первоначальную выборку из исходного реестра ФНС.
# Для ускорения работы скрипта результат сохранил в файл sample_50.csv.

# df = pd.read_excel("Реестр (1).xlsx", skiprows=2)
# df_clean = df[
#    (df['Тип субъекта'] == 'Юридическое лицо') &
#    (df['Категория'].isin(['Малое предприятие', 'Среднее предприятие'])) &
#    (df['Основной вид деятельности'].str.contains('41.20', na=False))
# ].copy()
# df_sample = df_clean.sample(n=50, random_state=42)
# df_sample.to_csv("sample_50.csv", index=False)

df_sample = pd.read_csv("sample_50.csv")

# Парсинг финансовых данных
financial_data = []
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*"
})

print("Начинаем сбор финансовой отчетности...")

for index, row in df_sample.iterrows():
    inn = str(row['ИНН'])
    try:
        url_search = f"https://bo.nalog.gov.ru/advanced-search/organizations/search?query={inn}&page=0"
        res_search = session.get(url_search).json()
        
        if not res_search.get("content"):
            continue
            
        org_id = res_search["content"][0]["id"]
        
        url_bfo = f"https://bo.nalog.gov.ru/nbo/organizations/{org_id}/bfo/"
        res_bfo = session.get(url_bfo).json()
        
        for report in res_bfo:
            year = report.get('period')
            try:
                fin_result = report['typeCorrections'][0]['correction']['financialResult']
                net_profit = fin_result.get('current2400', 0)
                ebita = fin_result.get('current2200', 0)
                revenue = fin_result.get('current2110', 0)
                
                financial_data.append({
                    'ИНН': inn,
                    'Год': int(year),
                    'Чистая_прибыль': net_profit,
                    'EBITA': ebita,
                    'Выручка': revenue
                })
            except (KeyError, IndexError):
                pass
    except Exception as e:
        pass 
        
    time.sleep(0.5) 

df_fin = pd.DataFrame(financial_data)

#Расчет метрик и визуализация
YEAR_CURRENT = 2024
YEAR_PAST = 2023

pivot_profit = df_fin.pivot(index='ИНН', columns='Год', values='Чистая_прибыль').dropna(subset=[YEAR_CURRENT, YEAR_PAST])

pivot_profit['Рост_%'] = ((pivot_profit[YEAR_CURRENT] - pivot_profit[YEAR_PAST]) / (pivot_profit[YEAR_PAST].abs() + 1)) * 100
pivot_profit['Рост_%'] = pivot_profit['Рост_%'].round().astype(int)
pivot_profit = pivot_profit[(pivot_profit['Рост_%'] > -1000) & (pivot_profit['Рост_%'] < 1000)]

plt.figure(figsize=(10, 6))
plt.hist(pivot_profit['Рост_%'], bins=20, color='skyblue', edgecolor='black')
plt.title(f'Распределение роста чистой прибыли строительных компаний ({YEAR_CURRENT} vs {YEAR_PAST})')
plt.xlabel('Процент роста чистой прибыли (%)')
plt.ylabel('Количество компаний')
plt.grid(axis='y', alpha=0.75)
plt.axvline(x=0, color='red', linestyle='--', label='Нулевой рост')
plt.legend()
plt.show()

print("""
=== Вывод по анализу рынка строительства (ОКВЭД 41.20) ===
Отрасль показывает неоднородную динамику:
1. Основная масса компаний находится в зоне стагнации или умеренного изменения прибыли (около 0%).
2. Наблюдается заметное количество компаний с существенным ростом прибыли (от +100% до +400% и выше), что говорит о наличии высокомаржинальных и быстрорастущих ниш.
3. Компаний с сильным падением прибыли значительно меньше, чем растущих.
Итог: Отрасль перспективна, однако требует тщательного выбора конкретных проектов, так как успех распределен неравномерно.
""")

# Географический анализ
df_2024 = df_fin[df_fin['Год'] == YEAR_CURRENT]

df_2024['ИНН'] = df_2024['ИНН'].astype(str)
df_sample['ИНН'] = df_sample['ИНН'].astype(str)

if not df_2024.empty:
    df_merged = df_2024.merge(df_sample[['ИНН', 'Регион']], on='ИНН', how='inner')
    region_revenue = df_merged.groupby('Регион')['Выручка'].sum().reset_index()
    top_regions = region_revenue.sort_values(by='Выручка', ascending=False).head(10).sort_values(by='Выручка', ascending=True)
    
    plt.figure(figsize=(12, 7))
    plt.barh(top_regions['Регион'], top_regions['Выручка'], color='coral', edgecolor='black')
    plt.title(f'Топ регионов по выручке строительных компаний ({YEAR_CURRENT} год)')
    plt.xlabel('Суммарная выручка (тыс. руб.)')
    plt.ylabel('Регион')
    plt.grid(axis='x', alpha=0.75)
    plt.tight_layout()
    plt.show()
else:
    print("Нет данных за 2024 год для построения графика по регионам.")
