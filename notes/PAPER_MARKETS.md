# PAPER MARKETS — design (yfinance paper trading for LLM seats)

## Goal
Each eligible Ollama seat gets a **paper wallet** and trades against **real** market quotes
(yfinance or similar). No real brokerage. Track P&L over months.

## Data flow
1. Scheduler jobs (America/Chicago, US equities):
   - `paper-open`   ~09:35 CT  (just after open)
   - `paper-mid`    ~12:00 CT
   - `paper-close`  ~15:45 CT  (before close)
2. Job loads: watchlist quotes (yfinance) + each trader wallet/positions snapshot.
3. Brief LLM (one at a time, keep_alive=0 to spare VRAM):
   - market summary (symbols, last, day%%, volume)
   - cash, positions, day P&L
   - Ask: HOLD / BUY / SELL — symbol, shares or $ notional, one-line reason
4. Parser marks proposed trades into `paper_orders` (pending).
5. Fill engine applies last/quote ± slip to `paper_fills` + update wallet (no live broker).
6. Stamp WHI: Ax-PAPER (fills), Tx-PAPER (rejects/parse fail).
7. GUI tile PAPER MARKETS shows wallets + last briefing.

## Tables (proposed)
- paper_wallets(seat, cash, equity, updated_zulu)
- paper_positions(seat, symbol, shares, avg_cost)
- paper_orders(id, zulu, seat, side, symbol, qty, status)
- paper_fills(id, zulu, seat, side, symbol, qty, price)
- paper_briefs(id, zulu, slot, seat, prompt_hash, reply)

## Starting capital (reasonable)
- **$10,000 USD paper** per active trader seat — enough for round lots / ETFs,
  not so large that P&L is noise-free fantasy.
- Optional VIP: qwen3.5:9b gets **$25,000** as flagship book.

## Who should trade (from ollama list)
INCLUDE:
- qwen3.5:9b          flagship book
- llama3-groq-tool-use:8b   tool-ish discipline
- qwen3:8b
- llama3:8b
- nova-commander      style book
- nova-auditor        smaller / risk-aware book ($5k) — critiques size

SKIP (pointless or wrong modality):
- moondream           vision only
- qwen2:0.5b          too small for finance reasoning
- gemma2:2b           weak multi-step
- nova-sentinel       tiny
- llama3.2:3b         thin for allocation
- nova-chronicler     narrative chronicler, not trader
- codellama           code valet — build the platform, do not trade
- phi3:mini           optional later only

## VRAM / memory ponder
Loading many 4–7GB tags + TTS + GUI will thrash. Paper jobs must:
- call **one seat per tick**
- `keep_alive: 0` unload
- never load moondream/codellama for market briefs
- prefer ETF watchlist (SPY QQQ IWM GLD TLT AAPL MSFT) over huge universes

## Stack
- `yfinance` for quotes (open source; rate-limit politely)
- Fill at last price; no options v1
- HIL: no real money path; tile starts `"live": false` until steward flips

## Next build (tomorrow+)
nova/paper.py · sched paper-open/mid/close · deck tile live · /paper slash
