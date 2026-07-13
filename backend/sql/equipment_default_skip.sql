-- 設備マスタ: 普段は使用しない（一覧・カレンダーで初期「本日は使用しない」）
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('equipments') AND name = 'default_skip'
)
BEGIN
    ALTER TABLE equipments ADD default_skip BIT NOT NULL
        CONSTRAINT DF_equipments_default_skip DEFAULT 0;
END

-- 普段は使用しない設備を、その日だけ「使用する」にした記録
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'equipment_day_use')
BEGIN
    CREATE TABLE equipment_day_use (
        id INT IDENTITY(1,1) PRIMARY KEY,
        equipment_id INT NOT NULL,
        use_date DATE NOT NULL,
        CONSTRAINT UQ_equipment_day_use UNIQUE (equipment_id, use_date)
    );
END
