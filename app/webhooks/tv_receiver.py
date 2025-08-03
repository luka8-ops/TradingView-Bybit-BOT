# app/webhooks/tv_receiver.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.config import settings
from app.api.bybit import bybit_client

router = APIRouter()

class TradingViewPayload(BaseModel):
    passphrase: str
    symbol: str
    action: str
    qty: Optional[str] = None
    leverage: Optional[int] = 10
    stop_loss_price: Optional[str] = None
    take_profit_price: Optional[str] = None
    comment: Optional[str] = None

@router.post("/tradingview-webhook")
async def handle_tradingview_webhook(payload: TradingViewPayload):
    """
    Receives and validates webhook alerts from TradingView and executes trades.
    """
    if payload.passphrase != settings.TRADINGVIEW_PASSPHRASE:
        raise HTTPException(status_code=401, detail="Invalid passphrase")

    print(f"Received signal for {payload.symbol}: {payload.action}")

    try:
        if payload.action == "open_long":
            # Place a market buy order using pybit's place_order method
            bybit_client.place_order(
                category="linear",
                symbol=payload.symbol,
                side="Buy",
                orderType="Market",
                qty=payload.qty,
                leverage=str(payload.leverage)
            )

            # Set the SL and TP if provided
            if payload.stop_loss_price or payload.take_profit_price:
                bybit_client.set_trading_stop(
                    category="linear",
                    symbol=payload.symbol,
                    tpPrice=payload.take_profit_price if payload.take_profit_price else None,
                    slPrice=payload.stop_loss_price if payload.stop_loss_price else None,
                    tpslMode="Full"
                )

            return {"status": "success", "message": f"Long position opened and stops set for {payload.symbol}."}

        elif payload.action == "open_short":
            # Place a market sell order
            bybit_client.place_order(
                category="linear",
                symbol=payload.symbol,
                side="Sell",
                orderType="Market",
                qty=payload.qty,
                leverage=str(payload.leverage)
            )

            # Set the SL and TP if provided
            if payload.stop_loss_price or payload.take_profit_price:
                bybit_client.set_trading_stop(
                    category="linear",
                    symbol=payload.symbol,
                    tpPrice=payload.take_profit_price if payload.take_profit_price else None,
                    slPrice=payload.stop_loss_price if payload.stop_loss_price else None,
                    tpslMode="Full"
                )

            return {"status": "success", "message": f"Short position opened and stops set for {payload.symbol}."}

        elif payload.action == "close_long":
            # Close the entire position by placing a market sell order with reduce_only=True
            bybit_client.place_order(
                category="linear",
                symbol=payload.symbol,
                side="Sell",
                orderType="Market",
                qty=payload.qty,
                reduceOnly=True
            )
            return {"status": "success", "message": f"Long position for {payload.symbol} fully closed."}

        elif payload.action == "close_short":
            # Close the entire position by placing a market buy order with reduce_only=True
            bybit_client.place_order(
                category="linear",
                symbol=payload.symbol,
                side="Buy",
                orderType="Market",
                qty=payload.qty,
                reduceOnly=True
            )
            return {"status": "success", "message": f"Short position for {payload.symbol} fully closed."}
        
        else:
            return {"status": "ignored", "message": f"Action '{payload.action}' not supported."}

    except Exception as e:
        print(f"An error occurred: {e}")
        # The pybit library returns a rich error object. We can inspect it if needed.
        # For now, a generic 500 error is fine.
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {e}")