-- No se divide name por espacios: los nombres compuestos son ambiguos.
-- Esta ruta se aplica únicamente a tablas antiguas sin first_name/last_name.
ALTER TABLE students RENAME COLUMN name TO first_name;
ALTER TABLE students ADD COLUMN last_name TEXT NOT NULL DEFAULT '';
