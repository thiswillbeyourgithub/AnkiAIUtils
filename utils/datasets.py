import collections
import json
import pandas as pd
import litellm
import random
import numpy as np
from tqdm import tqdm
from joblib import Memory
import re
from typing import Dict, List
from pathlib import Path
from string import punctuation

from rapidfuzz import fuzz
from sklearn.metrics.pairwise import cosine_similarity

from utils.llm import tkn_len

DATASET_SEPARATOR = "----"
DATASET_SEPARATOR_INVALID = re.compile("^-{1,3}[^-]|-{5,}")
assert not re.search(DATASET_SEPARATOR_INVALID, DATASET_SEPARATOR), "Invalid dataset separators"

REG_PUNCT = re.compile("|".join([re.escape(el) for el in list(punctuation)]))

def _embedder(text_list, model_name):
    """compute the emebdding of 1 text"""
    assert isinstance(text_list, list), f"text_list must be list, not {type(text_list)}"

    vec = litellm.embedding(
            model=model_name,
            input=text_list,
            )
    return [np.array(d["embedding"]).squeeze().reshape(1, -1) for d in vec.data]


def load_dataset(
        path: str,
        check_args: Dict = None,
    ) -> Dict:
    """Load and validate a dataset from a text file.

    The dataset file should contain alternating system/user/assistant messages
    separated by '----'. The first message must be a system message, followed by
    user/assistant pairs.

    Parameters
    ----------
    path : str
        Path to the dataset file
    check_args : Dict, optional
        Additional arguments to pass to check_dataset(), by default None

    Returns
    -------
    List
        List of message dictionaries with 'role' and 'content' keys,
        validated according to check_dataset() rules.
        First message is the system message.

    Raises
    ------
    AssertionError
        If dataset format or content is invalid
    """
    if not check_args:
        check_args = {}
    path = Path(path)
    assert path.exists(), f"{path} not found"
    dataset = path.read_text()
    assert dataset, "Empty dataset file"
    assert len(re.split(DATASET_SEPARATOR_INVALID, dataset)) == 1
    dataset = re.split(DATASET_SEPARATOR, dataset)
    assert dataset
    dataset = [d.strip() for d in dataset if d.strip()]  # remove empty

    dataset = [
        {
            "role": "system" if i == 0 else ("user" if i % 2 == 1 else "assistant"),
            "content": content,
        }
        for i, content in enumerate(dataset)
    ]

    check_dataset(dataset, **check_args)

    return dataset

def check_dataset(dataset: List[Dict], must_be_unique: bool = True) -> None:
    """Validate the format and content of a conversation dataset.

    Ensures the dataset follows the expected structure of alternating messages:
    - First message must be a system message
    - Followed by alternating user/assistant messages
    - Minimum 5 elements (1 system prompt + 2 examples)
    - Must have an odd number of messages

    Parameters
    ----------
    dataset : List[Dict]
        List of message dictionaries, each containing 'role' and 'content' keys.
        Roles must be one of: 'system', 'user', 'assistant'
    must_be_unique : bool, optional
        If True, ensures no duplicate prompts appear in questions or answers,
        by default True

    Raises
    ------
    AssertionError
        If any validation check fails:
        - Wrong message order/roles
        - Missing/invalid keys
        - Empty content
        - Duplicate prompts (if must_be_unique=True)
        - Too few messages
    """
    assert dataset[1]["role"] == "user", "Second message is not from user!"
    assert len(dataset) >= 5, (
        f"Dataset contains {len(dataset)} elements, the minimum is 5 "
        "(1 system prompts + 2 examples)"
    )
    assert len(dataset) % 2 == 1, "Even number of examples in dataset"
    for i, d in enumerate(dataset):
        if i == 0:
            assert d["role"] == "system", "First message is not from system!"
        elif i % 2 == 1:
            assert d["role"] == "user", "odd message is not from user!"
        elif i % 2 == 0:
            assert d["role"] == "assistant", "even message is not from assistant!"

    # check undesired keys
    for i, d in enumerate(dataset):
        keys = [k for k in d.keys()]
        for k in keys:
            assert k in ["content", "role"], f"Found key {k} in dataset"
        assert "content" in d
        assert d["content"]
        assert "role" in d
        assert d["role"] in ["system", "user", "assistant"]

    # make sure sure no duplicate
    contents_q = [p["content"] for i, p in enumerate(dataset) if i % 2 == 0]
    contents_a = [p["content"] for i, p in enumerate(dataset) if i % 2 == 1]
    contents = [p["content"] for p in dataset]
    for d in dataset:
        c = d["content"]
        if must_be_unique:
            assert contents_q.count(c) <= 1 and contents_a.count(c) <= 1, f"Prompt appearing multiple times as question or answer (can only once for ech)"
            # in some specific cases the prompts can appear multiple times, such
            # as in illustrator: the sanitizing dataset can have a prompt appearing
            # twice to force the LLM to modify only one fact at a time
        else:
            assert contents.count(c) in [1, 2], f"Prompt appearing more than 2 times: {c}"


