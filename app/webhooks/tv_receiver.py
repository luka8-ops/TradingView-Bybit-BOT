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

# Define your static trading parameters here
QUANTITY = "0.001"  
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

    print(f"Received signal for {payload.symbol}: {payload.action}")

    if payload.symbol.endswith(".P"):
        payload.symbol = payload.symbol.replace(".P", "")
    
    print(f"Received signal for {payload.symbol}: {payload.action}")

    try:
        # First, we set the leverage for the symbol
        try:
            bybit_client.set_leverage(
                category="linear",
                symbol=payload.symbol,
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
            bybit_client.place_order(
                category="linear",
                symbol=payload.symbol,
                side="Buy",
                orderType="Market",
                qty=QUANTITY
            )
            
            # 2. Wait for the order to fill and get the entry price
            # This is the crucial part that was missing
            retries = 5
            entry_price = None
            while retries > 0 and not entry_price:
                time.sleep(2)  # Wait 2 seconds for the order to fill
                position_info = bybit_client.get_positions(category="linear", symbol=payload.symbol)
                
                if position_info.get("result", {}).get("list"):
                    position = position_info["result"]["list"][0]
                    if position["side"] == "Buy" and float(position["size"]) > 0:
                        entry_price = float(position["avgPrice"])
                retries -= 1
            
            if not entry_price:
                raise Exception("Failed to get position info after placing order.")

            # 3. Calculate SL and TP prices from our static percentages
            tp_price = entry_price * (1 + (TP_PERCENT / 100))
            sl_price = entry_price * (1 - (SL_PERCENT / 100))
            
            # 4. Set the SL and TP orders using the calculated prices
            bybit_client.set_trading_stop(
                category="linear",
                symbol=payload.symbol,
                tpPrice=str(tp_price),
                slPrice=str(sl_price),
                tpslMode="Full"
            )

            return {"status": "success", "message": f"Long position opened and stops set for {payload.symbol}."}

        elif payload.action == "sell":
            # 1. Place a market sell order
            bybit_client.place_order(
                category="linear",
                symbol=payload.symbol,
                side="Sell",
                orderType="Market",
                qty=QUANTITY
            )
            
            # 2. Wait for the order to fill and get the entry price
            retries = 5
            entry_price = None
            while retries > 0 and not entry_price:
                time.sleep(2)  # Wait 2 seconds for the order to fill
                position_info = bybit_client.get_positions(category="linear", symbol=payload.symbol)
                
                if position_info.get("result", {}).get("list"):
                    position = position_info["result"]["list"][0]
                    if position["side"] == "Sell" and float(position["size"]) > 0:
                        entry_price = float(position["avgPrice"])
                retries -= 1
            
            if not entry_price:
                raise Exception("Failed to get position info after placing order.")

            # 3. Calculate SL and TP prices (reversed for a short position)
            tp_price = entry_price * (1 - (TP_PERCENT / 100))
            sl_price = entry_price * (1 + (SL_PERCENT / 100))
            
            # 4. Set the SL and TP orders
            bybit_client.set_trading_stop(
                category="linear",
                symbol=payload.symbol,
                tpPrice=str(tp_price),
                slPrice=str(sl_price),
                tpslMode="Full"
            )
            return {"status": "success", "message": f"Short position opened and stops set for {payload.symbol}."}

        elif payload.action == "close":
            # Determine if it's a long or short position to close it correctly
            position_info = bybit_client.get_positions(category="linear", symbol=payload.symbol)
            if position_info.get("result", {}).get("list"):
                position = position_info["result"]["list"][0]
                if float(position["size"]) > 0:
                    # Place a market order to close the position
                    side_to_close = "Sell" if position["side"] == "Buy" else "Buy"
                    bybit_client.place_order(
                        category="linear",
                        symbol=payload.symbol,
                        side=side_to_close,
                        orderType="Market",
                        qty=position["size"],
                        reduceOnly=True
                    )
            return {"status": "success", "message": f"Position for {payload.symbol} fully closed."}

        else:
            return {"status": "ignored", "message": f"Action '{payload.action}' not supported."}

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {e}")