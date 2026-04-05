from pydantic import BaseModel
from typing import Optional, List


class ResumeRequest(BaseModel):
    vacancy_text: str
    experience: str
    education: str
    skills: str
    additional_info: Optional[str] = ""


class CoverLetterRequest(BaseModel):
    vacancy_text: str
    candidate_summary: Optional[str] = ""


class InterviewStartRequest(BaseModel):
    vacancy_text: str
    candidate_summary: Optional[str] = ""


class InterviewAnswerRequest(BaseModel):
    answer: str
    vacancy_text: str
    candidate_summary: Optional[str] = ""
    conversation_history: List[dict]  # [{"role": "...", "content": "..."}]


class VacancyAnalysisRequest(BaseModel):
    vacancy_text: str


class AssistantMessageRequest(BaseModel):
    message: str


class PaymentCreateRequest(BaseModel):
    package: str     # basic, pro, vip, assistant_50, assistant_200, assistant_unlimited
    method: str      # crypto, rucard, revolut


class UserResponse(BaseModel):
    telegram_id: int
    username: Optional[str]
    full_name: Optional[str]
    credits_resume: int
    credits_cover_letter: int
    credits_interview: int
    credits_assistant: int
    subscription_type: str
    total_resumes_generated: int
    total_assistant_messages: int
    total_spent_rub: float
    referral_code: Optional[str]

    class Config:
        from_attributes = True


class GenerationResponse(BaseModel):
    text: str
    tokens_used: int
    credits_remaining: int


class PaymentResponse(BaseModel):
    method: str
    # Crypto
    payment_url: Optional[str] = None
    invoice_id: Optional[str] = None
    # Manual (RU card / Revolut)
    card_number: Optional[str] = None
    card_holder: Optional[str] = None
    bank_name: Optional[str] = None
    revolut_tag: Optional[str] = None
    revolut_link: Optional[str] = None
    amount_rub: Optional[int] = None
    amount_usdt: Optional[float] = None
    payment_db_id: Optional[int] = None


class CryptoCheckResponse(BaseModel):
    status: str   # active | paid | expired
