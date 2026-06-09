import re
from fastapi import FastAPI, Response, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
from dateparser.search import search_dates
import os
import sys
from datetime import datetime


# Defensive Import to remain compatible with both local and cloud folder structures
try:
    import database
except ModuleNotFoundError:
    import Personal_Finance_Tracker.database as database

app = FastAPI(title="Cloud Native Finance Gateway")

# Change this to whatever secret string you want. You will type this into Meta's dashboard.
# Update this line in your main.py file
MY_VERIFY_TOKEN = os.environ.get("MY_VERIFY_TOKEN")


CATEGORY_KEYWORDS = {
    "Food & Dining": ["swiggy", "zomato", "starbucks", "restaurant", "grocery", "blinkit", "zepto", "food", "cafe", "dine"],
    "Fuel & Travel": ["petrol", "uber", "ola", "auto", "flight", "diesel", "cab", "irctc", "train"],
    "Rent & Bills": ["rent", "electricity", "wifi", "ebill", "maid", "recharge", "jio", "airtel", "insurance"],
    "Shopping": ["amazon", "myntra", "flipkart", "clothes", "mall", "zara", "ajio"]
}

CREDIT_KEYWORDS = ["salary", "credited", "refund", "cashback", "received", "dividend", "interest", "income"]

def rule_based_parse(text: str):
    """Extract amount, date, category, description, and transaction type (expense/credit)."""

    # 1. Extract date
    extracted_date = None
    date_matches = search_dates(
        text,
        settings={
            "PREFER_DATES_FROM": "past",
            "RELATIVE_BASE": datetime.now(),
            "DATE_ORDER": "DMY"
        }
    )

    if date_matches:
        # Take first detected date
        extracted_date = date_matches[0][1]

    text_lowercase = text.lower()

    # 2. Determine Transaction Type (Credit vs Expense)
    transaction_type = "expense"
    for word in CREDIT_KEYWORDS:
        if word in text_lowercase:
            transaction_type = "credit"
            break

    # 3. Extract amount (Updated regex to handle both income and expenses)
    if transaction_type == "credit":
        amount_match = re.search(
            r'\b(?:credited|received|refund|cashback|income)\s+(\d+(?:\.\d+)?)\b',
            text,
            re.IGNORECASE
        )
    else:
        amount_match = re.search(
            r'\b(?:paid|spent|pay|expense)\s+(\d+(?:\.\d+)?)\b',
            text,
            re.IGNORECASE
        )

    if amount_match:
        amount = float(amount_match.group(1))
    else:
        # Fallback: first number not part of a detected date
        amounts = re.findall(r'\d+(?:\.\d+)?', text)
        if not amounts:
            return None
        amount = float(amounts[0])

    # 4. Assign Category and Description based on Transaction Type
    assigned_category = "Other"
    clean_description = "Unclassified Expense" if transaction_type == "expense" else "Unclassified Credit"

    if transaction_type == "credit":
        assigned_category = "Income"
        # Find which specific keyword matched to use as description
        for word in CREDIT_KEYWORDS:
            if word in text_lowercase:
                clean_description = word.capitalize()
                break
    else:
        # Standard rule-based category matching for expenses
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lowercase:
                    assigned_category = category
                    clean_description = keyword.capitalize()
                    break
            if assigned_category != "Other":
                break

    # Fallback description using text words if still classified as "Other"
    if assigned_category == "Other":
        alpha_chunks = re.findall(r'[a-zA-Z]+', text)
        if alpha_chunks:
            # Exclude basic action keywords to keep descriptions descriptive
            filtered_chunks = [w for w in alpha_chunks if w.lower() not in ['paid', 'spent', 'pay', 'credited', 'received']]
            if filtered_chunks:
                clean_description = " ".join(filtered_chunks[:2]).capitalize()
            else:
                clean_description = " ".join(alpha_chunks[:2]).capitalize()

    return {
        "amount": amount,
        "date": extracted_date.strftime("%Y-%m-%d %H:%M:%S") if extracted_date else None,
        "category": assigned_category,
        "clean_description": clean_description,
        "transaction_type": transaction_type
    }

@app.get("/webhook/whatsapp")
async def verify_meta_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    STEP 1: Meta Handshake Verification.
    Meta fires a GET request to verify this server actually belongs to you.
    """
    if hub_mode == "subscribe" and hub_verify_token == MY_VERIFY_TOKEN:
        print("✅ Meta Webhook successfully verified!")
        return PlainTextResponse(hub_challenge)
    
    print("❌ Webhook verification failed mismatch.")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    STEP 2: Real-time Ingest Pipeline.
    Meta sends an asymmetrical nested JSON document here every time you send a text.
    """
    payload = await request.json()
    
    # Safely navigate Meta's deeply nested payload layout to see if it contains a text message
    try:
        entry = payload.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        message_data = value.get("messages", [])[0]
        
        # Make sure the incoming packet is a text message, not an image or a status update
        if message_data.get("type") == "text":
            body_text = message_data["text"]["body"]
            sender_phone = message_data["from"]
            
            print(f"\n[Cloud Ingest] Text from {sender_phone}: '{body_text}'")
            
            # Execute parsing regex
            parsed = rule_based_parse(body_text)
            
            if parsed and parsed["amount"] > 0:
                database.insert_expense(
                    sender=sender_phone,
                    raw_text=body_text,
                    amount=parsed["amount"],
                    category=parsed["category"],
                    clean_description=parsed["clean_description"],
                    timestamp=parsed["date"],
                    transaction_type=parsed["transaction_type"]
                )
                print(f"💾 Cloud DB Logged: {parsed['clean_description']} | ₹{parsed['amount']}")
            else:
                print("⚠️ Entry skipped: No clear pattern.")
                
    except (IndexError, KeyError, TypeError):
        # Meta sends delivery confirmations ("sent", "delivered", "read") through this exact same endpoint. 
        # If the incoming payload doesn't look like a message text structure, we ignore it safely.
        pass

    # Meta strictly requires an HTTP 200 OK response to confirm you received the message.
    # If you don't return this, Meta will repeatedly send the same text thinking your server is dead.
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)