"""
llm/phi3.py
-----------
mlx-lm wrapper for microsoft/Phi-3-mini-4k-instruct.

Exposes the same .generate(prompt, max_tokens) -> str interface
as the old Phi2LLM, so callers only need an import swap.

The chat-template is applied internally: callers pass a plain
instruction string; this class wraps it into Phi-3's system/user
message format before calling mlx_lm.generate().
"""

from mlx_lm import load, generate

MODEL_ID = "mlx-community/Phi-3-mini-4k-instruct-4bit"

SYSTEM_PROMPT = (
    "You are a concise welfare eligibility assistant. "
    "Given structured information about an applicant and a scheme evaluation, "
    "write a single short sentence (max 30 words) explaining the eligibility decision. "
    "Do not repeat the rules. Do not add caveats. Just state the outcome clearly."
)


class Phi3LLM:
    def __init__(self):
        print(f"Loading {MODEL_ID} via mlx-lm...")
        self.model, self.tokenizer = load(MODEL_ID)
        print("Model ready.\n")

    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        """
        Wrap `prompt` in Phi-3's chat template and generate a completion.

        Args:
            prompt:     The instruction / user message string.
            max_tokens: Maximum number of new tokens to generate.

        Returns:
            The generated text string (input prompt excluded).
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]

        # Apply Phi-3's chat template to get the full formatted string
        formatted = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        response = generate(
            self.model,
            self.tokenizer,
            prompt=formatted,
            max_tokens=max_tokens,
            verbose=False,
        )

        return response.strip()
