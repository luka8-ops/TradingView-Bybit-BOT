# app/webhooks/tv_receiver.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.config import settings
from app.api.bybit import bybit_client
import time

router = APIRouter()

class TradingViewPayload(BaseModel):
    passphrase: str
    symbol: str
    action: str
    entry_price: float

# Define your static trading parameters here
QUANTITY = "0.004"  
TP_PERCENT = 4.3
SL_PERCENT = 1.0
LEVERAGE = 20

@router.post("/tradingview-webhook")
async def handle_tradingview_webhook(payload: TradingViewPayload):
    """
    Receives and validates webhook alerts from TradingView and executes trades.
    """
    if payload.passphrase != settings.TRADINGVIEW_PASSPHRASE:
        raise HTTPException(status_code=401, detail="Invalid passphrase")

    SYMBOL = payload.symbol.replace(".P", "")
    
    print(f"Received signal for {payload.symbol}: {payload.action}")

    try:
        # First, we set the leverage for the symbol
        try:
            bybit_client.set_leverage(
                category="linear",
                symbol=SYMBOL,
                buyLeverage=str(LEVERAGE),
                sellLeverage=str(LEVERAGE)
            )
            print(f"Leverage set to {LEVERAGE}x for {payload.symbol}")
        except Exception as e:
            # Bybit returns ErrCode: 110043 if leverage is already set, which we can ignore
            if "110043" in str(e):
                print(f"Leverage is already set for {payload.symbol}, ignoring.")
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
            
            wait_for_position_open(SYMBOL)
            set_tp_sl(symbol=SYMBOL, entry_price=payload.entry_price, action=payload.action)

            print("Order response:", response)
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

            wait_for_position_open(SYMBOL)
            set_tp_sl(symbol=SYMBOL, entry_price=payload.entry_price, action=payload.action)

            print("Order response:", response)
            return {"status": "success", "message": f"Short position opened and stops set for {payload.symbol}."}

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {e}")
    
# Polls the Bybit API until a position is open for the given symbol.
def wait_for_position_open(symbol: str, max_retries: int = 10, delay: float = 0.5):
    for attempt in range(max_retries):
        position = bybit_client.get_positions(
            category="linear",
            symbol=symbol
        )
        try:
            size = float(position["result"]["list"][0]["size"])
            print(f"[Attempt {attempt + 1}] Position size: {size}")
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise HTTPException(status_code=500, detail=f"Invalid position response: {e}")
        
        if size > 0:
            print("Position opened")
            return  
        time.sleep(delay)
    
    raise HTTPException(status_code=500, detail="Position not open after waiting")

# Calculates and sets Take Profit and Stop Loss for the given symbol and trade direction.
def set_tp_sl(symbol: str, entry_price: float, action: str):
    if action == "buy":
        tp_price = entry_price * (1 + (TP_PERCENT / LEVERAGE / 100))
        sl_price = entry_price * (1 - (SL_PERCENT / LEVERAGE / 100))
    elif action == "sell":
        tp_price = entry_price * (1 - (TP_PERCENT / LEVERAGE / 100))
        sl_price = entry_price * (1 + (SL_PERCENT / LEVERAGE / 100))
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
        tpslMode="Full"
    )

