//+------------------------------------------------------------------+
//|                        GoldScalperResearch_v14_NY_LondonRetest.mq5|
//|               Copyright 2026, GoldScalperResearch (GSR) Team     |
//|                    High-Expectancy Edge Discovery Architecture   |
//+------------------------------------------------------------------+
#property copyright   "Copyright 2026, GoldScalperResearch Team"
#property link        "https://github.com/GoldScalperResearch"
#property version     "14.00"
#property description "GSR v14: London-to-New York Midpoint Retest Continuation Engine"
#property strict

#include <Trade\Trade.mqh>

//--- Input Parameters
input group "=== Trading Parameters ==="
input double   InpLots              = 0.02;     // Fixed Lot Size (Simulation Baseline)
input ulong    InpMagicNumber       = 140001;   // Magic Number
input int      InpTradeHour         = 13;       // Execution Hour (UTC, 13:00)
input int      InpLondonStartHour   = 7;        // London Start Hour (UTC)
input int      InpLondonEndHour     = 11;       // London Trend End Hour (UTC)
input int      InpPreNYHour         = 12;       // Pre-NY Pullback Hour (UTC)
input double   InpMinLondonRange    = 8.0;      // Minimum London Range ($/oz)
input double   InpMaxLondonRange    = 32.0;     // Maximum London Range ($/oz)
input double   InpTargetR           = 2.0;      // Reward-to-Risk Target Ratio (R)
input int      InpMaxBarsHold       = 12;       // Maximum Holding Time in H1 Bars

input group "=== Risk & Protection Guards ==="
input int      InpMaxSpreadPoints   = 80;       // Max Spread Allowed in Points (80 = $0.80)
input bool     InpCloseFriday       = true;     // Mandatory Friday Position Close
input int      InpCloseFridayHour   = 20;       // Friday Close Hour (UTC)

//--- Global Objects
CTrade         ExtTrade;
datetime       g_lastBarTime        = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   ExtTrade.SetExpertMagicNumber(InpMagicNumber);
   ExtTrade.SetMarginMode();
   ExtTrade.SetTypeFillingBySymbol(_Symbol);
   
   PrintFormat("GSR v14 Initialized: Symbol=%s, Magic=%d, Lots=%.2f, TargetR=%.1f",
               _Symbol, InpMagicNumber, InpLots, InpTargetR);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   PrintFormat("GSR v14 Deinitialized. Reason code: %d", reason);
}

