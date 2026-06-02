import re
from fastapi import FastAPI, Response
import database

app = FastAPI(title="Free Open-Source Finance Gateway")

CATEGORY_KEYWORDS = {
    "Food & Dining": ["swiggy", "zomato", "starbucks", "restaurant", "grocery", "blinkit", "zepto", "food", "cafe", "dine"],
    "Fuel & Travel": ["petrol", "uber", "ola", "auto", "flight", "diesel", "cab", "irctc", "train"],
    "Rent & Bills": ["rent", "electricity", "wifi", "ebill", "maid", "recharge", "jio", "airtel", "insurance"],
    "Shopping": ["amazon", "myntra", "flipkart", "clothes", "mall", "zara", "ajio"]
}

def rule_based_parse(text: str):
    amounts = re.findall(r'\d+(?:\.\d+)?', text)
    if not amounts:
        return None
    
    amount = float(amounts[0])
    text_lowercase = text.lower()
    
    assigned_category = "Other"
    clean_description = "Unclassified Expense"
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lowercase:
                assigned_category = category
                clean_description = keyword.capitalize()
                break
        if assigned_category != "Other":
            break
            
    if assigned_category == "Other":
        alpha_chunks = re.findall(r'[a-zA-Z]+', text)
        if alpha_chunks:
            clean_description = " ".join(alpha_chunks[:2]).capitalize()
            
    return {
        "amount": amount,
        "category": assigned_category,
        "clean_description": clean_description
    }

# CHANGED: We now accept standard URL query string parameters instead of Form elements
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(Body: str, From: str):
    print(f"\n[Bridge Webhook Ingest] Raw Text: '{Body}'")
    
    parsed = rule_based_parse(Body)
    
    if parsed and parsed["amount"] > 0:
        database.insert_expense(
            sender=From,
            raw_text=Body,
            amount=parsed["amount"],
            category=parsed["category"],
            clean_description=parsed["clean_description"]
        )
        print(f"💾 Logged via Local Bridge: {parsed['clean_description']} | ₹{parsed['amount']}")
    else:
        print("⚠️ Entry skipped: Could not parse numeric amount pattern.")
        
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)