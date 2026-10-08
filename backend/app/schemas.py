"""Request and response models. Pydantic validates every request at the boundary,
even when the frontend has already checked the same thing."""

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

RsvpResponse = Literal["yes", "no", "maybe"]

# Shared field types
Email = Annotated[EmailStr, Field(max_length=254)]
Title = Annotated[str, Field(min_length=1, max_length=120)]
Description = Annotated[str, Field(max_length=2000)]
Location = Annotated[str, Field(max_length=200)]
Capacity = Annotated[int, Field(ge=1, le=10000)]


class StrictModel(BaseModel):
    # Reject unknown fields and trim spaces around every string.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _must_be_future(value: datetime) -> datetime:
    if value <= datetime.now(timezone.utc):
        raise ValueError("must be in the future")
    return value


# ---------- auth ----------

class Credentials(StrictModel):
    email: Email
    password: Annotated[str, Field(min_length=8, max_length=128)]

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class Host(BaseModel):
    id: int
    email: str


# ---------- events (host) ----------

class EventCreate(StrictModel):
    title: Title
    description: Description = ""
    location: Location = ""
    starts_at: AwareDatetime  # must include a timezone, e.g. 2026-11-01T18:00:00Z
    capacity: Capacity | None = None

    @field_validator("starts_at")
    @classmethod
    def future(cls, v: datetime) -> datetime:
        return _must_be_future(v)


class EventUpdate(StrictModel):
    title: Title | None = None
    description: Description | None = None
    location: Location | None = None
    starts_at: AwareDatetime | None = None
    capacity: Capacity | None = None
    rsvp_open: bool | None = None

    @field_validator("starts_at")
    @classmethod
    def future_if_given(cls, v: datetime | None) -> datetime | None:
        return None if v is None else _must_be_future(v)

    @model_validator(mode="after")
    def only_capacity_can_be_null(self):
        # capacity: null means "remove the limit". Null makes no sense for the others.
        for name in self.model_fields_set - {"capacity"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        if not self.model_fields_set:
            raise ValueError("send at least one field to change")
        return self

    def changes(self) -> dict:
        """Only the fields the client actually sent."""
        return {name: getattr(self, name) for name in self.model_fields_set}


class Counts(BaseModel):
    yes: int
    no: int
    maybe: int
    attending: int


class HostEvent(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    location: str
    starts_at: datetime
    capacity: int | None
    rsvp_open: bool
    accepting_rsvps: bool
    counts: Counts
    created_at: datetime


class Rsvp(BaseModel):
    id: int
    name: str
    email: str
    response: RsvpResponse
    party_size: int
    note: str
    created_at: datetime


# ---------- public ----------

class PublicEvent(BaseModel):
    slug: str
    title: str
    description: str
    location: str
    starts_at: datetime
    accepting_rsvps: bool
    spots_left: int | None


class RsvpCreate(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: Email
    response: RsvpResponse
    party_size: Annotated[int, Field(ge=1, le=10)] = 1
    note: Annotated[str, Field(max_length=500)] = ""

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()


class RsvpConfirmation(BaseModel):
    name: str
    response: RsvpResponse
    party_size: int
