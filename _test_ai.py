import os
from dotenv import load_dotenv
load_dotenv(".env", override=True)
from FlaskWebProject1.ai_service import _call_chat, is_enabled
print("enabled:", is_enabled())
from FlaskWebProject1.ai_service import chat
r = chat("What words are prohibited?", "", "Demo Brand (BrandGuard Sample)", "prohibited_term: cheap (severity: high)")
print("chat result:", r)