from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

MODEL_ID = "microsoft/phi-2"

class Phi2LLM:
    def __init__(self):
        print("Loading tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self.tokenizer.pad_token = self.tokenizer.eos_token

        print("Loading Phi-2 model (CPU)...")
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype=torch.float32
        )
        self.model.eval()

    def generate(self, prompt: str, max_tokens: int = 80):
        inputs = self.tokenizer(prompt, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=False,          
                use_cache=False,
                repetition_penalty=1.2,          
                pad_token_id=self.tokenizer.eos_token_id
            )

        generated_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(generated_tokens, skip_special_tokens=True)    

        # return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
