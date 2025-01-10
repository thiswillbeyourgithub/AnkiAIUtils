"""
A tool for reformulating Anki flashcards using LLMs while preserving their structure.

This module provides functionality to:
- Reformulate flashcard content while preserving cloze deletions
- Reset cards back to their original state
- Track changes and costs in a SQLite database
"""
import copy
import time
import datetime
import fire
import re
from textwrap import dedent
import rtoml
import sqlite3
from tqdm import tqdm
import json
import zlib
from pathlib import Path
from typing import List, Dict
from inspect import signature
import traceback
import sys
import faulthandler
import pdb

from rapidfuzz.fuzz import ratio as levratio
from joblib import Parallel, delayed
import pandas as pd
import litellm

from utils.misc import load_formatting_funcs, replace_media
from utils.llm import llm_price, tkn_len, chat, model_name_matcher
from utils.anki import anki, sync_anki, addtags, removetags, updatenote
from utils.logger import create_loggers
from utils.datasets import load_dataset, semantic_prompt_filtering
from utils.cloze_utils import iscloze, getclozes

Path("databases").mkdir(exist_ok=True)
REFORMULATOR_DIR = Path("databases/reformulator")
REFORMULATOR_DIR.mkdir(exist_ok=True)


# logger
log_file = REFORMULATOR_DIR / "reformulator_logs.txt"
Path(log_file).touch()
whi, yel, red = create_loggers(log_file, ["white", "yellow", "red"])

# get today's date for the logging and tags
d = datetime.datetime.today()
today = f"{d.day:02d}_{d.month:02d}_{d.year:04d}"


# status string
STAT_CHANGED_CONT = "Content has been changed"
STAT_OK_RESET = "OK to reset"
STAT_OK_REFORM = "OK to reformulate"


