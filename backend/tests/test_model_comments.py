from app.core.database import Base
from app.models import (
    BloodPressureRecord,
    Feedback,
    HealthArchive,
    Message,
    UserProfile,
)


def test_all_model_tables_and_columns_have_comments():
    models = (
        BloodPressureRecord,
        UserProfile,
        HealthArchive,
        Message,
        Feedback,
    )
    for model in models:
        table = model.__table__
        assert table.comment
        for column in table.columns:
            assert column.comment, f"{table.name}.{column.name} 缺少字段注释"


def test_all_business_models_are_registered():
    assert {
        "bp_records",
        "user_profiles",
        "health_archives",
        "messages",
        "feedback",
    }.issubset(Base.metadata.tables)
