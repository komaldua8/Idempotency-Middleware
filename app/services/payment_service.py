#payments service
import asyncio
async def process_mock_payment(amount: float)->dict:
    await asyncio.sleep(2)
    return{
        "success": True,
        "amount": amount,
        "transaction_id":f"tx_mock_{id(amount)}"
    }