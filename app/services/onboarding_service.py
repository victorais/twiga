import logging
from typing import List, Optional, Tuple

from app.database.models import User, OnboardingState, UserState
from app.services.flow_service import flow_client
from app.database.db import update_user


class OnboardingHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.flow_client = flow_client
        self.state_handlers = {
            OnboardingState.new: self.handle_new,
            OnboardingState.personal_info_submitted: self.handle_personal_info_submitted,
            OnboardingState.class_subject_info_submitted: self.handle_class_subject_info_submitted,
            OnboardingState.completed: self.handle_completed,
        }

    async def handle_new(self, user: User) -> Tuple[str, Optional[List[str]]]:
        try:
            self.logger.info(f"Handling new user {user.wa_id}")
            # Call the send_personal_and_school_info_flow method from FlowService
            await self.flow_client.send_personal_and_school_info_flow(
                user.wa_id, user.name
            )

            self.logger.info(
                f"Triggered send_personal_and_school_info_flow for user {user.wa_id}"
            )

            response_text = None  # we don't want to send a response here since the flow will handle it
            options = None
            return response_text, options

        except Exception as e:
            self.logger.error(f"Error handling new user {user.wa_id}: {str(e)}")
            response_text = "An error occurred during the onboarding process. Please try again later."
            options = None
            return response_text, options

    async def handle_personal_info_submitted(
        self, user: User
    ) -> Tuple[str, Optional[List[str]]]:
        self.logger.info(f"Handling personal info submitted for user {user.wa_id}")

        await self.flow_client.send_class_and_subject_info_flow(user.wa_id, user.name)

        response_text = None
        options = None
        return response_text, options

    def handle_class_subject_info_submitted(
        self, user: User
    ) -> Tuple[str, Optional[List[str]]]:
        self.logger.info(
            f"Handling class and subject info submitted for user {user.wa_id}"
        )
        response_text = "Thank you for submitting your class and subject information. Your onboarding is almost complete."
        options = ["Complete Onboarding"]
        return response_text, options

    def handle_completed(self, user: User) -> Tuple[str, Optional[List[str]]]:
        self.logger.info(f"Handling completed onboarding for user {user.wa_id}")
        response_text = "Your onboarding is complete. Welcome!"
        options = None
        return response_text, options

    def handle_default(self, user: User) -> Tuple[str, Optional[List[str]]]:
        self.logger.info(f"Handling default onboarding state for user {user.wa_id}")
        response_text = "I'm not sure how to handle your request."
        options = None
        return response_text, options

    async def process_state(self, user: User) -> Tuple[str, Optional[List[str]]]:
        # Get the user's current state from the user object
        user_onboarding_state = user.on_boarding_state
        user_state = user.state

        # Update the user state to onboarding, only if the user is not already in the onboarding state
        if user_state != UserState.onboarding:
            await update_user(user.wa_id, state=UserState.onboarding)

            self.logger.info(
                f"Updated user state to {UserState.onboarding} for user {user.wa_id}"
            )

        self.logger.info(
            f"Going to handle OnboardingState: {user_onboarding_state} for user {user.wa_id}"
        )
        # Fetch the appropriate handler for the user's current state
        handler = self.state_handlers.get(user_onboarding_state, self.handle_default)
        response_text, options = await handler(user)

        self.logger.info(
            f"Processed message for {user.wa_id}: state={user_onboarding_state} -> response='{response_text}', options={options}"
        )

        return response_text, options


# Instantiate and export the OnboardingHandler client
onboarding_client = OnboardingHandler()
