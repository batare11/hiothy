from inspect import signature

from app.api.routes.users import list_feedback


def test_feedback_history_is_paginated():
    parameters = signature(list_feedback).parameters
    assert parameters["page"].default.default == 1
    assert parameters["page_size"].default.default == 10
