from fastapi import APIRouter, Depends, HTTPException
from api.middleware.auth import get_telegram_user
from api.schemas import PaymentCreateRequest, PaymentResponse, CryptoCheckResponse
from config import PRICING, CRYPTOBOT_TOKEN, RU_CARD_NUMBER, RU_CARD_HOLDER, RU_BANK_NAME, REVOLUT_TAG, REVOLUT_LINK
from database.db import save_payment

router = APIRouter()


@router.post("/create", response_model=PaymentResponse)
async def api_create_payment(
    req: PaymentCreateRequest,
    tg_user: dict = Depends(get_telegram_user),
):
    if req.package not in PRICING:
        raise HTTPException(status_code=400, detail="Unknown package")

    pkg = PRICING[req.package]

    if req.method == "crypto":
        if not CRYPTOBOT_TOKEN:
            raise HTTPException(status_code=503, detail="Crypto payments not configured")
        from services.payment_service import create_crypto_invoice
        pay_url, invoice_id = await create_crypto_invoice(tg_user["id"], req.package)
        await save_payment(
            telegram_id=tg_user["id"],
            amount_rub=pkg["price_rub"],
            package=req.package,
            payment_id=invoice_id,
        )
        return PaymentResponse(
            method="crypto",
            payment_url=pay_url,
            invoice_id=invoice_id,
            amount_rub=pkg["price_rub"],
            amount_usdt=pkg.get("price_usdt"),
        )

    elif req.method == "rucard":
        db_payment = await save_payment(
            telegram_id=tg_user["id"],
            amount_rub=pkg["price_rub"],
            package=req.package,
        )
        return PaymentResponse(
            method="rucard",
            card_number=RU_CARD_NUMBER,
            card_holder=RU_CARD_HOLDER,
            bank_name=RU_BANK_NAME,
            amount_rub=pkg["price_rub"],
            payment_db_id=db_payment.id,
        )

    elif req.method == "revolut":
        db_payment = await save_payment(
            telegram_id=tg_user["id"],
            amount_rub=pkg["price_rub"],
            package=req.package,
        )
        return PaymentResponse(
            method="revolut",
            revolut_tag=REVOLUT_TAG,
            revolut_link=REVOLUT_LINK or None,
            amount_rub=pkg["price_rub"],
            amount_usdt=pkg.get("price_usdt"),
            payment_db_id=db_payment.id,
        )

    raise HTTPException(status_code=400, detail="Unknown payment method")


@router.get("/check/{invoice_id}", response_model=CryptoCheckResponse)
async def check_crypto_payment(
    invoice_id: str,
    package: str,
    tg_user: dict = Depends(get_telegram_user),
):
    from services.payment_service import check_crypto_invoice, apply_package_credits
    from database.db import update_payment_status
    status = await check_crypto_invoice(invoice_id)
    if status == "paid":
        await apply_package_credits(tg_user["id"], package)
        await update_payment_status(invoice_id, "succeeded")
    return CryptoCheckResponse(status=status)