class AnkiReformulator:
    VERSION = "1.0"

    def __init__(
        self,
        query: str = None,
        dataset_path: str = None,
        main_field_index: int = 0,
        mode: str = "reformulate",
        exclude_done: bool = True,
        exclude_version: bool = True,
        exclude_media: bool = False,
        confirm_edited_reset: bool = True,
        # llm: str = "anthropic/claude-3-5-sonnet-20240620",
        llm: str = "openrouter/anthropic/claude-3.5-sonnet:beta",
        # embedding_model: str = "mistral/mistral-embed",
        embedding_model: str = "openai/text-embedding-3-small",
        max_token: int = 4000,
        llm_temp: int = 0,
        string_formatting: str = None,
        n_note_limit: int = 1000,
        tkn_warn_limit: int = 100_000,
        parallel: int = 4,
        verbose: bool = False,
        print_db_then_exit: bool = False,
        debug: bool = False,
    ) -> None:
        """

        Parameters
        ----------

        query: str
            the anki query to use to fetch the notes.

        dataset_path: str
            path to a dataset text file where the delimiter is '----'. Each cell while
            be treated as a note. For each pair of cell, the first must contain
            the flashcard to reformulate and the second must contain the reforumated.

        main_field_index: int, default 0
            index of the field to edit. For example 0 if you want to reformulate the first field of the card

        mode: str, default 'reformulate'
            either 'reformulate' or 'reset' to load back the content of the flashcard before
            reformulation.

        exclude_done: bool, default True
            exclude notes with tag AnkiReformulator::Done::*
            Only applies in mode=="reformulate"

        exclude_version: bool, default True
            exclude notes with the current version mentionned in the
            AnkiReformulator field.
            Only applies in mode=="reformulate"

        exclude_media: bool, default False
            If True, will exclude any note that contains in the main field:
                * an image (<img...)
                * or a sound [sound:...
                * or a link href / http
            This is because:
                1 as LLMs are non deterministic I preferred
                    to avoid taking the risk of botching the content
                2 it was easier to code at the start
                3 it costs less token

            Nowadays, I implemented a regex replacement that first replaces
            each media by a simple string like [IMAGE1] and check if it's
            indeed present in the output of the LLM then replace it back.
            This is what happens if False.

        confirm_edited_reset: bool, default True
            if you use mode='reset' and a note has been changed since
            it was reformulated and confirm_edited_reset is True, then will
            ask for what to do for those cards.
            If false those cards will not be reset and be tagged
            'AnkiReformulator::ChangedContent'

        llm: str, default "anthropic/claude-3-5-sonnet-20240620"
            LLM to use, in litellm format (meaning you specify the backend before the /)

        embedding_model: str, default "openai/text-embedding-3-small"
            embedding model to use

        max_token: int, default 4000
            max number of token per query

        llm_temp: float, default 0

        string_formatting: str, default None
            path to a python file declaring functions to specify specific
            formatting.

            In reformulator, functions that can be loaded are:
            - "cloze_input_parser"
            - "cloze_output_parser"
            both taking a unique string argument and returning a unique string.

            They will then replace the function declared in utils/cloze_utils.

        n_note_limit: int, default 1000
            if the number of notes to process is higher, raise an Error

        tkn_warn_limit: int, default 100_000
            if the number of token in the cards to process is above, raise an Error

        parallel: bool, default 4
            Only used if mode is 'reformulate'. 1 to disable multithreading

        verbose: bool, default False

        print_db_then_exit: bool, default False

        debug: bool, default False
            if True, a console will be opened on exceptions
        """
        if debug:
            def handle_exception(exc_type, exc_value, exc_traceback):
                """Custom exception handler that opens pdb on non-keyboard interrupts."""
                if not issubclass(exc_type, KeyboardInterrupt):
                    [print(line) for line in traceback.format_tb(exc_traceback)]
                    print(str(exc_value))
                    print(str(exc_type))
                    print("\n--debug was used so opening debug console at the "
                      "appropriate frame. Press 'c' to continue to the frame "
                      "of this print.")
                    pdb.post_mortem(exc_traceback)
                    print("You are now in the exception handling frame.")
                    breakpoint()
                    sys.exit(1)

            sys.excepthook = handle_exception
            faulthandler.enable()

        if print_db_then_exit:
            db_content = self.load_db()
            if not db_content:
                red("Empty database.")
            else:
                print(json.dumps(db_content, ensure_ascii=False, indent=4))
            return
        else:
            sync_anki()
            assert query is not None, "Must specify --query"
            assert dataset_path is not None, "Must specify --dataset_path"
        litellm.set_verbose = verbose

        # arg sanity check and storing
        assert "note:" in query, f"You have to specify a notetype in the query ({query})"
        assert mode in ["reformulate", "reset"], "Invalid value for 'mode'"
        assert isinstance(exclude_done, bool), "exclude_done must be a boolean"
        assert isinstance(exclude_version, bool), "exclude_version must be a boolean"
        assert isinstance(exclude_media, bool), "exclude_media must be a boolean"
        self.exclude_media = exclude_media
        assert isinstance(confirm_edited_reset, bool), "confirm_edited_reset must be a boolean"
        assert str(main_field_index).isdigit(), "main_field_index must be an int"
        if str(parallel) == -1:
            parallel = -1
        else:
            assert str(parallel).isdigit(), "parallel must be an int or -1"
            parallel = int(parallel)
        main_field_index = int(main_field_index)
        assert main_field_index >= 0, "invalid field_index"
        self.base_query = query
        self.dataset_path = dataset_path
        self.mode = mode
        self.exclude_done = exclude_done
        self.exclude_version = exclude_version

        if string_formatting:
            red(f"Loading specific string formatting from {string_formatting}")
            cloze_input_parser, cloze_output_parser = load_formatting_funcs(
                    path=string_formatting,
                    func_names=["cloze_input_parser", "cloze_output_parser"]
            )
            for func in [cloze_input_parser, cloze_output_parser]:
                params = dict(signature(func).parameters)
                assert len(params.keys()) == 1, f"Expected 1 argument for {func}"
                assert "cloze" in params, f"{func} must have 'cloze' as argument"
        else:
            from utils.cloze_utils import cloze_input_parser, cloze_output_parser
        self.cloze_input_parser = cloze_input_parser
        self.cloze_output_parser = cloze_output_parser

        self.llm = llm
        self.embedding_model = embedding_model
        self.field_index = main_field_index
        self.confirm_edited_reset = confirm_edited_reset
        self.llm_temp = llm_temp
        assert max_token >= 1000, "You should not set max_token to less than 1000"
        self.max_token = max_token
        if llm in llm_price:
            self.price = llm_price[llm]
        elif llm.split("/", 1)[1] in llm_price:
            self.price = llm_price[llm.split("/", 1)[1]]
        elif model_name_matcher(llm) in llm_price:
            self.price = llm_price[model_name_matcher(llm)]
        else:
            raise Exception(f"{llm} not found in llm_price")
        self.verbose = verbose

    def reformulate(self):
        query = self.base_query
        if self.mode == "reformulate":
            if self.exclude_done:
                query += " -AnkiReformulator::Done::*"

            if self.exclude_version:
                query += f" -AnkiReformulator:\"*version*=*'{self.VERSION}'*\""

        # load db just in case, and create one if it doesn't already exist
        self.db_content = self.load_db()
        if not self.db_content:
            red("Empty database. If you have already ran anki_reformulator "
                "before then something went wrong!")
            whi("Creating a empty database")
            self.save_to_db({})
            self.db_content = self.load_db()
            assert self.db_content, "Could not create database"

        whi("Computing estimated costs")
        self.compute_cost(self.db_content)

        # load dataset
        whi("Loading dataset")
        dataset = load_dataset(self.dataset_path)
        # check that each note is valid but exclude the system prompt, which is
        # the first entry
        for id, d in enumerate(dataset[1:]):
            dataset[id]["content"] = self.cloze_input_parser(d["content"]) if iscloze(d["content"]) else d["content"]
        assert len(dataset) % 2 == 1, "Even number of examples in dataset"
        self.dataset = dataset

        # if any note contains RESETTING or DOING, tell the user
        nids = anki(action="findNotes",
                    query="tag:AnkiReformulator::RESETTING")
        if nids:
            red(f"Found {len(nids)} notes with tag AnkiReformulator::RESETTING : {nids}")
        nids = anki(action="findNotes", query="tag:AnkiReformulator::DOING")
        if nids:
            red(f"Found {len(nids)} notes with tag AnkiReformulator::DOING : {nids}")

        # find notes ids for the specific note type
        nids = anki(action="findNotes", query=query)
        assert nids, f"No notes found for the query '{query}'"

        # find the field names for this note type
        fields = anki(action="notesInfo",
                      notes=[int(nids[0])])[0]["fields"]
        assert "AnkiReformulator" in fields.keys(), \
                "The notetype to edit must have a field called 'AnkiReformulator'"
        try:
            self.field_name = list(fields.keys())[self.field_index]
        except IndexError:
            raise AssertionError(f"main_field_index {self.field_index} is invalid. "
                                 f"Note only has {len(fields.keys())} fields!")

        if self.exclude_media:
            # now find notes ids after excluding the img in the important field
            query += f' -{self.field_name}:"*<img*"'
            # also exclude sounds
            query += f' -{self.field_name}:"*[sound:*"'
            # and links
            query += f' -{self.field_name}:"*http://*"'
            query += f' -{self.field_name}:"*https://*"'

        whi(f"Query to find note: '{query}'")
        nids = anki(action="findNotes", query=query)
        assert nids, f"No notes found for the query '{query}'"
        whi(f"Found {len(nids)} notes")

        # retrieve cards info
        self.notes = pd.DataFrame(
            anki(action="notesInfo", notes=nids)
        ).set_index("noteId")
        self.notes = self.notes.loc[nids]
        assert not self.notes.empty, "Empty notes"

        assert len(set(self.notes["modelName"].tolist())) == 1, \
                "Contains more than 1 note type"

        # check absence of image and sounds in the main field
        # as well as incorrect tags
        for nid, note in self.notes.iterrows():
            if self.exclude_media:
                _, media = replace_media(
                    content=note["fields"][self.field_name]["value"],
                    media=None,
                    mode="remove_media")
                assert not media, f"Found media in nid:{nid}: {media} in {_}"

            for tag in note["tags"]:
                if tag.startswith("AnkiReformulator"):
                    assert "::" in tag
                    if "_" not in tag:
                        assert "AnkiReformulator::Done" not in tag
                        assert tag in [
                                "AnkiReformulator::TODO",
                                "AnkiReformulator::FAILED",
                        ]
                        assert tag not in [
                            "AnkiReformulator::RESETTING",
                            "AnkiReformulator::DOING",
                        ], f"Found tag indicated an error hapenned in a previous run: {tag}\nnid:{nid}\nnote: '{note}'"
                else:
                    assert not tag.lower().startswith("ankireformulator")

        # check if required tokens are higher than our limits
        tkn_sum = sum(tkn_len(d["content"]) for d in self.dataset)
        tkn_sum += sum(tkn_len(replace_media(content=note["fields"][self.field_name]["value"],
                                             media=None,
                                             mode="remove_media")[0])
                       for _, note in self.notes.iterrows())
        assert tkn_sum <= tkn_warn_limit, (f"Found {tkn_sum} tokens to process, which is "
                                           f"higher than the limit of {tkn_warn_limit}")

        assert len(self.notes) <= n_note_limit, (f"Found {len(self.notes)} notes to process "
                                                 f"which is higher than the limit of {n_note_limit}")

        if self.mode == "reformulate":
            func = self.reformulate_note
        elif self.mode == "reset":
            func = self.reset_note
        else:
            raise ValueError(f"Unknown mode {self.mode}")

        def error_wrapped_func(*args, **kwargs):
            """Wrapper that catches exceptions and marks failed notes with appropriate tags."""
            try:
                return func(*args, **kwargs)
            except Exception as err:
                addtags(nid=note.name, tags="AnkiReformulator::FAILED")
                red(f"Error when running self.{func.__name__}: '{err}'")
                return str(err)

        # getting all the new values in parallel and using caching
        new_values = Parallel(
            backend="threading",
            n_jobs=parallel,
        )(
            delayed(error_wrapped_func)(nid, note)
            for nid, note in tqdm(
                self.notes.iterrows(),
                total=len(self.notes),
                desc="Processing notes"
            )
        )

        failed_runs = [self.notes.iloc[i_nv]
                       for i_nv in range(len(new_values))
                       if isinstance(new_values[i_nv], str)]
        if failed_runs:
            red(f"Found {len(failed_runs)} failed notes")
            failed_run_index = pd.DataFrame(failed_runs).index
            self.notes.drop(index=failed_run_index, inplace=True)
            new_values = [nv for nv in new_values if isinstance(nv, dict)]
            assert not self.notes.empty, "All notes failed!"
            assert len(new_values) == len(self.notes)

        # applying the changes
        whi("Applying changes")
        for values in tqdm(new_values, desc="Applying changes to anki"):
            if self.mode == "reformulate":
                self.apply_reformulate(values)
            elif self.mode == "reset":
                self.apply_reset(values)
            else:
                raise ValueError(self.mode)

        whi("Clearing unused tags")
        anki(action="clearUnusedTags")

        # TODO: Why add and them remove them?
        # add and remove the tag TODO to make it easier to re add by the user
        # as it was cleared by calling 'clearUnusedTags'
        nid, note = next(self.notes.iterrows())
        addtags(nid, tags="AnkiReformulator::TODO")
        removetags(nid, tags="AnkiReformulator::TODO")

        sync_anki()

        # display the total cost again at the end
        db = self.load_db()
        assert db, "Empty database at the end of the run. Something went wrong?"
        self.compute_cost(db)

    def compute_cost(self, db_content: List[Dict]) -> None:
        """Sum the dollar cost of each cards processed in
        $REFORMULATOR_DIR/reformulator.db
        This is used to know if something went wrong.
        """
        n_db = len(db_content)
        red(f"Number of entries in databases/reformulator/reformulator.db: {n_db}")
        dol_costs = []
        dol_missing = 0
        for dic in db_content:
            if self.mode != "reformulate":
                continue
            try:
                dol = float(dic["dollar_price"])
                dol_costs.append(dol)
            except Exception:
                dol_missing += 1
        if dol_costs:
            dol_total = sum(dol_costs)
            red(f"Total cost: ${dol_total:.4f}")
            dol_mean = dol_total / len(dol_costs)
            red(f"Mean cost: ${dol_mean:.4f}")
        # if dol_missing:
        if dol_missing > 0.1 * len(dol_costs):
            red(f"Number of missing dollar cost of entries: {dol_missing}")
        # else:
        #     whi("No missing dollar cost of entry found")
        if hasattr(self, "_cost_so_far"):
            red(f"Cost of this run: ${dol_total-self._cost_so_far:.2f}")
        elif dol_costs:
            self._cost_so_far = dol_total

    def reformulate_note(self, nid: int, note: pd.Series) -> Dict:
        """Generate a reformulated version of a note's content using an LLM.

        Parameters
        ----------
        nid : int
            Note ID from Anki
        note : pd.Series
            Row from the notes DataFrame containing the note data

        Returns
        -------
        Dict
            Log dictionary containing the reformulation results and metadata
        """
        nid = int(nid)
        log = {
            "nid": nid,
            "mode": self.mode,
            "date": today,
            "version": self.VERSION,
            "timestamp": time.time(),
            "llm_model": self.llm,
            "llm_temp": self.llm_temp,
            "status": None,
        }

        # reformulate the content
        content = note["fields"][self.field_name]["value"]
        log["note_field_content"] = content
        formattedcontent = self.cloze_input_parser(content)
        log["note_field_formattedcontent"] = formattedcontent

        # if the card is in the dataset, just take the dataset value directly
        skip_llm = False
        for i, d in enumerate(self.dataset):
            fc2 = ""  # also check with media replaced
            fc3 = ""
            try:
                fc2 = replace_media(
                    content=formattedcontent,
                    media=None,
                    mode="remove_media")[0]
                fc3 = self.cloze_input_parser(fc2) if iscloze(fc2) else fc2
            except:
                pass

            if d["content"] in [formattedcontent, fc2, fc3]:
                if d["role"] == "assistant":
                    newcontent = d["content"]
                elif d["role"] == "user":
                    newcontent = self.dataset[i + 1]["content"]
                else:
                    raise ValueError(f"Unexpected role of message in dataset: {d}")
                skip_llm = True
                break

        fc, media = replace_media(
            content=formattedcontent,
            media=None,
            mode="remove_media")
        log["media"] = media

        if skip_llm:
            log["llm_answer"] = {"Skipped": True}
            log["dollar_price"] = 0
        else:
            dataset = copy.deepcopy(self.dataset)
            curr_mess = [{"role": "user", "content": fc}]
            dataset = semantic_prompt_filtering(
                curr_mess=curr_mess[0],
                max_token=self.max_token,
                temperature=0,
                prompt_messages=dataset,
                keywords="",
                embedding_model=self.embedding_model,
                whi=whi,
                yel=yel,
                red=red)
            dataset += curr_mess

            assert dataset[0]["role"] == "system", "First message is not from system!"
            assert dataset[1]["role"] == "user", "Second message is not from user!"
            assert (
                dataset[-2]["role"] == "assistant"
            ), "Penultimate message is not from assistant!"
            assert dataset[-1]["role"] == "user", "Last message is not from user!"
            assert len(dataset) % 2 == 0, "Number of message is not even!"

            tkn_sum = sum([tkn_len(p["content"]) for p in dataset])
            assert tkn_sum < self.max_token, (
                f"Number of token exceeding limit: {tkn_sum}>{self.max_token}")

            assert tkn_len(dataset) <= self.max_token
            answer = chat(
                model=self.llm,
                messages=dataset,
                temperature=self.llm_temp,
                verbose=self.verbose,
            )
            nc = answer["choices"][0]["message"]["content"].strip()
            if "IMPOSSIBLE" in nc or "impossible: " in nc:
                raise Exception(f"Detected failure mode of LLM: '{nc}'")

            assert nc != fc
            newcontent, _ = replace_media(
                content=nc,
                media=media,
                mode="add_media",
            ) if media else (nc, None)
            assert isinstance(newcontent, str)
            log["llm_answer"] = answer

            if self.price:
                log["dollar_price"] = (
                    self.price["input_cost_per_token"] * answer["usage"]["prompt_tokens"]
                    + self.price["output_cost_per_token"] *
                    answer["usage"]["completion_tokens"]
                )
            else:
                log["dollar_price"] = "?"

        log["note_field_newcontent"] = newcontent
        formattednewcontent = self.cloze_output_parser(newcontent)
        log["note_field_formattednewcontent"] = formattednewcontent
        log["status"] = STAT_OK_REFORM

        if iscloze(content) and iscloze( newcontent + formattednewcontent):
            # check that no cloze were lost
            for cl in getclozes(content):
                cl = cl.split("::")[0] + "::"
                assert cl.startswith("{{c") and cl in content
                assert cl in formattednewcontent, f"A cloze was lost: {cl} from '{formattednewcontent}' present in '{content}'"
            # check that no cloze were added
            for cl in getclozes(formattednewcontent):
                cl = cl.split("::")[0] + "::"
                assert cl.startswith("{{c") and cl in formattednewcontent
                assert cl in content, f"A cloze was added: {cl} from '{formattednewcontent}' present in '{content}'"

        return log

    def apply_reformulate(self, log: Dict) -> None:
        """Apply reformulation changes to an Anki note and update its metadata.

        Parameters
        ----------
        log : Dict
            Log dictionary containing the reformulation results
        """
        nid = int(log["nid"])
        note = self.notes.loc[nid]

        # portion of the log that should be in the anki card
        minilog = {
            k: v
            for k, v in log.items()
            if k
            not in [
                "note_field_formattedcontent",
                "note_field_formattednewcontent",
                "llm_answer",
            ]
        }

        new_minilog = rtoml.dumps(minilog, pretty=True)
        new_minilog = new_minilog.strip().replace("\n", "<br>")
        previous_minilog = note["fields"].get("AnkiReformulator", {}).get("value", "").strip()
        if previous_minilog:
            new_minilog += "<!--SEPARATOR-->"
            new_minilog += "<br><br><details><summary>Older minilog</summary>"
            new_minilog += previous_minilog.replace("\n", "<br>")
            new_minilog += "</details>"

        if log["status"] != STAT_OK_REFORM:
            raise Exception(red(f"Unexpected status: {log['status']}"))

        # add DOING tags
        addtags(nid, tags="AnkiReformulator::DOING")

        # makes sure to avoid having a close in the final field otherwise
        # "Empty cards..." will not work and you'll get an annoying
        # warning in the browser
        new_minilog = new_minilog.replace("}}", "]]")
        new_minilog = re.sub(r"\{\{c(\d+)::", r"[[c\1::", new_minilog)
        assert "{{c1::" not in new_minilog, "Failed to substitute cloze markups before storing to field"
        assert "{{c" not in new_minilog, "Failed to substitute cloze markups before storing to field"

        # also lightly break the html of images to avoid them being rendered
        # in the AnkiReformulator field
        new_minilog = new_minilog.replace("<img src=", "< img src=")

        # update note content
        updatenote(
            nid,
            fields={
                self.field_name: log["note_field_formattednewcontent"],
                # TODO: Might be nice to not require this
                "AnkiReformulator": new_minilog,
            },
        )

        # add done tags
        addtags(nid, f"AnkiReformulator::Done::{today}")

        # remove now useless tag
        removetags(nid, "AnkiReformulator::TODO")

        assert self.save_to_db(log), "Error when saving to db!"

        # remove DOING tag
        removetags(nid, "AnkiReformulator::DOING")

    def reset_note(self, nid: int, note: pd.Series) -> Dict:
        """Reset a note back to its state before reformulation.

        Parameters
        ----------
        nid : int
            Note ID from Anki
        note : pd.Series
            Row from the notes DataFrame containing the note data

        Returns
        -------
        Dict
            Log dictionary containing the reset results and metadata
        """
        log = {
            "nid": nid,
            "date": today,
            "version": self.VERSION,
            "timestamp": time.time(),
            "mode": self.mode,
            "status": None
        }
        currcontent = note["fields"][self.field_name]["value"]
        log["nonresetcontent"] = currcontent

        # check if contains the appropriate tags
        currtags = note["tags"]
        assert any(
            t.startswith("AnkiReformulator::Done") for t in currtags
        ), f"Note does not contain tag AnkiReformulator::Done : {nid} {currtags} {note}"

        # check if relevant entries found in the database
        entries = [
            ent
            for ent in self.db_content
            if str(ent["nid"]) == str(nid) and ent["mode"] == "reformulate"
        ]

        if not entries:
            red(f"Entry not found for note {nid}. Looking for the content of "
                "the field AnkiReformulator")
            logfield = note["fields"]["AnkiReformulator"]["value"]
            logfield = logfield.split(
                "<!--SEPARATOR-->")[0]  # keep most recent
            if not logfield.strip():
                raise Exception(f"Note {nid} was not found in the db and its "
                                "AnkiReformulator field was empty.")

            # replace the [[c1::cloze]] by {{c1::cloze}}
            logfield = logfield.replace("]]", "}}")
            logfield = re.sub(r"\[\[c(\d+)::", r"{{c\1::", logfield)
            if iscloze(currcontent):
                assert not iscloze(logfield), f"Failed to substitute cloze markups before storing to field"

            # parse old content
            buffer = []
            for line in logfield.split("<br>"):
                if buffer:
                    try:
                        _ = rtoml.loads("".join(buffer + [line]))
                        buffer.append(line)
                        continue
                    except Exception:
                        assert buffer[-1].endswith(
                            "'"
                        ), f"Buffer does not end like expected: {buffer[-1]}"
                        assert line.startswith("dollar_price = ")
                        break
                elif line.startswith("note_field_content = '"):
                    buffer.append(line)
            assert buffer, f"No matching lines in AnkiReformulator field of note {nid}"
            oldcontent = rtoml.loads("".join(buffer))["note_field_content"]

            # parse new content at the time
            buffer = []
            for line in logfield.split("<br>"):
                if buffer:
                    try:
                        # TODO: What are you trying to do here? Just check that adding the line keeps valid toml?
                        # If so, you should catch the specific exception that the load function raises on error
                        rtoml.loads("".join(buffer + [line]))
                        buffer.append(line)
                        continue
                    except Exception:
                        assert buffer[-1].endswith(
                            "'"
                        ), f"Buffer does not end like expected: {buffer[-1]}"
                        break
                elif line.startswith("note_field_formattednewcontent = '"):
                    buffer.append(line)
            assert buffer, f"No matching lines in AnkiReformulator field of note {nid}"
            formnewcontentatthetime = rtoml.loads("".join(buffer))[
                "note_field_formattednewcontent"]
        else:
            # load the latest formulation
            entries = sorted(entries, key=lambda x: float(x["timestamp"]))
            assert (
                entries[0]["timestamp"] <= entries[-1]["timestamp"]
            ), "wrong sorting order"
            assert int(nid) == int(entries[-1]["nid"]), "Non matching nid!"
            oldcontent = entries[-1]["note_field_content"]
            formnewcontentatthetime = entries[-1]["note_field_formattednewcontent"]
        log["resetcontent"] = oldcontent

        ratio = levratio(formnewcontentatthetime, currcontent)
        if ratio == 100:
            log["status"] = STAT_OK_RESET
        else:
            # check if it's just the formatting
            if self.confirm_edited_reset:
                message = dedent(f"""
                \n\n
                Note {nid} was manually changed since it was reformulated.
                Levenshtein ratio: {ratio:.4f}
                Current content:
                '''
                CURRCON
                '''

                Content at the time:
                '''
                NEWCON
                '''

                * Y(es) to proceed with the reset.
                * N(o) to ignore this card and just tag it AnkiReformulator::ContentChanged.
                * Q(uit) to quit.
                """).replace(
                    "NEWCON",
                    formnewcontentatthetime
                ).replace(
                    "CURRCON",
                    self.cloze_input_parser(currcontent) if iscloze(currcontent) else currcontent
                )
                ans = ""
                while ans.lower() not in ["y", "yes", "n", "no", "q", "quit"]:
                    ans = input(message)
                if ans.lower().startswith("y"):
                    log["status"] = STAT_OK_RESET
                elif ans.lower().startswith("n"):
                    log["status"] = STAT_CHANGED_CONT
                elif ans.lower().startswith("q"):
                    raise SystemExit("Quitting.")
                else:
                    raise ValueError(ans)
            else:
                log["status"] = STAT_CHANGED_CONT

            # add check that number of cloze are equivalent. If not, just warn the
            # user in read
            half_cloze_text = self.cloze_input_parser(currcontent)
            full_cloze_text = formnewcontentatthetime + half_cloze_text
            if iscloze(full_cloze_text):
                # check that no cloze were lost
                checked = []
                for cl in getclozes(full_cloze_text):
                    n = int(cl.split("::")[0].split("{{c")[1])
                    n_str = "{{c" + str(n) + "::"
                    if n_str in checked:
                        continue
                    checked.append(n_str)
                    if n_str in half_cloze_text and n_str in formnewcontentatthetime:
                        continue
                    if n_str not in half_cloze_text:
                        red(f"nid:{nid} Cloze {n_str} found in previous cloze "
                            "version but not in current. This can result in "
                            "card being created or destroyed. Think about it")
                    else:
                        red(f"nid:{nid} Cloze {n_str} found in current cloze "
                            "version but not in previous. This can result in "
                            "card being created or destroyed. Think about it")

        previous_minilog = note["fields"]["AnkiReformulator"]["value"].strip()
        assert previous_minilog, f"No previous minilog found in note: {nid}: {note}"
        log["previous_minilog"] = previous_minilog

        return log

    def apply_reset(self, log: Dict) -> None:
        """Apply reset changes to an Anki note and update its metadata.

        Parameters
        ----------
        log : Dict
            Log dictionary containing the reset results
        """
        nid = int(log["nid"])

        # portion of the log that should be in the anki card
        minilog = {k: v for k, v in log.items() if k not in [
            "previous_minilog"]}
        previous_minilog = log["previous_minilog"]

        if log["status"] != STAT_OK_RESET:
            if log["status"] == STAT_CHANGED_CONT:
                addtags(nid, tags="AnkiReformulator::ChangedContent")
                red(f"Content of note with nid {nid} was changed since last "
                    "time. Not resetting it but adding the tag AnkiReformulator::ChangedContent")
                return
            else:
                raise Exception(red(f"Unexpected status: {log['status']}"))

        # add RESETTING tags
        addtags(nid, tags="AnkiReformulator::RESETTING")

        # append the new minilog the the old one, in hidden detail tag
        new_minilog = rtoml.dumps(minilog, pretty=True)
        new_minilog = new_minilog.strip().replace("\n", "<br>")
        new_minilog += "<!--SEPARATOR-->"
        new_minilog += "<br><br><details><summary>Older minilog</summary>"
        new_minilog += previous_minilog.replace("\n", "<br>")
        new_minilog += "</details>"

        # makes sure to avoid having a close in the final field otherwise
        # "Empty cards..." will not work and you'll get an annoying
        # warning in the browser
        new_minilog = new_minilog.replace("}}", "]]")
        new_minilog = re.sub(r"\{\{c(\d+)::", r"[[c\1::", new_minilog)
        if iscloze(log["nonresetcontent"]):
            assert not iscloze(new_minilog), f"Failed to substitute cloze markups before storing to field"

        # update note content
        updatenote(
            nid,
            fields={
                self.field_name: log["resetcontent"],
                "AnkiReformulator": new_minilog,
            },
        )

        assert self.save_to_db(log), "Error when saving to db!"

        # remove TO_RESET tag if present
        removetags(nid, "AnkiReformulator::TO_RESET")
        # remove Done tag
        removetags(nid, "AnkiReformulator::Done")
        # remove DOING tag
        removetags(nid, "AnkiReformulator::RESETTING")

    ##################################################
    # DB HANDLING METHODS ############################
    ##################################################

    def save_to_db(self, dictionnary: Dict) -> bool:
        """Save a log dictionary to the SQLite database.

        Parameters
        ----------
        dictionnary : Dict
            Log dictionary to save

        Returns
        -------
        bool
            True if save was successful
        """
        data = zlib.compress(
            json.dumps(
                dictionnary,
                ensure_ascii=False,
            ).encode(),
            level=9,  # 1: fast but large, 9 slow but small
        )
        conn = sqlite3.connect(str((REFORMULATOR_DIR / "reformulator.db").absolute()))
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS dictionaries
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data TEXT)""")
        cursor.execute("INSERT INTO dictionaries (data) VALUES (?)", (data,))
        conn.commit()
        conn.close()
        return True

    def load_db(self) -> Dict:
        """Load all log dictionaries from the SQLite database.

        Returns
        -------
        Dict
            All log dictionaries from the database, or False if database not found
        """
        if not (REFORMULATOR_DIR / "reformulator.db").exists():
            red(f"db not found: '{REFORMULATOR_DIR}/reformulator.db'")
            return False
        conn = sqlite3.connect(str((REFORMULATOR_DIR / "reformulator.db").absolute()))
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM dictionaries")
        rows = cursor.fetchall()
        # TODO: Why do you compress? This just makes it more difficult to debug
        return [json.loads(zlib.decompress(row[0])) for row in rows]


if __name__ == "__main__":
    try:
        args, kwargs = fire.Fire(lambda *args, **kwargs: [args, kwargs])
        if "help" in kwargs:
            print(help(AnkiReformulator), file=sys.stderr)
        else:
            whi(f"Launching reformulator.py with args '{args}' and kwargs '{kwargs}'")
            r = AnkiReformulator(*args, **kwargs)
            r.reformulate()
            sync_anki()
    except AssertionError as e:
        red(e)
    except Exception as e:
        red(e)
        raise
