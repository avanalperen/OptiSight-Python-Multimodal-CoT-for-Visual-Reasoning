import sys
import torch
import config
import time
from transformers import AutoProcessor
from PIL import Image

try:
    from deepseek_vl.models import VLChatProcessor, MultiModalityCausalLM
    MultiModalityCausalLM._supports_sdpa = True
    
    processor = VLChatProcessor.from_pretrained(config.DEEPSEEK_PATH)
    
    start_load = time.time()
    model = MultiModalityCausalLM.from_pretrained(
        config.DEEPSEEK_PATH,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="cuda",
        attn_implementation="sdpa"
    )
    model.eval()
    print("Model load:", time.time() - start_load)
    
    image = Image.new("RGB", (384, 384), "white")
    conversation = [
        {
            "role": "User",
            "content": "<image_placeholder>describe the image.",
            "images": [image]
        },
        {
            "role": "Assistant",
            "content": ""
        }
    ]
    
    start_prep = time.time()
    for _ in range(5):
        prepare_inputs = processor(
            conversations=conversation,
            images=[image],
            force_batchify=True
        ).to(model.device)
        
        inputs_embeds = model.prepare_inputs_embeds(**prepare_inputs)
        
        start_gen = time.time()
        with torch.no_grad():
            outputs = model.language_model.generate(
                inputs_embeds=inputs_embeds,
                attention_mask=prepare_inputs.attention_mask,
                pad_token_id=processor.tokenizer.eos_token_id,
                bos_token_id=processor.tokenizer.bos_token_id,
                eos_token_id=processor.tokenizer.eos_token_id,
                max_new_tokens=100,
                do_sample=False,
                use_cache=True
            )
        print("Gen loop:", time.time() - start_gen)
    
except Exception as e:
    import traceback
    traceback.print_exc()
