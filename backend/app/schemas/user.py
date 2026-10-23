
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("name")
    @classmethod
    def validate_name(cls, val: str) -> str:
        val = val.strip()

        if not val:
            raise ValueError("Name cannot be empty or whitespace")

        return val

    @field_validator("email")
    @classmethod
    def validate_college_email(cls, val: EmailStr) -> EmailStr:
        domain = str(val).rsplit("@", 1)[1].lower()

        if domain != "nitp.ac.in":
            raise ValueError(
                "Only @nitp.ac.in email addresses are allowed"
            )

        return val
