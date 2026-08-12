"""Reusable owner-scoped reads for Telegram presentation flows."""

from uuid import UUID

from mood_tracker.application.contracts.questionnaires import ListQuestionnaireFields
from mood_tracker.application.contracts.users import GetUserByTelegramId
from mood_tracker.domain.entities import Field, UserProfile
from mood_tracker.domain.enums import QuestionnaireKind
from mood_tracker.presentation.services import ApplicationServices


# TODO: move
async def get_user_profile(
    telegram_id: int, services: ApplicationServices
) -> UserProfile | None:
    """Return the profile belonging to one Telegram account."""
    return await services.get_user_by_telegram_id().execute(
        GetUserByTelegramId(telegram_id)
    )


async def get_owned_field(
    profile: UserProfile, field_id: UUID, services: ApplicationServices
) -> Field | None:
    """Return a field only when it belongs to the supplied profile."""
    return next(
        (
            item.field
            for item in await services.list_questionnaire_fields().execute(
                ListQuestionnaireFields(profile.id, QuestionnaireKind.DAY)
            )
            if item.field.id == field_id
        ),
        None,
    )
