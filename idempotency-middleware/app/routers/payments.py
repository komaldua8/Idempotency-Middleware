from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.payment_service import process_mock_payment

router=APIRouter(prefix="/api/v1")

class PaymentRequest(BaseModel):
    amount:float
@router.post("/payments")
async def create_payment(payload:PaymentRequest):
    result=await process_mock_payment(payload.amount)
    return result