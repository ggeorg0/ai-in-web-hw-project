import json

from openai import AsyncOpenAI

from ..config import VLLM_URL

PROMPT = (
    "Extract the list of products to buy from the phrase and convert each "
    "product to its basic dictionary form (nominative singular).\n"
    "\n"
    "Examples:\n"
    "Input: купи помидоры и огурцы\n"
    'Output: {"products": ["помидор", "огурец"]}\n'
    "Input: мне нужно молоко, хлеб и яблоки\n"
    'Output: {"products": ["молоко", "хлеб", "яблоко"]}\n'
    "Input: возьми пачку масла и бананы\n"
    'Output: {"products": ["масло", "банан"]}\n'
    "Input: сегодня хорошая погода\n"
    'Output: {"products": []}\n'
    "\n"
    "Now extract products from the user's phrase."
)

JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "products",
        "schema": {
            "type": "object",
            "properties": {"products": {"type": "array", "items": {"type": "string"}}},
            "required": ["products"],
        },
    },
}


async def call_vllm_extract(text: str) -> list[str]:
    client = AsyncOpenAI(
        base_url=f"{VLLM_URL}/v1",
        api_key="not-needed",
    )

    completion = await client.chat.completions.create(
        model="Qwen/Qwen3-0.6B",
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": text},
        ],
        response_format=JSON_SCHEMA,
        max_tokens=512,
    )

    content = completion.choices[0].message.content
    result = json.loads(content)
    return result.get("products", [])
