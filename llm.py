import os
from groq import Groq, RateLimitError
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY environment variable not set")

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

_token_log = {"total_tokens": 0, "requests": 0}
def get_token_stats() -> dict:
    return dict(_token_log)

def call_model(model_name, prompt):
    response = client.chat.completions.create(
        model=model_name,
        messages=[{
            "role": "user",
            "content": prompt
        }],
        temperature=0,
    )
    usage = response.usage
    if usage:
        _token_log["total_tokens"] += usage.total_tokens
        _token_log["requests"] += 1
    return response.choices[0].message.content

def generate_answer(prompt):
    try:
        res = call_model("llama-3.3-70b-versatile", prompt)
        return res
    except RateLimitError:
        try:
            res = call_model("llama-3.1-8b-instant", prompt)
            return res
        except RateLimitError:
            return "Service is temporarily busy. Please try again in a few minutes."
    except Exception as e:
        print(f"[LLM] Unexpected error: {e}")
        return f"An error occurred while generating the answer."