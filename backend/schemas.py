from datetime import date, datetime

from pydantic import BaseModel


class TaskOut(BaseModel):
    id: int
    letter_id: int
    description: str
    deadline: date | None
    is_done: bool
    created_at: datetime
    letter_title: str | None = None
    letter_sender: str | None = None
    letter_receiver: str | None = None

    model_config = {"from_attributes": True}


class TaskUpdate(BaseModel):
    description: str | None = None
    deadline: date | None = None
    is_done: bool | None = None


class LetterOut(BaseModel):
    id: int
    title: str | None
    summary: str | None
    sender: str | None
    receiver: str | None
    creation_date: date | None
    ingested_at: datetime
    keywords: str | None
    tags: str | None
    full_text: str | None
    pdf_path: str | None
    page_count: int | None
    tasks: list[TaskOut] = []

    model_config = {"from_attributes": True}


class LetterUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    sender: str | None = None
    receiver: str | None = None
    creation_date: date | None = None
    keywords: str | None = None
    tags: str | None = None


class LetterListOut(BaseModel):
    id: int
    title: str | None
    summary: str | None
    sender: str | None
    receiver: str | None
    creation_date: date | None
    ingested_at: datetime
    keywords: str | None
    tags: str | None
    page_count: int | None

    model_config = {"from_attributes": True}


class LetterListResponse(BaseModel):
    items: list[LetterListOut]
    total: int


class IngestResponse(BaseModel):
    job_id: str


class SettingOut(BaseModel):
    key: str
    value: list[str]


class SettingUpdate(BaseModel):
    value: list[str]


class TranslationOut(BaseModel):
    id: int
    letter_id: int
    language: str
    translated_text: str | None
    translated_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