def semantic_prompt_filtering(
    curr_mess: Dict,
    max_token: int,
    temperature: float,
    prompt_messages: List[Dict],
    keywords: List[str],
    embedding_model: str,
    verbose: bool = False,
    whi=print,
    yel=print,
    red=print,
    check_args=None
    ) -> List[Dict]:
    """goes through the list of previous prompts of the profile, check
    correctness of the key/values, then returns only what's under the maximum
    number of tokens for model

    Parameters
    ----------
    curr_mess: the prompt to find the closest similarity too
    max_token: threshold of token to not go above
    temperature: the higher the temperature, the less deterministic the filtering becomes
    prompt_messages: list of prompt to filter from
    keywords: list of regex that if match a prompt will increase
        the chance of it being picked
    embedding_model: str
    verbose: bool, default False
    whi, yel, red: coloured printer instances, default print
    check_args: dict, default None
        arguments to pass to check_dataset

    returns
    -------
    The filtered prompt as a list of dict (NOT including the curr_mess)

    """
    if not check_args:
        check_args = {}
    assert isinstance(curr_mess, dict)

    assert max_token >= 500, "max_token should be above 500"
    assert max_token <= 15500, "max_token should be under 15500"
    assert not curr_mess["role"] == "system", "Found system prompt in prompt_filter!"
    assert curr_mess not in prompt_messages, "current message is already in prompt_message"

    check_dataset(prompt_messages)

    # turn list of prompt into list where user/assistant messages are paired
    system_prompt = None
    grouped_pm = []
    for d in prompt_messages:
        if d["role"] == "system":
            system_prompt = d
        elif d["role"] == "user":
            grouped_pm.append([d])
        else:
            grouped_pm[-1].append(d)
    assert all(len(dd) == 2 for dd in grouped_pm)
    assert all(dd[0]["role"] == "user" for dd in grouped_pm)
    assert all(dd[1]["role"] == "assistant" for dd in grouped_pm)
    assert system_prompt

    # count the number of tokens added so far
    tkns = 0
    tkns += tkn_len(curr_mess["content"])
    tkns += tkn_len(system_prompt["content"])
    all_tkns = sum([tkn_len(m["content"]) for m in prompt_messages])

    # score based on keywords:
    if keywords:
        for i, k in enumerate(keywords):
            if isinstance(k, str):
                keywords[i] = re.compile(k, flags=re.DOTALL|re.MULTILINE|re.IGNORECASE)
        max_sim = [0, None]
        min_sim = [1, None]
        for i, pr in enumerate(prompt_messages):
            score = sum([1 if re.search(kw, pr["content"]) else 0 for kw in keywords])
            prompt_messages[i]["kw_score"] = score
            if score > max_sim[0]:
                max_sim[0] = score
                max_sim[1] = pr["content"]
            if score < min_sim[0]:
                min_sim[0] = score
                min_sim[1] = pr["content"]

        # scale from 0 to 1
        for i, pr in enumerate(prompt_messages):
            prompt_messages[i]["kw_score"] = (prompt_messages[i]["kw_score"] - min_sim[0]) / (max_sim[0] - min_sim[0])
    else:
        for i, pr in enumerate(prompt_messages):
            prompt_messages[i]["kw_score"] = 1

    # score based on embedding similarity
    whi("Computing cosine similarity")
    max_sim = [0, None]
    min_sim = [1, None]

    model = embedding_model
    for rep in ["\"", "/", "'", " "]:
        model = model.replace(rep, "")
    mem = Memory(f".cache/embedding_cache/{model}", verbose=0)
    embedder = mem.cache(_embedder)

    to_embed = [curr_mess["content"]]
    to_embed += [pr["content"] for pr in prompt_messages]

    all_embeddings = [embedder(text_list=[e], model_name=embedding_model)[0] for e in to_embed]
    assert all(isinstance(item, np.ndarray) for item in all_embeddings)
    assert len(all_embeddings) == len(prompt_messages) + 1
    new_prompt_vec = all_embeddings.pop(0).squeeze().reshape(1, -1)
    embeddings_contents = all_embeddings[:len(prompt_messages)]
    sim = cosine_similarity(new_prompt_vec, np.array(embeddings_contents).squeeze()).squeeze()

    if verbose:
        max_sim = [sim.max(), prompt_messages[sim.argmax()]["content"]]
        min_sim = [sim.min(), prompt_messages[sim.argmin()]["content"]]
        whi(f"Memory with lowest similarity is: {round(min_sim[0], 4)} '{min_sim[1]}'")
        whi(f"Memory with highest similarity is: {round(max_sim[0], 4)} '{max_sim[1]}'")

    # scaling
    sim -= sim.min()
    sim /= sim.max()
    for i in range(len(prompt_messages)):
        prompt_messages[i]["content_sim"] = float(sim[i].squeeze())
    assert len(prompt_messages) == len(list(sim)), "Unexpected list length"

    # combine score

    w = [
        3,  # embedding similarity score
        1,  # keyword score
        ]
    for i, pr in enumerate(prompt_messages):
        score = pr["content_sim"] * w[0]
        score += pr["kw_score"] * w[1]
        score /= sum(w)
        assert score
        prompt_messages[i]["pick_score"] = score
        assert score >= 0 and score <= 1, f"invalid pick_score: {score}"
    prompt_messages = [pr for pr in prompt_messages if pr]

    # add by decreasing pick score
    picksorted = sorted(prompt_messages, key=lambda x: x["pick_score"], reverse=True)

    output_pr = [system_prompt]  # each picked prompt will be added here

    content_sim = {}
    for pr in prompt_messages:
        content_sim[pr["content"]] = pr["content_sim"]

    exit_while = False
    cnt = 0
    max_iter = 50
    while (not exit_while) and prompt_messages and len(output_pr) < len(prompt_messages):
        cnt += 1
        if cnt >= max_iter:
            red(f"Exited filtering loop after {cnt} iterations, have you added enough memories?")
            exit_while = True
            break

        for pr_idx, pr in enumerate(picksorted):
            if pr in output_pr:
                continue

            # match the prompt to its user/assistant duo
            pair = None
            for p1, p2 in grouped_pm:
                if p1["content"] == pr["content"] and p2 not in output_pr:
                    # we check that p2 and p1 are not already in output_pr
                    # because some datasets allow to have an answer of a
                    # message be also the question of the next message,
                    # for example in illustrator sanitizer. Wether the dataset
                    # contains such duplicate prompts is already checked for
                    # validity in the function check_dataset
                    pair = p2
                elif p2["content"] == pr["content"] and p1 not in output_pr:
                    pair = p1
                if pair is not None:
                    break
            assert pair
            assert pair != pr
            assert pair not in output_pr

            newtknlen = tkn_len(pr["content"]) + tkn_len(pair["content"])
            if tkns + newtknlen >= max_token:
                # will exit while at the end of this loop but not
                # before
                exit_while = True
                break

            # # as the temperature incrase, increase the randomness of the picking
            if temperature > 0:
                if temperature <= 0.3:
                    threshold = 0.05
                else:
                    threshold = temperature - 0.3
                if random.random() >= pr["pick_score"] - threshold:
                    continue

            # keep the most relevant previous memories in the prompt

            tkns += newtknlen
            # add so that the first prompt is always the system prompt
            # and the last prompt pair is always the closest prompt to
            # the user messag
            output_pr.insert(1, pr if pr["role"] == "assistant" else pair)
            output_pr.insert(1, pr if pr["role"] == "user" else pair)
            assert pr in output_pr[1:3]
            assert pair in output_pr[1:3]

        if exit_while:
            break

    if len(output_pr) != len(prompt_messages):
        red(f"Tokens of the kept prompts after {cnt} iterations: {tkns} (of all prompts: {all_tkns} tokens) Number of prompts: {len(output_pr)}/{len(prompt_messages)}")

    # TODO: This complains about duplicates. It looks like for some reason the
    # last one is added as assistant AND user, but we only compare the content.
    contents = [pm["content"] for pm in output_pr]
    dupli = [k for k,v in collections.Counter(contents).items() if v>1]
    if dupli:
        raise Exception(f"{len(dupli)} duplicate prompts found in memory.py: {dupli}")

    # Keep only the content and the role keys for each prompt
    new_output = [{k: v for k, v in pk.items() if k in {"content", "role"}} for pk in output_pr]

    assert curr_mess not in new_output
    assert new_output, "No prompt were selected!"
    check_dataset(new_output, **check_args)

    return new_output


def format_anchor_key(key: str) -> str:
    """turn anchor keys like "lupus" into "flashcard about {{c1::lupus}}"
    to increase the chances of it matching."""
    return "TOPIC: '" + key + "'"


def load_and_embed_anchors(path: str, model: str):
    """
    Load the memory anchors.

    At the end we have:
    anchors:
        a dict where each key/val are straight from the json,
        except for __COMMENT keys that are used for easier manual
        editing of the file.
        An example of key/value would be:
            "lupus / lupus erythematosus": "a wolf"
    embeddings:
        a pandas dataframe where the index is made of keys + subkeys.
        Subkeys are the key from the json but split at " / "
        Hence we have in the index "lupus", "lupus erythematosus",
        "lupus / lupus erythematosus".
        The columns contain the vector for "a wolf". A column "Anchor" contains
        also the value "a wolf" (used for deduplicating matching anchors).
        Hence, we have many chances at selecting the best anchors

    the matchig subset of anchors are what are sent to the LLM, embeddings
    are just use in the backend to identify the relevant anchors. Hence
    why subkeys appear in embeddings.index but not as keys of anchors.

    """
    path = Path(path)
    assert path.exists(), f"Anchor file not found: {path}"
    content = path.read_text()
    assert content, "Empty anchor file"

    embeddings = {}
    mem = Memory(f".cache/embedding_cache/{model}", verbose=0)
    embedder = mem.cache(_embedder)

    try:
        temp_anchors = json.loads(content)
    except Exception as err:
        raise Exception(f"Failed to load json anchor: {err}")

    # embed all key patterns
    anchors = {}
    for key, val in temp_anchors.items():
        if key == "__COMMENT":
            continue
        assert not key.startswith("__"), (
            f"This key seems odd: {key}")
        anchors[key] = val
    assert len(list(anchors.values())) == len(set(list(anchors.values()))), (
        "found dulicate values in anchors")

    index = []
    values = []
    for k, v in anchors.items():
        for kk in k.split("/"):  # add subkeys too
            index.append(kk.strip())
            values.append(v)
    if len(index) != len(set(index)):
        dup = [i for i in index if index.count(i) > 1]
        raise Exception(f"Found duplicate index in anchor: {','.join(dup)}")
    assert len(index) >= len(anchors)

    data = [
        embedder(
            text_list=[format_anchor_key(ind)],
            model_name=model
        )[0] for ind in tqdm(index, desc="Embedding anchors", unit="key")
    ]
    assert len(data) == len(index)
    assert max(data[0].shape) > 100
    data = np.array(data).squeeze()

    df = pd.DataFrame(
        index=index,
        columns=[f"V_{i+1}" for i in range(data[0].squeeze().shape[0])],
        data=data
    )
    df["Anchor"] = values
    assert len(index) == data.shape[0]
    return anchors, df


def preprocess_text(text: str) -> str:
    "text preprocessor for fuzzy_finding"
    return re.sub(REG_PUNCT, "", text).lower().strip().replace("é", "e")


def fuzzy_included(
    key: str,
    corpus: str,
    threshold: int = 80
        ) -> bool:
    """Check if a key is approximately contained within a corpus text.

    Uses fuzzy string matching to determine if the key appears in the corpus,
    accounting for minor variations. The matching score is adjusted based on
    length differences between the key and corpus.

    Parameters
    ----------
    key : str
        The string pattern to search for
    corpus : str
        The text to search within
    threshold : int, optional
        Minimum adjusted similarity score (0-100) required to consider a match,
        by default 80

    Returns
    -------
    bool
        True if the key is found in the corpus with sufficient similarity,
        False otherwise

    Notes
    -----
    The actual matching score is adjusted by subtracting half a point for each
    character difference in length between the key and corpus. This helps
    prevent false positives from very short keys matching long corpus segments.
    """
    score = fuzz.partial_ratio(key, corpus)
    length_difference = abs(len(key) - len(corpus))
    adjusted_score = score - (length_difference * 0.5)
    return adjusted_score >= threshold


def filter_anchors(
    n: int,
    content: str,
    anchors: Dict,
    embeddings: pd.DataFrame,
    model: str,
    ) -> List[List]:
    """Find the most relevant anchor pairs for a given content.

    First checks for exact or fuzzy matches of anchor keys in the content.
    Then uses embedding similarity to find additional relevant anchors
    up to the requested number.

    Parameters
    ----------
    n : int
        Number of anchor pairs to return
    content : str
        The text to find relevant anchors for
    anchors : Dict
        Dictionary of anchor key/value pairs
    embeddings : pd.DataFrame
        DataFrame containing pre-computed embeddings for anchor keys,
        with index being keys/subkeys and columns being embedding vectors
        plus an 'Anchor' column with the anchor values
    model : str
        Name of the embedding model to use for similarity comparison

    Returns
    -------
    List[List]
        List of [key, value] pairs for the most relevant anchors.
        Length will be at most n.
        Keys may be either full compound keys ("key1 / key2")
        or individual subkeys, depending on best match.

    Notes
    -----
    The function first looks for exact or fuzzy matches of anchor keys
    in the content. If fewer than n matches are found, it uses
    embedding similarity to find additional relevant anchors.
    Duplicate anchor values are deduplicated, keeping the most specific key.
    """
    pcontent = preprocess_text(content)
    embed_index = embeddings.index.tolist()
    embed_text = embeddings["Anchor"]
    embeddings = embeddings.drop(columns=["Anchor"])

    # check if the key is already present by chance to make sure to include it
    found_keys = []
    for ind in embed_index:
        ind_orig = ind
        ind = preprocess_text(ind)

        if ind in pcontent:
            found_keys.append(ind_orig)
            break
        elif fuzzy_included(ind, pcontent):
            found_keys.append(ind_orig)
            break
    assert len(found_keys) <= 2 * n, f"Found {len(found_keys)} matching anchors so something went probably wrong"
    assert len(set(found_keys)) == len(found_keys), "Found duplicate keys?"

    # found_keys can contain either keys or subkeys so we need to deduplicate
    # those that have the same value in anchors (meaning the same embeddings)
    keep = []
    val_so_far = []
    for keyorsubkey in found_keys:
        val = embed_text.loc[keyorsubkey]
        if val not in val_so_far:
            keep.append(keyorsubkey)
            val_so_far.append(val)
        elif "/" in keyorsubkey:
            keep[val_so_far.index(val)] = keyorsubkey
    found_keys = keep

    if len(found_keys) >= n:
        val_so_far = [anchors[k] for k in found_keys]
        assert len(val_so_far) == len(set(val_so_far)), "duplicate values in anchors"
        return [[k, v] for k, v in zip(found_keys, val_so_far)]

    n = n - len(found_keys)
    assert n > 0

    mem = Memory(f".cache/embedding_cache/{model}", verbose=0)
    embedder = mem.cache(_embedder)

    vec = embedder(text_list=[content], model_name=model)[0]

    sim = cosine_similarity(vec, embeddings.values.squeeze()).squeeze()

    assert sim.shape[0] == len(embeddings)

    for ind in sim.argsort():
        keyorsubkey = embed_index[ind]
        val = embed_text.loc[keyorsubkey]
        if val not in val_so_far:
            found_keys.append(keyorsubkey)
            val_so_far.append(val)
        elif "/" in keyorsubkey:
            found_keys[val_so_far.index(val)] = keyorsubkey

    assert len(val_so_far) == len(set(val_so_far)), "duplicate values in anchors"

    # reverse
    val_so_far = val_so_far[::-1]
    found_keys = found_keys[::-1]

    val_so_far = val_so_far[:n]
    found_keys = found_keys[:n]
    out = [[k, v] for k, v in zip(found_keys, val_so_far)]
    return out
