from fastapi import APIRouter
from ..models.api import (
    OnboardingSubmission,
    OnboardingSubmissionResponse,
)

router = APIRouter()

@router.post("/onboarding", response_model=OnboardingSubmissionResponse)
def submit_onboarding_form(submission: OnboardingSubmission) -> OnboardingSubmissionResponse:
    # In a real application, this would persist the submission to a database
    # and potentially trigger further actions (e.g., send welcome email).
    # For this example, we just return the received submission.
    return OnboardingSubmissionResponse(
        message="Onboarding form submitted successfully!",
        submission=submission,
    )
