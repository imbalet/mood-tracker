"""Public input and output contracts for application use cases."""

from mood_tracker.application.contracts.calendar import GetMonthCalendar, MonthCalendar
from mood_tracker.application.contracts.diary import (
    ConfirmReference,
    DayForm,
    GetDay,
    ReferenceReview,
    SaveDayValue,
    SkipDayText,
)
from mood_tracker.application.contracts.events import (
    ChangeEventTime,
    CompleteEvent,
    CreateEvent,
    CreateQuickEvent,
    DeleteEvent,
    GetEvent,
    GetEventsForDate,
    SaveEventValue,
    SkipEventField,
)
from mood_tracker.application.contracts.questionnaires import (
    AddFieldVersion,
    AttachFieldToQuestionnaire,
    CreateField,
    DeleteField,
    DetachFieldFromQuestionnaire,
    ListQuestionnaireFields,
    MoveQuestionnaireField,
    QuestionnaireFieldItem,
    RenameField,
    SetFieldDisplay,
    SetQuestionnaireFieldEnabled,
    SetQuestionnaireFieldRequired,
)
from mood_tracker.application.contracts.references import (
    GetReferenceHistory,
    ReferenceHistory,
)
from mood_tracker.application.contracts.users import (
    GetUserByTelegramId,
    RegisterUser,
    SetTimezone,
)

__all__ = [
    "AddFieldVersion",
    "AttachFieldToQuestionnaire",
    "ChangeEventTime",
    "CompleteEvent",
    "ConfirmReference",
    "CreateEvent",
    "CreateField",
    "CreateQuickEvent",
    "DayForm",
    "DeleteEvent",
    "DeleteField",
    "DetachFieldFromQuestionnaire",
    "GetDay",
    "GetEvent",
    "GetEventsForDate",
    "GetMonthCalendar",
    "GetReferenceHistory",
    "GetUserByTelegramId",
    "ListQuestionnaireFields",
    "MonthCalendar",
    "MoveQuestionnaireField",
    "QuestionnaireFieldItem",
    "ReferenceHistory",
    "ReferenceReview",
    "RegisterUser",
    "RenameField",
    "SaveDayValue",
    "SaveEventValue",
    "SetFieldDisplay",
    "SetQuestionnaireFieldEnabled",
    "SetQuestionnaireFieldRequired",
    "SetTimezone",
    "SkipDayText",
    "SkipEventField",
]
