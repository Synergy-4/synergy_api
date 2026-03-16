import logging
from app.schemas.activity import ActivityPayload, ThemeConfig, FontConfig, GameConfig, StepConfig

logger = logging.getLogger(__name__)

def get_fallback_activity() -> ActivityPayload:
    # A static, safe fallback SDUI configuration
    return ActivityPayload(
        version="1.0.0",
        theme=ThemeConfig(
            primary_color="#FFA726",
            secondary_color="#FFCC80",
            background_color="#FFF3E0",
            card_color="#FFFFFF",
            heading_font=FontConfig(family="Comic Sans MS", size=24.0, weight="bold", color="#3E2723"),
            body_font=FontConfig(family="Arial", size=16.0, weight="normal", color="#4E342E")
        ),
        steps=[
            StepConfig(
                id="intro_1",
                type="instruction",
                title="Let's find the matching pairs!",
                description="Tap on the cards that look exactly the same.",
                voiceover_text="Let's find the matching pairs! Tap on the cards that look exactly the same."
            ),
            StepConfig(
                id="game_1",
                type="game",
                title="Matching Game",
                game_config=GameConfig(
                    game_type="matching",
                    difficulty="easy",
                    data={
                        "pairs": [
                            {"id": "apple", "image_url": "https://example.com/apple.png", "label": "Apple"},
                            {"id": "banana", "image_url": "https://example.com/banana.png", "label": "Banana"},
                            {"id": "orange", "image_url": "https://example.com/orange.png", "label": "Orange"}
                        ]
                    }
                )
            ),
            StepConfig(
                id="reward_1",
                type="reward",
                title="Great Job!",
                description="You found all the matches!",
                lottie_url="https://assets2.lottiefiles.com/packages/lf20_touohxv0.json",
                voiceover_text="Great Job! You found all the matches!"
            )
        ]
    )

def validate_and_fallback(payload_data: dict) -> ActivityPayload:
    try:
        # Pydantic handles the deep validation of all nested schemas
        return ActivityPayload.model_validate(payload_data)
    except Exception as e:
        logger.error(f"Failed to validate generated activity payload. Falling back. Error: {e}")
        return get_fallback_activity()
