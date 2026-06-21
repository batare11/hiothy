from pathlib import Path


SCHEMA_SQL = (
    Path(__file__).resolve().parents[1] / "scripts" / "schema.sql"
).read_text(encoding="utf-8")


def test_schema_contains_all_business_tables():
    for table_name in (
        "bp_records",
        "user_profiles",
        "health_archives",
        "messages",
        "feedback",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in SCHEMA_SQL


def test_schema_contains_later_added_fields():
    for column_name in (
        "hypertension_grade",
        "age",
        "height_cm",
        "weight_jin",
        "gender",
        "marital_status",
        "smoking",
        "drinking",
        "staying_up_late",
        "note",
    ):
        assert column_name in SCHEMA_SQL
    for message_column in (
        "severity",
        "related_record_id",
        "action_type",
        "action_path",
        "dedupe_key",
    ):
        assert message_column in SCHEMA_SQL


def test_schema_contains_old_dictionary_conversion_and_grade_backfill():
    assert "ALTER COLUMN gender TYPE INTEGER" in SCHEMA_SQL
    assert "ALTER COLUMN marital_status TYPE INTEGER" in SCHEMA_SQL
    assert "UPDATE bp_records" in SCHEMA_SQL


def test_schema_guarantees_hypertension_grade_on_every_write():
    assert "set_bp_hypertension_grade" in SCHEMA_SQL
    assert "BEFORE INSERT OR UPDATE OF systolic, diastolic" in SCHEMA_SQL
    assert "ALTER COLUMN hypertension_grade SET NOT NULL" in SCHEMA_SQL


def test_schema_contains_table_and_column_comments():
    table_columns = {
        "bp_records": (
            "id",
            "systolic",
            "diastolic",
            "heart_rate",
            "hypertension_grade",
            "created_at",
            "updated_at",
            "user_id",
            "mini_user_id",
            "mini_user_name",
            "note",
        ),
        "user_profiles": (
            "id",
            "mini_user_id",
            "nickname",
            "avatar_url",
            "gender",
            "phone",
            "birth_date",
            "created_at",
            "updated_at",
        ),
        "health_archives": (
            "id",
            "mini_user_id",
            "age",
            "height_cm",
            "weight_jin",
            "gender",
            "marital_status",
            "smoking",
            "drinking",
            "staying_up_late",
            "note",
            "created_at",
            "updated_at",
        ),
        "messages": (
            "id",
            "mini_user_id",
            "title",
            "content",
            "message_type",
            "severity",
            "related_record_id",
            "action_type",
            "action_path",
            "dedupe_key",
            "is_read",
            "created_at",
        ),
        "feedback": (
            "id",
            "mini_user_id",
            "content",
            "contact",
            "status",
            "created_at",
        ),
    }
    for table_name, columns in table_columns.items():
        assert f"COMMENT ON TABLE {table_name} IS" in SCHEMA_SQL
        for column_name in columns:
            assert (
                f"COMMENT ON COLUMN {table_name}.{column_name} IS"
                in SCHEMA_SQL
            )
