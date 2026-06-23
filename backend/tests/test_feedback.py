from inspect import signature

import pytest
from pydantic import ValidationError

from app.api.routes.users import list_feedback
from app.schemas.user import FeedbackCreate, FeedbackReply, UserProfileUpdate


def test_feedback_history_is_paginated():
    parameters = signature(list_feedback).parameters
    assert parameters["page"].default.default == 1
    assert parameters["page_size"].default.default == 10


def test_profile_schema_rejects_phone_collection():
    with pytest.raises(ValidationError):
        UserProfileUpdate(nickname="测试用户", phone="13800138000")


def test_feedback_schema_rejects_contact_collection():
    with pytest.raises(ValidationError):
        FeedbackCreate(content="测试反馈", contact="13800138000")


def test_feedback_reply_requires_meaningful_content():
    with pytest.raises(ValidationError):
        FeedbackReply(reply="好")
    assert FeedbackReply(reply="已经处理").reply == "已经处理"
