import time
import torch
import config
from PIL import Image
from deepseek_vl.models import VLChatProcessor, MultiModalityCausalLM
from transformers import StoppingCriteria, StoppingCriteriaList

MultiModalityCausalLM._supports_sdpa = True

model_path = config.DEEPSEEK_PATH
processor = VLChatProcessor.from_pretrained(model_path)
model = MultiModalityCausalLM.from_pretrained(
    model_path,
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
    device_map="cuda",
    attn_implementation="sdpa"
).eval()

class StoppingCriteriaSub(StoppingCriteria):
    def __init__(self, stops=[], encounters=1):
        super().__init__()
        self.stops = [stop.to(model.device) for stop in stops]

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs):
        for stop in self.stops:
            if input_ids.shape[-1] >= len(stop) and torch.all((stop == input_ids[0][-len(stop):])).item():
                return True
        return False

stop_words = ["<｜end of sentence｜>", "User:", "\nUser", "Assistant:", "User"]
stop_words_ids = [torch.tensor(processor.tokenizer.encode(word, add_special_tokens=False)) for word in stop_words]
stopping_criteria = StoppingCriteriaList([StoppingCriteriaSub(stops=stop_words_ids)])

def test_inference(image_size):
    print(f"\n--- Testing size: {image_size}x{image_size} ---")
    image = Image.new("RGB", (image_size, image_size), "green") # Using green to give it some content type
    
    conversation = [
        {
            "role": "User",
            "content": "<image_placeholder> Describe the image.",
            "images": [image]
        },
        {
            "role": "Assistant",
            "content": ""
        }
    ]
    
    prepare_inputs = processor(
        conversations=conversation,
        images=[image],
        force_batchify=True
    ).to(model.device)
    
    inputs_embeds = model.prepare_inputs_embeds(**prepare_inputs)
    print(f"Inputs Embeds Shape: {inputs_embeds.shape} (Sequence Length: {inputs_embeds.shape[1]})")
    
    start_time = time.time()
    with torch.no_grad():
        outputs = model.language_model.generate(
            inputs_embeds=inputs_embeds,
            attention_mask=prepare_inputs.attention_mask,
            pad_token_id=processor.tokenizer.eos_token_id,
            bos_token_id=processor.tokenizer.bos_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            max_new_tokens=50,
            do_sample=False,
            use_cache=True,
            stopping_criteria=stopping_criteria
        )
    end_time = time.time()
    
    final_response = processor.tokenizer.decode(outputs[0].cpu().tolist(), skip_special_tokens=True).strip()
    if "User:" in final_response:
        final_response = final_response.split("User:")[0].strip()
    if "Assistant:" in final_response:
        final_response = final_response.split("Assistant:")[0].strip()
        
    print(f"Time: {end_time - start_time:.2f}s")
    print(f"Generated ({len(outputs[0])} tokens): {final_response}")

# Warmup
test_inference(384)

# Test real sizes
test_inference(384)
test_inference(224)
test_inference(112)
