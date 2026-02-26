import torch
from deepseek_vl.models import MultiModalityCausalLM, VLChatProcessor
from PIL import Image
import time

model_path = "/home/aavan/Desktop/Project Files/Vision Language Models/deepseek-vl-1.3b"
print("Loading processor...")
processor = VLChatProcessor.from_pretrained(model_path)
print("Loading model...")
# Use bfloat16 as recommended by deepseek, but we can check if float16 is faster.
model = MultiModalityCausalLM.from_pretrained(model_path, trust_remote_code=True, torch_dtype=torch.bfloat16).cuda().eval()

image = Image.new('RGB', (384, 384), color = 'white')
prompt = "Describe this image in detail."

conversation = [
    {
        "role": "User",
        "content": f"<image_placeholder>{prompt}",
        "images": [image]
    },
    {
        "role": "Assistant",
        "content": ""
    }
]

print("Preparing inputs...")
prepare_inputs = processor(
    conversations=conversation,
    images=[image],
    force_batchify=True
).to(model.device)

inputs_embeds = model.prepare_inputs_embeds(**prepare_inputs)

print("Generating...")
start = time.time()
with torch.no_grad():
    outputs = model.language_model.generate(
        inputs_embeds=inputs_embeds,
        attention_mask=prepare_inputs.attention_mask,
        pad_token_id=processor.tokenizer.eos_token_id,
        bos_token_id=processor.tokenizer.bos_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
        max_new_tokens=200,
        do_sample=False,
        use_cache=True
    )
end = time.time()

print(f"Time taken: {end - start:.2f}s")
answer = processor.tokenizer.decode(outputs[0].cpu().tolist(), skip_special_tokens=False)
print(f"RAW OUTPUT WITH SPECIAL TOKENS:\n{answer}")

# Try the alternative way: using inputs.input_ids (which DeepSeek examples use)
print("\n--- Alternative Generation ---")
with torch.no_grad():
    alt_outputs = model.generate(
        **prepare_inputs,
        pad_token_id=processor.tokenizer.eos_token_id,
        bos_token_id=processor.tokenizer.bos_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
        max_new_tokens=200,
        do_sample=False,
        use_cache=True
    )
print(f"Alt Time: {time.time() - end:.2f}s")
alt_ans = processor.tokenizer.decode(alt_outputs[0].cpu().tolist(), skip_special_tokens=False)
print(f"ALT RAW OUTPUT:\n{alt_ans}")

