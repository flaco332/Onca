-- Composite indexes avoid per-student sorting for latest/history lookups.
CREATE INDEX IF NOT EXISTS idx_payments_latest
ON payments(student_id, payment_date DESC, payment_id DESC);
CREATE INDEX IF NOT EXISTS idx_certificates_latest
ON medical_certificates(student_id, issue_date DESC, certificate_id DESC);
CREATE INDEX IF NOT EXISTS idx_participations_student
ON student_activities(student_id, student_activity_id DESC);
CREATE INDEX IF NOT EXISTS idx_participations_activity
ON student_activities(activity_id);

-- Do not rebuild legacy tables or remove legacy rows. Guard future writes.
CREATE TRIGGER IF NOT EXISTS payments_amount_insert
BEFORE INSERT ON payments WHEN NEW.amount IS NULL OR NEW.amount <= 0 OR NEW.amount > 1000000000
BEGIN SELECT RAISE(ABORT, 'invalid_payment_amount'); END;
CREATE TRIGGER IF NOT EXISTS payments_amount_update
BEFORE UPDATE OF amount ON payments WHEN NEW.amount IS NULL OR NEW.amount <= 0 OR NEW.amount > 1000000000
BEGIN SELECT RAISE(ABORT, 'invalid_payment_amount'); END;
CREATE TRIGGER IF NOT EXISTS activities_cost_insert
BEFORE INSERT ON extra_activities WHEN NEW.cost IS NULL OR NEW.cost < 0 OR NEW.cost > 1000000000
BEGIN SELECT RAISE(ABORT, 'invalid_activity_cost'); END;
CREATE TRIGGER IF NOT EXISTS activities_cost_update
BEFORE UPDATE OF cost ON extra_activities WHEN NEW.cost IS NULL OR NEW.cost < 0 OR NEW.cost > 1000000000
BEGIN SELECT RAISE(ABORT, 'invalid_activity_cost'); END;
CREATE TRIGGER IF NOT EXISTS participation_amount_insert
BEFORE INSERT ON student_activities WHEN NEW.paid_amount IS NULL OR NEW.paid_amount < 0 OR NEW.paid_amount > 1000000000
BEGIN SELECT RAISE(ABORT, 'invalid_participation_amount'); END;
CREATE TRIGGER IF NOT EXISTS participation_amount_update
BEFORE UPDATE OF paid_amount ON student_activities WHEN NEW.paid_amount IS NULL OR NEW.paid_amount < 0 OR NEW.paid_amount > 1000000000
BEGIN SELECT RAISE(ABORT, 'invalid_participation_amount'); END;

-- Historical duplicates remain, but new duplicate participation is rejected.
CREATE TRIGGER IF NOT EXISTS participation_unique_insert
BEFORE INSERT ON student_activities
WHEN EXISTS (SELECT 1 FROM student_activities WHERE student_id=NEW.student_id AND activity_id=NEW.activity_id)
BEGIN SELECT RAISE(ABORT, 'duplicate_participation'); END;
