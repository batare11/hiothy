from inspect import getsource, signature
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.api.routes import users as user_routes
from app.api.routes.users import list_feedback
from app.api.routes.admin import delete_feedback, serialize_admin_feedback
from app.models.feedback import Feedback, FeedbackMessage
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


def test_logically_deleted_reply_is_hidden_from_admin_output():
    feedback = Feedback(
        id=1,
        mini_user_id="openid",
        content="测试反馈",
        status="pending",
        reply="原管理员回复",
        replied_at=datetime(2026, 6, 23, 12, 0),
        reply_deleted_at=datetime(2026, 6, 23, 13, 0),
        created_at=datetime(2026, 6, 23, 11, 0),
    )
    data = serialize_admin_feedback(feedback)
    assert data["reply"] is None
    assert data["replied_at"] is None


def test_feedback_message_supports_user_and_admin_conversation():
    user_message = FeedbackMessage(
        feedback_id=1,
        sender_type="user",
        sender_id="user-openid",
        content="我还有一个问题",
    )
    admin_message = FeedbackMessage(
        feedback_id=1,
        sender_type="admin",
        sender_id="admin-openid",
        content="请继续描述",
    )
    assert user_message.sender_type == "user"
    assert admin_message.sender_type == "admin"


def test_delete_feedback_also_logically_deletes_messages():
    source = getsource(delete_feedback)
    assert "update(FeedbackMessage)" in source
    assert "FeedbackMessage.feedback_id == feedback_id" in source
    assert "deleted_at=feedback.deleted_at" in source


def test_user_delete_feedback_also_logically_deletes_messages():
    source = getsource(user_routes.delete_feedback)
    assert "feedback.mini_user_id != mini_user_id" in source
    assert "update(FeedbackMessage)" in source
    assert "FeedbackMessage.feedback_id == feedback_id" in source
    assert "deleted_at=feedback.deleted_at" in source


def test_user_delete_message_only_allows_own_user_messages():
    source = getsource(user_routes.delete_feedback_message)
    assert 'message.sender_type != "user"' in source
    assert "message.sender_id != mini_user_id" in source
    assert "message.deleted_at = datetime.now()" in source
