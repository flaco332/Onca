"""Datos sintéticos en memoria para verificar planes SQL; nunca seed de producción."""


def populate_query_plan_fixture(conn):
    conn.execute("INSERT INTO students(first_name,last_name) VALUES ('Alumno','Prueba')")
    conn.executemany("INSERT INTO payments(student_id,amount,payment_date,payment_month) VALUES (1,1,?,'2026-01')",
                     [(f"2026-01-{day:02d}",) for day in range(1, 29)] * 20)
