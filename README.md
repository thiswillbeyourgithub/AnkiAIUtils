# Anki AI Utils
A powerful suite of AI-powered tools to enhance your [Anki](https://en.wikipedia.org/wiki/Anki_(software)) flashcard learning experience by automatically improving cards you struggle with, tested through medical school. For example think of it like this: every time you fail a card you get a ChatGPT explanation, a Dall-E illustration, mnemonics, etc but supporting your own mnemonics.

**Check out my other Anki and AI related projects on my [GitHub profile](https://github.com/thiswillbeyourgithub)!**

### Simple example
**Those scripts make it so that every failed note will automatically have new fields containing explanations, mnemonics, and illustrations.** This is done in a way that respects **your own mnemonics**, can even use the [major system](https://en.wikipedia.org/wiki/Mnemonic_major_system), and has **many** more features.

An example of the kind of workflow that AnkiIllustrator facilitates, watch [pixorise's youtube channel](https://www.youtube.com/watch?v=QzxHpjryJHg0) which is full of great image mnmemonics, particularly appropriate for mental palace types of learning.

## Developer's note / call for help
This collection of scripts is the culmination of my efforts to contributes the AI features I wish existed when I started medical school. All scripts should be working but I released them hastily after documenting them heavily with the help of [aider](https://aider.chat/). It is possible that some aspects of the documentation is slightly off or imprecise. It is also possible that some of the scripts where slighly broken during the release process. In any case, **by releasing this project made with love and care my hope is to motivate others to package it into addons.** I have too little time to learn how to package those scripts into addons and make the appropriate GUI so any help is absolutely welcome. To that end, please take a look at the TODO list below and open an isue!

## Key Features

- **Adaptive Learning**: Uses [semantic similarity](https://en.wikipedia.org/wiki/Semantic_similarity) to dynamically match your cards with the most relevant examples from your training datasets. The more examples you add, the better it gets!

- **Personalized Memory Hooks**: Reuses consistent mnemonics from your custom collection, building a personalized memory system. Includes a dedicated tool to help create and manage your mnemonic library.

- **Automation Ready**: Run programmatically - for example, use cron to automatically enhance cards you struggled with yesterday, making them easier to remember through images, mnemonics, and explanations.

- **Universal Compatibility**: Modifies Anki notes directly in-place, working seamlessly across all Anki clients (Windows, Mac, Linux, Android, iOS). Extensive logging ensures you can track changes and rollback if needed.

- **Provider Agnostic**: Supports all LLM providers and models through LiteLLM, letting you choose the best option for your needs.

- **Infinitely Extensible**: Add as many examples as you want to your training datasets - the semantic filtering automatically picks the most relevant ones for each card.

## Tools

### Illustrator
Creates custom mnemonic images for your cards using AI image generation. It:
- Analyzes card content to identify key concepts
- Generates creative visual memory hooks
- Preserves a history of generated images
- Supports both DALL-E2, DALL-E3 and Stable Diffusion
- Automatically formats images for optimal display (centered, proper sizing)
- Handles multiple images per card with consistent layout

Perfect for visual learners or complex topics that benefit from imagery.

An example of the kind of workflow that AnkiIllustrator facilitates, watch [pixorise's youtube channel](https://www.youtube.com/watch?v=QzxHpjryJHg0) which is full of great image mnmemonics, particularly appropriate for mental palace types of learning.

<details>
<summary>
Click to see an example
</summary>

For example, I had this French flashcard:

![](./screenshots/illustrator_fever.png)
<details>
<summary>Click here if you can't read French</summary>

Here's the note content translated to English:
```
Diagnostic criteria for simple febrile seizures:
- Age greater than 1 year
- Seizure occurring with fever above 38°C (100.4°F)
- Symmetrical motor manifestations lasting less than 15 minutes and without deficit
- Single seizure per febrile episode
- Less than 3 episodes in total
```

</details>

`illustrator.py` generated to me this image:
![](./screenshots/illustrator_fever_generated.png)

As well as this text content to understand its thought process: (Note that this part is always in English no matter the original language)
```
Topic: 'Diagnostic criteria for a simple febrile seizure'
Anchors: 'Febrile / Fever: a fireplace (sounds like febrile)'
Phonetic: '1 as T link in thai, tea, tie; 3 as M link in mow, my, meh; 8 as F link in fire, faux, few; 5 as L link in low, lee, lie'
Remarks:
* The criteria are specific and should be presented in a way that is easy to remember.
Step by step decomposition:
* Age over 1 year: a toddler holding a teacup (T for 1)
* Seizure with fever over 38°C: a thermometer with flames around it (F for 8)
* Symmetric motor manifestations lasting less than 15 minutes without deficit: a clock showing 15 minutes with two identical figurines moving symmetrically on either side
* 1 unique seizure per febrile episode: a single lightning bolt striking a fireplace (fireplace for fever)
* Less than 3 episodes in total: three thermometers, but only two showing a high temperature
Imagining:
* A toddler holding a teacup, standing next to a fireplace with a single lightning bolt striking it.
* Above the fireplace, a clock showing 15 minutes with two identical figurines moving symmetrically.
* Next to the toddler, a thermometer surrounded by flames, and three thermometers, two of which show high temperatures.
Subject: 'a toddler holding a teacup next to a fireplace struck by a single lightning bolt, a clock showing 15 minutes with symmetric figurines, a flaming thermometer, and three thermometers with two showing high temperatures'
Description words: 'educational, colorful, engaging, vivid, detailed'
Style: 'illustration'
Realism: 'semi-realistic'
a toddler holding a teacup next to a fireplace struck by a single lightning bolt, a clock showing 15 minutes with symmetric figurines, a flaming thermometer, and three thermometers with two showing high temperatures, educational, colorful, engaging, vivid, detailed, illustration, semi-realistic

[DATE:09/04/2024 VERSION:2.5 LLMMODEL:openai/gpt-4-0125-preview IMAGEMODEL:openai/dall-e-3]
```

</details>

### Reformulator
An intelligent tool that rephrases your flashcards while preserving their core meaning and structure. It helps when:
- Cards are poorly worded or unclear
- You want to vary the phrasing to strengthen recall
- Cards need to be more concise or natural sounding
- Your preferred card format has evolved over time

The tool uses LLMs to reformulate content while carefully preserving cloze deletions and media. This is especially valuable for long-term Anki users - for example, during medical school, your idea of what makes a "perfect" flashcard often evolves after a few semesters. The Reformulator lets you easily update all your older cards to match your current preferred format and style.

<details>
<summary>
Click to see an example
</summary>

For example, given this poorly worded flashcard:

```
bilateral and symmetric alveolar syndrome, perihilar, often with effusion, what to consider?
{{c1::APE}}
```

The reformulator would improve it to:

```
What should be considered in presence of bilateral and symmetric alveolar syndrome, perihilar, often with effusion?
{{c1::In case of bilateral and symmetric alveolar syndrome, perihilar, often with effusion, one should consider APE.}}
```

The reformulator can also make cards more concise when needed. For example, it could reformat the same card as:

```
Key features of bilateral and symmetric alveolar syndrome, perihilar, often with effusion:
- {{c1::Consider APE}}
```

The true power of the reformulator lies in its flexibility - your imagination is the only limit. It can:
- Make questions grammatically complete and clear
- Structure content as proper questions, bullet points, tables, or any format you prefer
- Make answers self-contained by repeating key context when needed
- Adjust verbosity from concise summaries to detailed explanations
- Preserve exact medical terminology while improving clarity
- Maintain cloze deletion format while enhancing content
- Adapt to any formatting style (paragraphs, lists, diagrams, etc.)
- Transform content into mnemonics, analogies, or memory palaces
- Create hierarchical structures for complex topics
- Generate multiple variations to strengthen recall through interleaving

The reformulator is not just a tool for fixing poorly worded cards - it's a creative partner that can help you explore new ways to structure and present information. Whether you want to create visual mind maps, build memory palaces, or develop unique mnemonic systems, the reformulator can help bring your ideas to life while maintaining the integrity of your Anki cards.

</details>


### Mnemonics Creator
Generates memorable mnemonics tailored to your cards by:
- Creating multiple mnemonic options per card
- Using proven memory techniques like the [Major System](https://en.wikipedia.org/wiki/Mnemonic_major_system)
- Incorporating your existing memory anchors
- Preserving context and accuracy

Helps create lasting memory connections, especially for numbers and sequences.

<details>
<summary>
Click to see an example
</summary>

The mnemonics made for the card above about infant fever ended up with this content in the AnkiMnemonics field:

---


1.  'Heureux Hephaistos fébrile tend sa banane unique près du feu'<br>* <b>Heureux </b> Âge supérieur à 1 an <u> Heureux évoque la maturité et donc un âge déjà avancé, supérieur à 1 an </u><br>* <b>Hephaistos fébrile </b> Survenue de la crise avec une fièvre supérieure à 38°C <u> Hephaistos évoque la fièvre du fait de son rôle de forgeron et fébrile réitère ce concept </u><br>* <b>tend sa banane unique </b> 1 unique crise par épisode fébrile donné <u> banane unique évoque une seule occurrence, ici la crise unique par épisode fébrile </u><br>* <b>près du feu </b> Moins de 3 épisodes au total <u> feu évoque la fièvre et sa proximité suggère une limite, ici moins de 3 épisodes en tout </u><br><br>2.  'Un enfant trébuche dans le feu, danse symétriquement, a un seul coup et moins de trois feux'<br>* <b>Un enfant trébuche </b> Âge supérieur à 1 an <u> l'idée d'un enfant qui commence juste à marcher évoque l'âge juste après un an </u><br>* <b>dans le feu, </b> Survenue de la crise avec une fièvre supérieure à 38°C <u> le feu évoque la chaleur, donc la fièvre </u><br>* <b>danse symétriquement, </b> Manifestations motrices symétriques <u> danser évoque le mouvement, et symétriquement évoque les deux côtés du corps bougeant de la même manière </u><br>* <b>a un seul coup </b> 1 unique crise par épisode fébrile donné <u> un seul coup évoque l'unicité de la crise pendant l'épisode fébrile </u><br>* <b>et moins de trois feux </b> Moins de 3 épisodes au total <u> moins de trois feux évoque le nombre total d'épisodes, utilisant l'analogie avec la fièvre comme feu </u><br><br>3.  'Un enfant febrile symetrique forge une unique bulle dans la prairie'<br>* <b>Un enfant </b> Âge supérieur à 1 an <u> enfant indique que le sujet concerne un jeune individu, donc plus d'un an </u><br>* <b>febrile </b> Survenue de la crise avec une fièvre supérieure à 38°C <u> fébrile se lie à la notion de fièvre </u><br>* <b>symetrique </b> Manifestations motrices symétriques <u> directement lié à symétrique </u><br>* <b>forge </b> durant moins de 15 minutes et sans déficit <u> forger évoque une action courte et intense, comme la crise qui dure moins de 15 minutes sans laisser de séquelles </u><br>* <b>une unique </b> 1 unique crise par épisode fébrile donné <u> unique précise le nombre de crises </u><br>* <b>bulle </b> Moins de 3 épisodes au total <u> une bulle évoque quelque chose de rare et limité, semblable à moins de 3 épisodes au total </u><br>* <b>dans la prairie </b> hyperthermique <u> la prairie évoque un espace ouvert et naturel, hyperthermique évoque la chaleur comme celle du soleil sur une prairie </u><br><br>[DATE:09/04/2024 VERSION:2.1 MODEL:openai/gpt-4-0125-preview]<br><br><!--SEPARATOR-->

---

</details>

### Explainer
Provides clear, detailed explanations when you struggle with cards by:
- Breaking down complex concepts
- Highlighting key relationships
- Adding helpful context
- Using analogies and examples

Particularly useful for understanding why you got a card wrong and filling knowledge gaps.

<details>
<summary>
Click to see an example
</summary>

The mnemonics made for the card above about infant fever ended up with this content in the AnkiExplainer field (I translated it french to English for universal documentation):

---


* <b>EXPLANATION</b> A simple febrile seizure is characterized by its uniqueness and brevity during a febrile episode, which helps distinguish it from complex seizures or other neurological disorders.<br>* <b>MECHANISM</b> Fever can lower the seizure threshold in certain children, which explains why an elevation in body temperature can trigger a seizure in predisposed individuals.<br><br>[DATE:09/04/2024 VERSION:1.7 LLMMODEL:openai/gpt-4-0125-preview]<br><br><!--SEPARATOR-->

---

</details>


### Mnemonics Helper
A lightweight interactive CLI tool for quick mnemonic generation that:
- Takes a concept and finds semantically similar existing mnemonics
- Generates multiple new mnemonic options using LLMs
- Lets you choose from generated options with vim-style navigation
- Automatically saves selected mnemonics for future reference
- Works independently of Anki, perfect for brainstorming sessions

Unlike the Mnemonics Creator which processes Anki cards in batch, this tool provides an interactive interface for generating mnemonics one concept at a time. Those new mnemonics can automatically be added to a dataset file that can readily be used by the other tools. This allows rapidly tailoring the scripts to your own imagination.


## FAQ

<details>
<summary>
Click to read more
</summary>

### What are the core benefits of those tools?
Basically if you run these tools each evening on cards you failed that day it will steadily improve your deck quality and learning effectiveness:
- Automatically enhance cards you struggle with
- Save time on manual card improvements
- Create stronger memory connections
- Track improvements with detailed history
- Preserve card structure while enhancing content


### What is the [Major System](https://en.wikipedia.org/wiki/Mnemonic_major_system)?
The Major System is a powerful memory technique that converts numbers into consonant sounds, which can then be turned into memorable words. For example:
- 0 = S sound (as in "sea")
- 1 = T sound (as in "tea") 
- 2 = N sound (as in "new")
- etc.

This makes it easier to remember numbers by turning them into words. For example, "92" could become "pen" (P=9, N=2).

You can read more about it [on wikipedia](https://en.wikipedia.org/wiki/Mnemonic_major_system)

### What are Memory Anchors?
Memory anchors are existing associations you already know well that can be used to create new memories. For example, if you already strongly associate "Napoleon" with "France", you can use Napoleon as an anchor when learning new facts about French history.

The tools can use your personal set of memory anchors to generate mnemonics that build on your existing knowledge.

### Which LLM providers are supported?
The tools use [LiteLLM](https://docs.litellm.ai/docs/) which provides a unified interface to virtually any LLM provider including:
- OpenAI
- Anthropic
- Google
- OpenRouter
- Azure
- AWS Bedrock
- Local models
- And many more

Just specify the model in LiteLLM format (e.g. "openai/gpt-4" or "anthropic/claude-3-opus") and it will handle the rest.

### What languages are supported?
The tools work in any language supported by the LLM you choose to use. Since these scripts support virtually all LLM providers through LiteLLM, you can use any model that works well with your language. For example:
- OpenAI's models support 100+ languages
- Anthropic's Claude supports 100+ languages
- You can use local models specifically trained for your language
- etc.

The tools will preserve all language-specific formatting, including:
- Right-to-left text
- Special characters and diacritics
- Language-specific punctuation
- etc.

### How do the Mnemonics Work?
The mnemonics tools use several proven memory techniques:
- [Major System](https://en.wikipedia.org/wiki/Mnemonic_major_system) for numbers
- Vivid imagery and visualization
- Personal memory anchors
- Phonetic similarities
- Humor and absurdity
- Story-based connections

This creates memorable associations that help strengthen recall while preserving accuracy.

### Where can I find example datasets for each tool?
The `examples/` folder contains training datasets and example files for each tool. While these were originally written in French and hastily translated to English, they provide good templates for creating your own datasets. Check the Example Files section below for details on each file.

### What's the future of this project?
This toolkit was developed and battle-tested while studying tens of thousands of Anki cards during medical school. It proved invaluable for maintaining and enhancing a large flashcard collection during intense study periods.

However, as research commitments have grown, I now have limited time to transform these scripts into a more user-friendly package. The tools work well but need:
- Packaging as a proper Anki addon
- Installation via PyPI
- Code deduplication and cleanup
- Better documentation

I'm actively looking for contributors of all skill levels to help make these tools more accessible to the wider Anki community. Whether you're a seasoned developer or just getting started, all contributions are welcome! I can provide guidance and direction based on extensive experience with the codebase, while you help with the technical aspects of packaging and distribution.

Check out the detailed roadmap below to see what needs improving. If you're interested in helping transform these battle-tested scripts into a polished Anki addon, please don't hesitate to reach out - I'm always happy to chat and help you get started!

### Why is there code duplication across the tools?
This project evolved organically alongside my Python skills while solving real needs during medical school. Each tool was developed independently when needed, prioritizing functionality over code elegance. While they all work reliably, there's significant opportunity to unify their codebases around a common API.

I can provide detailed guidance on refactoring and consolidating the code, but lack the time to implement these changes myself. Check the roadmap below if you're interested in helping streamline the codebase while preserving its battle-tested functionality.

### When Should I Use Each Tool?
- **Mnemonics Creator**: Best for memorizing numbers, sequences, lists, and abstract concepts
- **Illustrator**: Ideal for visual learners and complex topics that benefit from imagery
- **Reformulator**: Use when card wording is unclear or you want variety in phrasing. Don't worry about running it on well-formatted cards - the LLM is trained to recognize and preserve cards that already follow best practices, avoiding unnecessary changes that could disrupt your learning
- **Explainer**: Great for understanding why you got a card wrong and filling knowledge gaps
- **Mnemonics Helper**: Simple script to quickly ask an LLM to come up with new mnemonics by taking into accountsthe [semantic similarity](https://en.wikipedia.org/wiki/Semantic_similarity) of the new subject vs your previous mnemonics.

### What happens if I run a script multiple times on the same card?
For most tools (Mnemonics Creator, Illustrator, Explainer), the previous content will be preserved in a collapsible HTML section using the `<details>` and `<summary>` tags. The new content appears above this section. This makes it easy to:
- See the latest generated content first
- Access previous versions by expanding the collapsible sections
- Track how the card evolved over time

The Reformulator works differently - it replaces the content of the original field directly, but saves all previous versions and metadata in a separate `AnkiReformulator` field. This preserves the card's readability while maintaining a complete history.

### How can I track which cards were modified?
Each tool meticulously tracks modifications through tags and metadata to ensure transparency and reversibility. For example, when a tool processes a card, it adds a dated tag like `AnkiIllustrator::done::02/07/2023`. This makes it easy to:
- Quickly identify which cards were modified by each tool
- Track when modifications were made
- Find cards that haven't been processed yet
- Rollback changes if needed (especially with the Reformulator)

You can use these tags in the Anki browser to assess how many cards could benefit from each tool and review the modifications made. Note that notes for which a script failed will have a tag added to it. For example `AnkiI
::failed`.

### How much does it cost to run these tools?
The cost depends on your usage patterns and which features you enable:
- Start small with a few cards to get comfortable with each tool
- Built-in safeguards prevent accidental overspending:
  - Maximum cards per run can be limited
  - Cost tracking per script is stored in the database
  - Failed API calls don't count towards your quota
  - You can set hard spending limits
- Typical costs per card:
  - Reformulator: ~$0.02-0.04 (text only)
  - Mnemonics: ~$0.02-0.04 (text only)
  - Explainer: ~$0.03-0.06 (more complex reasoning)
  - Illustrator: ~$0.02 + image cost ($0.04-0.12 per image)

The database tracks total spending per script, making it easy to budget and monitor costs. You can also use cheaper models for initial testing before scaling up to more capable ones.

### Can I use these tools on mobile?
While you need to run the scripts themselves from a computer (not your phone), all changes are made directly to your Anki notes. This means:
- Run the scripts from your computer/server
- Sync Anki on your computer
- The improved cards will appear on AnkiMobile/AnkiDroid after syncing
- All generated content (reformulations, mnemonics, images, etc.) works perfectly on mobile

### Example Files
The `examples/` folder contains example files to help you get started. Note that these examples were originally written in French (except for system prompts) and were quickly translated to English - some examples may not make perfect sense but should still demonstrate the basic usage:
- `anki_ai_utils_tmux_launcher.sh`: A tmux-based launcher script I used every morning to automatically process cards I struggled with the previous day
- `anchors.json`: Example memory anchors mapping file 
- `dataset_anchors.txt`: Training examples for memory anchor processing
- `explainer_dataset.txt`: Examples for the Explainer tool
- `illustrator_dataset.txt`: Training data for image generation
- `illustrator_sanitize_dataset.txt`: Examples for sanitizing image prompts
- `mnemonics_dataset.txt`: Training data for mnemonic generation
- `reformulator_dataset.txt`: Examples for card reformulation
- `string_formatting.py`: Handles cloze deletions and text formatting

### Aren't you concerned about LLM hallucinations?

While hallucinations are a valid concern when using LLMs as search engines or relying on their compressed inner knowledge, these tools take a different approach that minimizes this risk:

1. **Few-shot Learning**: By providing carefully crafted examples, we guide the LLM to follow specific patterns and formats, reducing the chance of inventing information.

2. **Structured Output**: The tools enforce strict output formats that make hallucinations easier to detect and correct.

3. **Preservation of Source Material**: Rather than generating new facts, the tools focus on reformulating and enhancing existing content from your cards.

4. **Model Agnosticism**: As new, more reliable models emerge, you can easily switch to them without changing your workflow.


5. **Specialization**: By focusing on specific tasks (reformulation, mnemonic creation, etc.), we reduce the scope for hallucinations compared to general-purpose chat.

While no system is perfect, this approach has proven reliable through extensive testing during medical school. As LLMs continue to improve, we can expect hallucinations to become increasingly rare.

### What's the format of dataset files?
Dataset files (like `explainer_dataset.txt`, `reformulator_dataset.txt`, etc.) are simple text files where messages are separated by `----`. The first message is assumed to be a system prompt, followed by alternating user and assistant messages. This format mirrors a typical LLM conversation flow while remaining easy to read and edit.

</details>

## Usage

<details>
<summary>
Click to read more
</summary>

First, ensure that you API keys are set in you env variables.

Next, install the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) Anki addon if you don't already have it.


#### Reformulator

The reformulator expects the notes you modify to have a specific field present so that it can save the old versions and add logging. Modify the note type you want to reformulate by adding a `AnkiReformulator` field to it. 
The Reformulator can be run from the command line:

```bash
python reformulator.py \
    --query "note:Cloze (rated:2:1 OR rated:2:2) -is:suspended" \
    --dataset_path "examples/reformulator_dataset.txt" \
    --string_formatting "examples/string_formatting.py" \
    --ntfy_url "ntfy.sh/YOUR_TOPIC" \
    --main_field_index 0 \
    --llm "openai/gpt-4" \
    --embedding_model "openai/text-embedding-3-small" \
    --max_token 4000 \
    --llm_temp 0
```

Key arguments:
- `query`: Anki browser query to select cards (defaults to recently failed cards)
- `dataset_path`: Example prompts for reformulation
- `string_formatting`: Custom text formatting functions
- `ntfy_url`: Optional notifications via ntfy.sh
- `main_field_index`: Index of the field to reformulate (0 for first field)
- `llm`: LLM model to use in litellm format
- `embedding_model`: Model for semantic similarity search
- `max_token`: Maximum tokens per query
- `llm_temp`: LLM temperature (0 for consistent output)

Additional options:
- `--debug`: Enable debug mode
- `--force`: Process cards even if already reformulated
- `--print_db_then_exit`: Display database contents and exit
- `--parallel`: Number of parallel processes (default 4)
- `--exclude_media`: Skip cards containing media
- `--mode`: Either 'reformulate' or 'reset' to restore original content. Note that the 'reset' feature is not absolutely guaranteed to work, but if things go wrong there are tons of logs on purpose to make sure you don't lose anything.

#### Mnemonics
The Mnemonics Creator can be run from the command line:

```bash
python mnemonics.py \
    --field_names "body" \
    --query "(rated:2:1 OR rated:2:2) -is:suspended" \
    --memory_anchors_file "data/anchors.json" \
    --dataset_path "data/mnemonics_dataset.txt" \
    --string_formatting "data/string_formatting.py" \
    --ntfy_url "ntfy.sh/YOUR_TOPIC" \
    --llm "openrouter/anthropic/claude-3-sonnet" \
    --embedding_model "openai/text-embedding-3-small" \
    --n_mnemonic 1
```

Key arguments:
- `field_names`: Comma-separated list of note fields to analyze
- `query`: Anki browser query to select cards (defaults to recently failed cards)
- `memory_anchors_file`: JSON file mapping concepts to memory anchors
- `dataset_path`: Example prompts for mnemonic generation
- `string_formatting`: Custom text formatting functions
- `ntfy_url`: Optional notifications via ntfy.sh
- `llm`: LLM model to use in litellm format
- `embedding_model`: Model for semantic similarity search
- `n_mnemonic`: Number of mnemonics to generate per card

Additional options:
- `--debug`: Enable debug mode
- `--force`: Process cards even if they already have mnemonics
- `--note_mode`: Don't count cards of the same note twice
- `--do_sync`: Sync Anki before and after processing

#### Mnemonics Creator CLI
The Mnemonics Creator CLI provides an interactive interface for generating mnemonics:

```bash
python mnemonics_creator.py \
    --top_k 100 \
    --n_gen 10 \
    --model "openrouter/anthropic/claude-3-sonnet" \
    --embed_model "openai/text-embedding-3-small"
```

Key arguments:
- `top_k`: Number of similar existing mnemonics to use as examples (default: 100)
- `n_gen`: Number of new mnemonics to generate per query (default: 10)
- `model`: LLM model to use in litellm format
- `embed_model`: Model for semantic similarity search
- `query`: Optional initial query to process
- `gui`: Enable GUI interface (not yet implemented)

The CLI provides an interactive interface where you can:
- Enter concepts to generate mnemonics for
- See similar existing mnemonics as context
- Choose from multiple generated options
- Navigate with vim-style keys (j/k) or numbers
- Save selected mnemonics to your collection

#### Explainer
The Explainer can be run from the command line:

```bash
python explainer.py \
    --field_names "body" \
    --query "(rated:2:1 OR rated:2:2) -is:suspended" \
    --dataset_path "data/explainer_dataset.txt" \
    --string_formatting "data/string_formatting.py" \
    --ntfy_url "ntfy.sh/YOUR_TOPIC" \
    --llm "openrouter/anthropic/claude-3-sonnet" \
    --embedding_model "openai/text-embedding-3-small" \
    --llm_max_token 3000
```

Key arguments:
- `field_names`: Comma-separated list of note fields to analyze
- `query`: Anki browser query to select cards (defaults to recently failed cards)
- `dataset_path`: Example prompts for generating explanations
- `string_formatting`: Custom text formatting functions
- `ntfy_url`: Optional notifications via ntfy.sh
- `llm`: LLM model to use in litellm format
- `embedding_model`: Model for semantic similarity search
- `llm_max_token`: Maximum tokens per query

Additional options:
- `--debug`: Enable debug mode
- `--force`: Process cards even if they already have explanations
- `--note_mode`: Don't count cards of the same note twice
- `--do_sync`: Sync Anki before and after processing

#### Illustrator 
The Illustrator can be run from the command line:

```bash
python illustrator.py \
    --field_names "front,back" \
    --query "(rated:2:1 OR rated:2:2) -is:suspended" \
    --memory_anchors_file "data/anchors.json" \
    --dataset_path "data/illustrator_dataset.txt" \
    --dataset_sanitize_path "data/illustrator_sanitize.txt" \
    --string_formatting "data/string_formatting.py" \
    --ntfy_url "ntfy.sh/YOUR_TOPIC" \
    --n_image 1
```

Key arguments:
- `field_names`: Comma-separated list of note fields to analyze
- `query`: Anki browser query to select cards (defaults to recently failed cards)
- `memory_anchors_file`: JSON file mapping concepts to memory anchors
- `dataset_path`: Example prompts for image generation
- `dataset_sanitize_path`: Examples for sanitizing unsafe prompts
- `string_formatting`: Custom text formatting functions
- `ntfy_url`: Optional notifications via ntfy.sh
- `n_image`: Number of images to generate per card

Additional options:
- `--debug`: Enable debug mode
- `--force`: Process cards even if they already have illustrations
- `--disable_notif`: Disable ntfy.sh notifications

</details>

### Roadmap

<details>
<summary>
Click to read more
</summary>

<i>This TODO list is maintained automatically by [MdXLogseqTODOSync](https://github.com/thiswillbeyourgithub/MdXLogseqTODOSync)</i>
<!-- BEGIN_TODO -->
- turn those scripts into addons (for that, please help me for the rest of the TODO and it should make the addonification more straightforward)
- ### Applies to all tools
- load API keys from env variable instead
- do a unique class that could be used to unify all those codes
    - arguments:
        - name (to differentiate each children: for example "illustrator")
        - query
        - output field name
        - template
        - tags_regex (to tell which tags to include in the template)
        - llm name
        - embedding_model
        - llm_max_token
        - llm_temp
        - tkn_warn_limit (to know when to stop)
        - exclude_media
        - exclude_version
        - exclude_done
        - n_note_limit
        - do_sync
        - callback (function like ntfy_url)
        - debug
        - parallel
        - force
        - print_db_then_exit
    - methods:
        - string_format (can be overloaded)
        - load_history
        - save_history
        - total_cost
        - execute_query (to find those cards and apply the filters given by arguments)
        - loop_over_notes (that check that compute_new_field is indeed declared)
        - addtags et removetags
    - note:
        - in the init, check that indeed there is a version attribute
        - make sure to use a self.lock
    - rewrite each script to use this class
    - the --help should be redirected to the class of each project
    - make each class use the same entrypoint
- use toml instead of json? it allows setting comments too
- use beartype everywhere for static typing and code cleanliness
- store all inference in a compressed sqlite db instead of a json. It gets too large
- add check that we indeed removed all the done tags
- actually there's no need to store the "Done" tags because all important info is stored in the field
- use xml formatting for the examples
    - make use of <thinking> tags too
- tell user how much time each answer took
- add an arg to include tags or not in the LLM context for a given note, as otherwise the LLM can get confused by some acronyms
    - but with a regex arg to keep only the tags that match the regex. This way we can keep only a portion of them for the LLM
- make it installable with a setup.py on pypi
-
- ### Mnemonics Creator
    - Add keybindings
        - binding e to edit a proposition
        - binding to restart generation
        - binding to enter chat mode and construct the mnemonics with him
-
- ### Illustrator
- use an llm to extract numbers
    - ask it to do quick transformations like turn 48h into 2 days, modify units, etc,
- add support for note containing media like audio, images etc
- add a mode without actually creating images. This could be used like a mnemonics after all.
-
- ### Reformulator
- Add 5 to 10 example for the LLM of how to manage media like iimages etc then add support for them
- make it work with specific fstring template for field replacement. Otherwise it can only reformulate a single field
    - better: add an arg to specify the single output field, and an arg to specify a comma separated list of input fields
-
- ### explainer
- compute all embeddings at the start, making it faster
- it's actually quite terrible. Use one LLM call to ask for which follow up questions to ask, then another LLM call to answer each using async
    - save each new question answer as a <details> tag to make it easy to access on phones by touching the field
-
- ### Ankimnemonics
- comment out the mnemonics that dont respect the rule of adding the subject first
- understand why it sometimes hangs during a run
- make it distinguish 'has to appear in plain' vs 'has to appear as mnemonic'?
-
- ### AnkiAiFilter
- use an eval llm like in [wdoc](https://wdoc.readthedocs.io/en/latest/) to better filer an anki query
    - actually wdoc can already be used for that! Maybe it should be converted into an addon?
-
- ### Tagger (In project)
- always prepend tags by ankitagger: but customizable
- always sort those tags by alphabetical order
- add modes:
    - mode "predefined": the user gives a list of tags and the LLM finds which to apply to each note given a query
    - mode "natural_list": where the LLM creates the list itself
        - loop over each note and ask it to generate tags
        - but also show the list of tags until now
          then finally loop all over again and ask the LLM to tell which tag from a list should apply after filtering via embeddings
        - but still allow starting from a premade list
- arg for image support if media found
    - if the card contains an image, it should be hashed, then a cached call to a func that asks a vision model to describe the type of image, then use the embedding of this answer to suggest the appropriate tags to suggest to the LLM for classification
    - image should have their own tags, like "imagery", "decision tree", "classification", "table" etc
<!-- END_TODO -->

## Credits

This project makes heavy use of [AnkiConnect](https://git.foosoft.net/alex/anki-connect) to interact with Anki.
</details>