//+------------------------------------------------------------------+
//| Position Count Helper                                            |
//+------------------------------------------------------------------+
bool HasOpenPosition(ulong magic)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == _Symbol)
      {
         if(PositionGetInteger(POSITION_MAGIC) == magic)
            return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| Close All Positions on Friday / Timeout                          |
//+------------------------------------------------------------------+
void CloseAllPositions(ulong magic, string comment)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == _Symbol)
      {
         if(PositionGetInteger(POSITION_MAGIC) == magic)
         {
            ulong ticket = PositionGetTicket(i);
            if(ticket > 0)
            {
               ExtTrade.PositionClose(ticket);
               PrintFormat("GSR v14 Closed Ticket %d. Reason: %s", ticket, comment);
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Check Position Holding Duration                                  |
//+------------------------------------------------------------------+
void CheckHoldingTimeout(ulong magic, int maxBars)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == _Symbol)
      {
         if(PositionGetInteger(POSITION_MAGIC) == magic)
         {
            datetime posTime = (datetime)PositionGetInteger(POSITION_TIME);
            int barsHeld = iBarShift(_Symbol, PERIOD_H1, posTime);
            if(barsHeld >= maxBars)
            {
               ulong ticket = PositionGetTicket(i);
               if(ticket > 0)
               {
                  ExtTrade.PositionClose(ticket);
                  PrintFormat("GSR v14 Timeout Exit after %d bars. Ticket %d", barsHeld, ticket);
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check bar open on H1
   datetime currentBarTime = iTime(_Symbol, PERIOD_H1, 0);
   if(currentBarTime == 0) return;
   
   bool isNewBar = (currentBarTime != g_lastBarTime);
   if(isNewBar)
   {
      g_lastBarTime = currentBarTime;
   }
   else
   {
      return; // Strictly execute on new H1 bar open
   }
   
   MqlDateTime dt;
   TimeToStruct(currentBarTime, dt);
   
   // 1. Mandatory Friday Close Guard
   if(InpCloseFriday && dt.day_of_week == 5 && dt.hour >= InpCloseFridayHour)
   {
      if(HasOpenPosition(InpMagicNumber))
      {
         CloseAllPositions(InpMagicNumber, "Friday Risk Flattening");
      }
      return;
   }
   
   // 2. Check holding duration for existing positions
   CheckHoldingTimeout(InpMagicNumber, InpMaxBarsHold);
   
   // 3. Single position concurrency guard
   if(HasOpenPosition(InpMagicNumber))
   {
      return;
   }
   
   // 4. Spread Guard Check
   long spreadPoints = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spreadPoints > InpMaxSpreadPoints)
   {
      PrintFormat("GSR v14 Spread too wide: %d > %d", spreadPoints, InpMaxSpreadPoints);
      return;
   }
   
   // 5. Evaluate Execution Condition at InpTradeHour (13:00 UTC)
   if(dt.hour != InpTradeHour)
   {
      return;
   }
   
   // Copy last 24 H1 bars
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, PERIOD_H1, 0, 24, rates);
   if(copied < 15) return;
   
   // Identify London Session Bars (07:00 to 11:00 UTC today)
   // In bar series: rates[0] is current 13:00 bar, rates[1] is 12:00, rates[2] is 11:00, ..., rates[6] is 07:00
   double londonHigh = -1.0;
   double londonLow  = 999999.0;
   int londonBarCount = 0;
   double londonClose = 0.0;
   
   for(int b = 1; b < 15; b++)
   {
      MqlDateTime barDt;
      TimeToStruct(rates[b].time, barDt);
      if(barDt.day == dt.day && barDt.mon == dt.mon && barDt.year == dt.year)
      {
         if(barDt.hour >= InpLondonStartHour && barDt.hour <= InpLondonEndHour)
         {
            if(rates[b].high > londonHigh) londonHigh = rates[b].high;
            if(rates[b].low < londonLow)   londonLow  = rates[b].low;
            londonBarCount++;
            if(barDt.hour == InpLondonEndHour)
            {
               londonClose = rates[b].close;
            }
         }
      }
   }
   
   if(londonBarCount < 4 || londonHigh <= 0 || londonLow >= 900000.0) return;
   
   double londonRange = londonHigh - londonLow;
   if(londonRange < InpMinLondonRange || londonRange > InpMaxLondonRange) return;
   
   double londonMidpoint = (londonHigh + londonLow) / 2.0;
   
   // Inspect completed 12:00 UTC bar (rates[1])
   MqlRates bar12 = rates[1];
   MqlDateTime dt12;
   TimeToStruct(bar12.time, dt12);
   if(dt12.hour != InpPreNYHour) return;
   
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   
   // SETUP A: Bullish London Trend Continuation
   // London closed in top 35% of range; 12:00 bar pulled back to midpoint + $2.50, but closed above midpoint
   if(londonClose > (londonLow + 0.65 * londonRange))
   {
      if(bar12.low <= (londonMidpoint + 2.5) && bar12.close > londonMidpoint)
      {
         double sl = londonLow - 0.50;
         double riskDist = ask - sl;
         
         if(riskDist >= 6.0 && riskDist <= 25.0)
         {
            double tp = NormalizeDouble(ask + (riskDist * InpTargetR), _Digits);
            sl = NormalizeDouble(sl, _Digits);
            
            ExtTrade.Buy(InpLots, _Symbol, ask, sl, tp, "GSR14_NY_London_Buy");
            PrintFormat("GSR v14 BUY: Ask=%.3f, SL=%.3f, TP=%.3f, Risk=%.2f, LondonR=%.2f",
                        ask, sl, tp, riskDist, londonRange);
         }
      }
   }
   // SETUP B: Bearish London Trend Continuation
   // London closed in bottom 35% of range; 12:00 bar pulled back to midpoint - $2.50, but closed below midpoint
   else if(londonClose < (londonLow + 0.35 * londonRange))
   {
      if(bar12.high >= (londonMidpoint - 2.5) && bar12.close < londonMidpoint)
      {
         double sl = londonHigh + 0.50 + (ask - bid);
         double riskDist = sl - bid;
         
         if(riskDist >= 6.0 && riskDist <= 25.0)
         {
            double tp = NormalizeDouble(bid - (riskDist * InpTargetR), _Digits);
            sl = NormalizeDouble(sl, _Digits);
            
            ExtTrade.Sell(InpLots, _Symbol, bid, sl, tp, "GSR14_NY_London_Sell");
            PrintFormat("GSR v14 SELL: Bid=%.3f, SL=%.3f, TP=%.3f, Risk=%.2f, LondonR=%.2f",
                        bid, sl, tp, riskDist, londonRange);
         }
      }
   }
}
//+------------------------------------------------------------------+
