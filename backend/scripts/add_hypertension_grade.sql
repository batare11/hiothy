ALTER TABLE bp_records
ADD COLUMN IF NOT EXISTS hypertension_grade INTEGER;

UPDATE bp_records
SET hypertension_grade = CASE
    WHEN systolic >= 180 OR diastolic >= 110 THEN 3
    WHEN systolic >= 160 OR diastolic >= 100 THEN 2
    WHEN systolic >= 140 OR diastolic >= 90 THEN 1
    ELSE 0
END
WHERE hypertension_grade IS NULL;

ALTER TABLE bp_records
ALTER COLUMN hypertension_grade SET DEFAULT 0;

ALTER TABLE bp_records
ALTER COLUMN hypertension_grade SET NOT NULL;

CREATE OR REPLACE FUNCTION set_bp_hypertension_grade()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.hypertension_grade := CASE
        WHEN NEW.systolic >= 180 OR NEW.diastolic >= 110 THEN 3
        WHEN NEW.systolic >= 160 OR NEW.diastolic >= 100 THEN 2
        WHEN NEW.systolic >= 140 OR NEW.diastolic >= 90 THEN 1
        ELSE 0
    END;
    RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS trg_bp_records_set_hypertension_grade ON bp_records;
CREATE TRIGGER trg_bp_records_set_hypertension_grade
BEFORE INSERT OR UPDATE OF systolic, diastolic
ON bp_records
FOR EACH ROW
EXECUTE FUNCTION set_bp_hypertension_grade();

COMMENT ON COLUMN bp_records.hypertension_grade
IS '成人诊室血压高血压等级：0=未达到高血压，1=1级，2=2级，3=3级';
