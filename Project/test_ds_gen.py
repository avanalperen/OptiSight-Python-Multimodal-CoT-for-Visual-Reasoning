import torch
from deepseek_vl.models import MultiModalityCausalLM, VLChatProcessor
from PIL import Image

model_path = "/home/aavan/Desktop/Project Files/Vision Language Models/deepseek-vl-1.3b"
processor = VLChatProcessor.from_pretrained(model_path)
model = MultiModalityCausalLM.from_pretrained(model_path, trust_remote_code=True, torch_dtype=torch.bfloat16).cuda()

image = Image.new('RGB', (384, 384), color = 'red')
prompt = "Describe this image"

conversation = [
    {
        "role": "<|User|>",
        "content": f"<image_placeholder>{prompt}",
        "images": [image]
    },
    {
        "role": "<|Assistant|>",
        "content": ""
    }
]

prepare_inputs = processor(
    conversations=conversation,
    images=[image],
    force_batchify=True
).to(model.device)

inputs_embeds = model.prepare_inputs_embeds(**prepare_inputs)

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

answer = processor.tokenizer.decode(outputs[0].cpu().tolist(), skip_special_tokens=True)
print(f"RAW OUTPUT: {answer}")
