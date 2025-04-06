from pydantic import BaseModel, Field

class EmailContent(BaseModel):
    """Model for email content"""
    subject: str = Field(description="The email subject")
    body: str = Field(description="The email body content")
    sender: str = Field(description="The email sender")