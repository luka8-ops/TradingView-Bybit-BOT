# app/webhooks/tv_receiver.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import time
from app.config import settings
from app.api.bybit import bybit_client

router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class TradingViewPayload(BaseModel):
    passphrase: str
    symbol: str
    action: str
    entry_price: str

# Define your static trading parameters here
QUANTITY = "0.003"  
TP_PERCENT = 7.2
SL_PERCENT = 1.2
LEVERAGE = 30

@router.post("/tradingview-webhook")
async def handle_tradingview_webhook(payload: TradingViewPayload):
    """
    Receives and validates webhook alerts from TradingView and executes trades.
    """
    # logger.info(f"Received webhook payload: {payload.model_dump()}")

    if payload.passphrase != settings.TRADINGVIEW_PASSPHRASE:
        raise HTTPException(status_code=401, detail="Invalid passphrase")

    SYMBOL = payload.symbol.replace(".P", "")
    
    logger.info(f"Received signal for {payload.symbol}: {payload.action}. PAYLOAD PRICE: {payload.entry_price}")

    try:
        # First, we set the leverage for the symbol
        try:
            bybit_client.set_leverage(
                category="linear",
                symbol=SYMBOL,
                buyLeverage=str(LEVERAGE),
                sellLeverage=str(LEVERAGE)
            )
            logger.info(f"Leverage set to {LEVERAGE}x for {payload.symbol}")
        except Exception as e:
            # Bybit returns ErrCode: 110043 if leverage is already set, which we can ignore
            if "110043" in str(e):
                logger.info(f"Leverage is already set for {payload.symbol}, ignoring.")
            else:
                # If it's another error, something is wrong
                raise HTTPException(status_code=500, detail=f"Failed to set leverage: {e}")

        # Now, we process the trading action
        if payload.action == "buy":
            # 1. Place the initial market buy order
            response = bybit_client.place_order(
                category="linear",
                symbol=SYMBOL,
                side="Buy",
                orderType="Market",
                qty=QUANTITY
            )
            
            set_tp_sl(symbol=SYMBOL, entry_price=payload.entry_price, action=payload.action)

            logger.info("Order response:", response)
            return {"status": "success", "message": f"Long position opened and stops set for {payload.symbol}."}

        elif payload.action == "sell":
            # 1. Place a market sell order
            response = bybit_client.place_order(
                category="linear",
                symbol=SYMBOL,
                side="Sell",
                orderType="Market",
                qty=QUANTITY
            )

            set_tp_sl(symbol=SYMBOL, entry_price=payload.entry_price, action=payload.action)

            logger.info("Order response:", response)
            return {"status": "success", "message": f"Short position opened and stops set for {payload.symbol}."}

    except Exception as e:
        logger.info(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {e}")

# Calculates and sets Take Profit and Stop Loss for the given symbol and trade direction.
def set_tp_sl(symbol: str, entry_price: float, action: str):
    try: 
        price = float(entry_price)
        if action == "buy":
            tp_price = price * (1 + (TP_PERCENT / LEVERAGE / 100))
            sl_price = price * (1 - (SL_PERCENT / LEVERAGE / 100))

            tp_limit_price = tp_price * 0.999
            sl_limit_price = sl_price * 0.999

        elif action == "sell":
            tp_price = price * (1 - (TP_PERCENT / LEVERAGE / 100))
            sl_price = price * (1 + (SL_PERCENT / LEVERAGE / 100))

            tp_limit_price = tp_price * 1.001
            sl_limit_price = sl_price * 1.001

        else:
            raise ValueError("Invalid action for TP/SL calculation")

        bybit_client.set_trading_stop(
            category="linear",
            symbol=symbol,
            positionIdx=0,
            takeProfit=str(tp_price),
            stopLoss=str(sl_price),
            tpTriggerBy="LastPrice",
            slTriggerBy="LastPrice",
            tpslMode="Partial",
            tpOrderType="Limit",
            slOrderType="Limit",
            tpLimitPrice=str(tp_limit_price),  # Specify the limit price for TP
            slLimitPrice=str(sl_limit_price),  # Specify the limit price for SL
            tpSize=QUANTITY,                   # Specify TP size
            slSize=QUANTITY                    # Specify SL size, must equal tpSize
        )
        
    except ValueError as e:
        print(f"Error in TP/SL calculation: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
