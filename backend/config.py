from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"
    llm_model: str = "google/gemini-3-flash-preview"

    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    models_dir: Path = Path(__file__).resolve().parent.parent / "models"

    max_image_width: int = 1800
    jpeg_quality: int = 78

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def db_path(self) -> Path:
        return self.data_dir / "letters.db"

    @property
    def db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path}"

    @property
    def pdf_dir(self) -> Path:
        return self.data_dir / "pdfs"


settings = Settings()
