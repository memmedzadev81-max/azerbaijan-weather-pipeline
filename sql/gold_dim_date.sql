-- Adds any dates that exist in silver but are missing from dim_date.
INSERT OR IGNORE INTO dim_date
    (date_key, full_date, year, quarter, month, month_name, day,
     day_of_week, day_name, is_weekend, season)
SELECT
    CAST(strftime('%Y%m%d', d) AS INTEGER)                    AS date_key,
    d                                                         AS full_date,
    CAST(strftime('%Y', d) AS INTEGER)                        AS year,
    (CAST(strftime('%m', d) AS INTEGER) + 2) / 3              AS quarter,
    CAST(strftime('%m', d) AS INTEGER)                        AS month,
    CASE strftime('%m', d)
        WHEN '01' THEN 'January'  WHEN '02' THEN 'February' WHEN '03' THEN 'March'
        WHEN '04' THEN 'April'    WHEN '05' THEN 'May'      WHEN '06' THEN 'June'
        WHEN '07' THEN 'July'     WHEN '08' THEN 'August'   WHEN '09' THEN 'September'
        WHEN '10' THEN 'October'  WHEN '11' THEN 'November' ELSE 'December'
    END                                                       AS month_name,
    CAST(strftime('%d', d) AS INTEGER)                        AS day,
    -- SQLite: %w gives 0 = Sunday; convert to ISO 1 = Monday ... 7 = Sunday
    ((CAST(strftime('%w', d) AS INTEGER) + 6) % 7) + 1        AS day_of_week,
    CASE strftime('%w', d)
        WHEN '0' THEN 'Sunday'   WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday'
        WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday'
        ELSE 'Saturday'
    END                                                       AS day_name,
    CASE WHEN strftime('%w', d) IN ('0', '6') THEN 1 ELSE 0 END AS is_weekend,
    CASE
        WHEN CAST(strftime('%m', d) AS INTEGER) IN (12, 1, 2) THEN 'Winter'
        WHEN CAST(strftime('%m', d) AS INTEGER) IN (3, 4, 5)  THEN 'Spring'
        WHEN CAST(strftime('%m', d) AS INTEGER) IN (6, 7, 8)  THEN 'Summer'
        ELSE 'Autumn'
    END                                                       AS season
FROM (SELECT DISTINCT observed_date AS d FROM silver_weather_hourly);
