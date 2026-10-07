-- La existencia de un adjunto antiguo no demuestra una verificación médica.
-- El estado empieza desmarcado y se confirma explícitamente al guardar el alumno.
ALTER TABLE students ADD COLUMN medical_verified INTEGER NOT NULL DEFAULT 0
    CHECK (medical_verified IN (0, 1));
