from typing import Dict, Tuple, List, Union
import os
import litellm
from pathlib import Path
from textwrap import dedent
from litellm import completion
from joblib import Memory
from difflib import get_close_matches

import tiktoken

from .shared import shared

litellm.drop_params = True


llm_price = {}
for k, v in litellm.model_cost.items():
    llm_price[k] = v

embedding_models = ["openai/text-embedding-3-large",
                    "openai/text-embedding-3-small",
                    "mistral/mistral-embed"]

# steps : price
sd_price = {"15": 0.001,
            "30": 0.002,
            "50": 0.004,
            "100": 0.007,
            "150": 0.01}

tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
llm_cache = Memory(".cache", verbose=0)


def llm_cost_compute(
        input_cost: int,
        output_cost: int,
        price: Tuple[float]) -> float:
    """
    Parameters
    ----------
    input_cost: int
        number of tokens in input messages
    output_cost: int
        number of tokens in completion answer from the LLM
    price: [int, int]
        list with the cost in dollars per 1000 token for in the
        format [input, completion]

    Returns
    -------
    total cost in dollars as a float

    """
    return input_cost * price["input_cost_per_token"] + output_cost * price["output_cost_per_token"]


def tkn_len(message: Union[str, List[Union[str, Dict]], Dict]):
    if isinstance(message, str):
        return len(tokenizer.encode(dedent(message)))
    elif isinstance(message, dict):
        return len(tokenizer.encode(dedent(message["content"])))
    elif isinstance(message, list):
        return sum([tkn_len(subel) for subel in message])


@llm_cache.cache
def chat(
    model: str,
    messages: List[Dict],
    temperature: float,
    check_reason: bool = True,
    **kwargs: Dict,
    ) -> Dict:
    """call to the LLM api. Cached."""
    answer = completion(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=False,
        **kwargs,
    ).json()
    if check_reason:
        assert all(a["finish_reason"] == "stop" for a in answer["choices"]), f"Found bad finish_reason: '{answer}'"
    return answer


def wrapped_model_name_matcher(model: str) -> str:
    "find the best match for a modelname (wrapped to make some check)"
    # find the currently set api keys to avoid matching models from
    # unset providers
    all_backends = list(litellm.models_by_provider.keys())
    backends = []
    for k, v in dict(os.environ).items():
        if k.endswith("_API_KEY"):
            backend = k.split("_API_KEY")[0].lower()
            if backend in all_backends:
                backends.append(backend)
    assert backends, "No API keys found in environnment"

    # filter by providers
    backend, modelname = model.split("/", 1)
    if backend not in all_backends:
        raise Exception(
            f"Model {model} with backend {backend}: backend not found in "
            "litellm.\nList of litellm providers/backend:\n"
            f"{all_backends}"
        )
    if backend not in backends:
        raise Exception(f"Trying to use backend {backend} but no API KEY was found for it in the environnment.")
    candidates = litellm.models_by_provider[backend]
    if modelname in candidates:
        return model
    subcandidates = [m for m in candidates if m.startswith(modelname)]
    if len(subcandidates) == 1:
        good = f"{backend}/{subcandidates[0]}"
        return good
    match = get_close_matches(modelname, candidates, n=1)
    if match:
        return match[0]
    else:
        print(f"Couldn't match the modelname {model} to any known model. "
              "Continuing but this will probably crash further down the code.")
        return model


def model_name_matcher(model: str) -> str:
    """find the best match for a modelname (wrapper that checks if the matched
    model has a known cost and print the matched name)"""
    assert "testing" not in model
    assert "/" in model, f"expected / in model '{model}'"

    out = wrapped_model_name_matcher(model)
    assert out in litellm.model_cost or out.split("/", 1)[1] in litellm.model_cost, f"Neither {out} nor {out.split('/', 1)[1]} found in litellm.model_cost"
    if out != model:
        print(f"Matched modelname '{model}' to '{out}'")
    return out
