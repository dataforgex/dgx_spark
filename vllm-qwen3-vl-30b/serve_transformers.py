#!/usr/bin/env python3
"""
Transformers-based server for Qwen3-VL-30B
Simple FastAPI server with OpenAI-compatible endpoints
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import torch
from transformers import AutoProcessor
from PIL import Image
import io
import base64
import uvicorn
import json
import logging
from qwen_vl_utils import process_vision_info

# Import the specific model class for Qwen3VL MoE
try:
    from transformers import Qwen3VLMoeForConditionalGeneration
except ImportError:
    from transformers import AutoModel
    Qwen3VLMoeForConditionalGeneration = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Qwen3-VL-30B Server", version="1.0.0")

# Global model and processor
model = None
processor = None
MODEL_NAME = "Qwen/Qwen3-VL-30B-A3B-Instruct"

# Request models
class Message(BaseModel):
    role: str
    content: str | List[Dict[str, Any]]

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

class CompletionRequest(BaseModel):
    model: str
    prompt: str
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7

@app.on_event("startup")
async def load_model():
    """Load model on startup"""
    global model, processor
    
    logger.info(f"Loading model: {MODEL_NAME}")
    logger.info("This may take several minutes...")
    
    try:
        # Load processor
        processor = AutoProcessor.from_pretrained(
            MODEL_NAME,
            trust_remote_code=True
        )
        logger.info("✓ Processor loaded")
        
        # Load model with device_map="auto" for automatic GPU placement
        # Use the specific model class for generation
        if Qwen3VLMoeForConditionalGeneration is not None:
            ModelClass = Qwen3VLMoeForConditionalGeneration
        else:
            # Fallback to using trust_remote_code to get the right class
            from transformers import AutoModelForCausalLM
            ModelClass = AutoModelForCausalLM

        try:
            # Try with flash attention first
            model = ModelClass.from_pretrained(
                MODEL_NAME,
                torch_dtype=torch.bfloat16,
                device_map="auto",
                trust_remote_code=True,
                attn_implementation="flash_attention_2"
            )
            logger.info("Using Flash Attention 2")
        except Exception as e:
            logger.warning(f"Flash attention not available, using default: {e}")
            model = ModelClass.from_pretrained(
                MODEL_NAME,
                torch_dtype=torch.bfloat16,
                device_map="auto",
                trust_remote_code=True
            )
        logger.info("✓ Model loaded successfully")
        logger.info(f"Model device: {model.device}")
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Qwen3-VL-30B Server",
        "model": MODEL_NAME,
        "status": "ready" if model is not None else "loading"
    }

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)"""
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "created": 1234567890,
                "owned_by": "qwen"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Chat completion endpoint (OpenAI-compatible)"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    try:
        # Extract messages
        messages = [msg.dict() for msg in request.messages]

        # Apply chat template
        text = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # Process vision info if present
        image_inputs, video_inputs = process_vision_info(messages)

        # Prepare inputs
        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            return_tensors="pt",
            padding=True
        )
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                do_sample=request.temperature > 0,
                pad_token_id=processor.tokenizer.pad_token_id
            )
        
        # Decode only the newly generated tokens (not the input)
        # This avoids issues with special token stripping changing text length
        new_token_ids = outputs[0, inputs["input_ids"].shape[1]:]
        response_text = processor.decode(
            new_token_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        ).strip()
        
        return {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": inputs["input_ids"].shape[1],
                "completion_tokens": outputs.shape[1] - inputs["input_ids"].shape[1],
                "total_tokens": outputs.shape[1]
            }
        }
        
    except Exception as e:
        logger.error(f"Error in chat completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/completions")
async def completions(request: CompletionRequest):
    """Text completion endpoint (OpenAI-compatible)"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    try:
        # Prepare inputs
        inputs = processor(
            text=[request.prompt],
            return_tensors="pt",
            padding=True
        )
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                do_sample=request.temperature > 0,
                pad_token_id=processor.tokenizer.pad_token_id
            )
        
        # Decode
        generated_text = processor.batch_decode(
            outputs,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )[0]
        
        return {
            "id": "cmpl-123",
            "object": "text_completion",
            "created": 1234567890,
            "model": request.model,
            "choices": [
                {
                    "text": generated_text,
                    "index": 0,
                    "finish_reason": "stop"
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy" if model is not None else "loading",
        "model_loaded": model is not None
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8102, help="Port to bind to")
    args = parser.parse_args()
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )
