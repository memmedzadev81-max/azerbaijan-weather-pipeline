# Pipeline-a bələdçi (Azərbaycanca)

## 1. Layihə nə edir? (sadə dildə)

Hər gün 5 şəhərin (Bakı, Gəncə, Sumqayıt, Lənkəran, Şəki) saatlıq hava məlumatını internetdən (Open-Meteo API) çəkir, təmizləyir və Power BI üçün hazır cədvəllərə çevirir.

Bu, data engineer-in əsas işinin kiçik bir modelidir:
**məlumatı mənbədən götür → təmizlə → hesabat üçün hazırla → yoxla → avtomatik işlət.**

## 2. Kompüterdə necə işə salmaq olar (Windows)

PowerShell-i açın və layihə qovluğuna keçin (öz ünvanınızı yazın):

```
cd "C:\Users\memme\Downloads\azerbaijan-weather-pipeline"
```

Lazımi paketləri quraşdırın (bir dəfə):

```
pip install -r requirements.txt
```

**İnternetsiz demo** (test məlumatı ilə):

```
python run_pipeline.py --sample
```

**Real məlumatla** (internet lazımdır):

```
python run_pipeline.py
```

**Testləri işə salmaq:**

```
python -m unittest -v
```

Nəticə `data` qovluğunda yaranır:
- `data\bronze\` — API-dən gələn xam JSON faylları
- `data\warehouse.db` — bütün cədvəllərin olduğu baza
- `data\gold_csv\` — Power BI üçün 3 CSV faylı

⚠️ Əgər həm `--sample`, həm də real rejimi sınamaq istəsəniz, aralarında `data` qovluğunu silin. Yoxsa test məlumatı ilə real məlumat qarışar.

## 3. Hər hissə nə edir? (müsahibə üçün mütləq bilin)

| Hissə | Fayl | Nə edir |
|---|---|---|
| **Extract** | `pipeline/extract.py` | API-yə sorğu göndərir. Xəta olsa, 3 dəfə yenidən cəhd edir (2 s, sonra 4 s gözləyərək). |
| **Bronze** | `data/bronze/` | API cavabını **dəyişmədən** saxlayır. Sonra kodda səhv tapılsa, API-yə yenidən müraciət etmədən hər şeyi bərpa etmək olar. |
| **Silver** | `pipeline/transform.py` | Təmizləmə: sütun adlarını dəyişir, tipləri düzəldir, mümkün olmayan dəyərləri (məs. 999 °C) NULL edir, boş sətirləri və dublikatları silir. |
| **Gold** | `pipeline/load_gold.py`, `sql/` | **Star schema** qurur: `dim_city`, `dim_date` (ölçü cədvəlləri) və `fact_weather_daily` (fakt cədvəli, gündəlik orta/min/max temperatur, yağış və s.). |
| **Data quality** | `pipeline/quality.py` | 11 yoxlama aparır. Biri belə uğursuz olsa, bütün yükləmə geri qaytarılır (rollback). |
| **Incremental load** | `pipeline/state.py` | Hər şəhər üçün "sonuncu yüklənən tarix" (watermark) saxlanır. Növbəti dəfə yalnız yeni günlər çəkilir. |
| **Orkestrasiya** | `dags/weather_pipeline_dag.py` | Airflow hər gün saat 06:00-da pipeline-ı avtomatik işə salır. |
| **Testlər** | `tests/test_pipeline.py` | 10 avtomatik test: təmizləmə qaydaları, təkrar işə salmada dublikat olmaması, xətada geri qaytarma və s. |

### Müsahibədə tez-tez soruşulan anlayışlar
- **Idempotent** — pipeline-ı 2 dəfə işə salsan da nəticə eyni qalır, dublikat yaranmır. (`ON CONFLICT DO UPDATE` və "əvvəl sil, sonra yenidən hesabla" ilə.)
- **Transaction / rollback** — silver, gold, yoxlamalar və watermark bir bütöv kimi yazılır: ya hamısı, ya heç biri.
- **Backfill** — keçmiş bir dövrü yenidən yükləmək: `python run_pipeline.py --start 2026-09-01 --end 2026-09-30`
- **Lineage** — silver-dəki hər sətirdə onun hansı bronze faylından gəldiyi yazılıb (`source_file`).

## 4. Power BI-da açmaq
1. Power BI Desktop → **Get Data → Text/CSV** → `data\gold_csv\` qovluğundakı 3 faylı yükləyin.
2. **Model** görünüşündə əlaqələri qurun:
   - `fact_weather_daily.city_id` → `dim_city.city_id`
   - `fact_weather_daily.date_key` → `dim_date.date_key`
3. Məsələn: şəhər və mövsümə görə orta temperatur, aylar üzrə yağış qrafiki.

## 5. GitHub-a yükləmək
1. github.com-da yeni **public** repo yaradın, adı: `azerbaijan-weather-pipeline`.
2. "uploading an existing file" linkinə basın, layihə qovluğundakı faylları sürüşdürüb atın (`data` qovluğunu atmayın).
3. **Commit changes** basın.

## 6. Airflow haqqında qeyd
Airflow Windows-da birbaşa işləmir (WSL2 və ya Docker lazımdır). DAG faylı hazırdır və kodu oxumaq, izah etmək üçün kifayətdir. Pipeline özü `python run_pipeline.py` ilə Windows-da tam işləyir.
