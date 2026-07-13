-- その日「使用しない」設備（点検・カレンダー対象外）
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'equipment_day_skip')
BEGIN
    CREATE TABLE equipment_day_skip (
        id INT IDENTITY(1,1) PRIMARY KEY,
        equipment_id INT NOT NULL,
        skip_date DATE NOT NULL,
        CONSTRAINT UQ_equipment_day_skip UNIQUE (equipment_id, skip_date)
    );
END
