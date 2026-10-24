from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="AwaazWeb API",
    description="Voice-first accessible web assistant",
    version="0.1.0",
)


class CommandRequest(BaseModel):
    command: str
    language: str = "hi-IN"


class CommandResponse(BaseModel):
    message: str
    intent: str
    status: str


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "awaazweb",
    }


@app.post("/api/command", response_model=CommandResponse)
def process_command(request: CommandRequest):
    command = request.command.lower().strip()

    if not command:
        return CommandResponse(
            message="Please tell me what you want me to do.",
            intent="unknown",
            status="needs_input",
        )

    scholarship_keywords = [
        "scholarship",
        "scholarship application",
        "scholarship status",
    ]

    if any(word in command for word in scholarship_keywords):
        return CommandResponse(
            message=(
                "I understood that you want to check "
                "your scholarship application status."
            ),
            intent="check_scholarship_status",
            status="planned",
        )

    return CommandResponse(
        message="This command is not supported yet.",
        intent="unknown",
        status="unsupported",
    )