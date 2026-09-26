# GZU: Data Science at the Command Line

goal: Become productive obtaining, scrubbing, exploring, and modeling data with Unix pipes and small tools — raising self-sufficiency without waiting on heavy GUI stacks.

audience: adult

tutor_notes: Adult GZU tone. Prefer pipes and small tools. Never invent flags — cite S1. Audio S3/S4 support NOVA lecture/speak. CPU node (LinuxBox1) is a fine practice host.

SOURCES [{"id": "S1", "title": "Data Science at the Command Line (PDF)", "locator": "D:\\pg\\documents\\Ebooks\\data_science_at_the_command_line.pdf", "authority": "primary", "note": "Jeroen Janssens \u2014 O'Reilly; authoritative book text", "sha256": "fd9a3b02e6ea5189824e1acf779247c515b328c39168791d75e132106bcb7c1e"}, {"id": "S2", "title": "DataScienceCommandLine.txt (audiobook transcript / extract)", "locator": "D:\\pg\\documents\\DataScienceCommandLine\\DataScienceCommandLine.txt", "authority": "secondary", "note": "Local extract + Pocket-TTS audio lineage on same folder", "sha256": "8fad51e606f516814ccd667c73e6190314211dd6215b39d26f3e0409b0e99ac8"}, {"id": "S3", "title": "DSCL_preface.mp3", "locator": "D:\\pg\\documents\\DataScienceCommandLine\\DSCL_preface.mp3", "authority": "secondary", "note": "Audio companion for lecture/speak path", "sha256": "1968a96d9d4bddad7d9a124aee101b85b024aa7ef190e8ae421df8a6bcbdf64f"}, {"id": "S4", "title": "DSCL_ch1.mp3", "locator": "D:\\pg\\documents\\DataScienceCommandLine\\DSCL_ch1.mp3", "authority": "secondary", "note": "Audio companion for lecture/speak path", "sha256": "a5b7bc56ca23e17ad092a20b0bc7e18dcaa4f6cbe6bbf9f90a910a622d9d902e"}, {"id": "S5", "title": "Data Science at the Command Line (PDF on LinuxBox1)", "locator": "/home/mike/Documents/data_science_at_the_command_line.pdf", "authority": "primary", "note": "Same book, second metal (OG Ubuntu). Hash when SSH hash convenient.", "sha256": null, "host_ref": "hearth:og-ubuntu"}]

PROVENANCE {"schema": "aitutor.course.v1", "content_sha256": "560b2b5f9b344e1d8fce0aca59eb76007f2043028ff0d4ced96dae6bb1ab29bd", "cite_count": 5, "hashed_zulu": "2026-09-21T10:19:59Z"}

WHI {"kind": "0x-DOC", "code_hint": "0x-DOC", "course_id": "gzu-dscl", "title": "GZU: Data Science at the Command Line", "cites": ["S1", "S2", "S3", "S4", "S5"], "stamped_zulu": "2026-09-21T10:19:59Z", "note": "Optional WHI header for NOVA ingest; AiTutor stays standalone."}

## Week 1: Orientation — why the command line for data science

objective: Explain when CLI pipelines beat heavyweight stacks and set up a practice shell.

topics: ["Unix philosophy", "pipes", "book map", "what to expect"]

activity: Skim preface + Ch.1 in S1/S2; list five daily data tasks you could pipe.

source_ids: ["S1", "S2"]

assessment: Can name obtain/scrub/explore/model and give one CLI example each.

## Week 2: Getting data

objective: Obtain data from files, APIs, and the web using CLI tools introduced in the book.

topics: ["curl", "scraping patterns", "file formats"]

activity: Follow a Ch.2-style obtain recipe from S1; save raw sample under a practice folder; cite commands used.

source_ids: ["S1", "S2"]

assessment: Raw file + command history with S1 page/section cite.

## Week 3: Creating reusable command-line tools

objective: Turn ad-hoc one-liners into small reusable tools (shell/Python) as in the book.

topics: ["shebangs", "arguments", "unpack patterns"]

activity: Write one tiny tool that does one job well; document usage in 5 lines citing S1.

source_ids: ["S1", "S2"]

assessment: Tool runs twice on different inputs without edits.

## Week 4: Scrubbing data

objective: Clean and reshape tabular/text data with classic filters (cut/sort/sed/jq patterns from the book).

topics: ["CSV/TSV", "jq", "normalization"]

activity: Scrub a messy sample to tidy columns; keep before/after and cite tools from S1.

source_ids: ["S1", "S2"]

assessment: Diff shows intentional cleans only; tools listed with cites.

## Week 5: Managing your data workflow

objective: Organize projects, history, and reproducibility habits from the book's workflow chapter.

topics: ["directories", "history", "reproducible runs"]

activity: Create a mini project layout and re-run last week's scrub from a single script.

source_ids: ["S1", "S2"]

assessment: Fresh shell can reproduce output from README + script.

## Week 6: Exploring data

objective: Explore distributions and structure at the CLI before jumping to notebooks.

topics: ["counts", "histograms", "sampling"]

activity: Produce three exploratory one-liners on a dataset; interpret in plain language.

source_ids: ["S1", "S2"]

assessment: Findings match the numbers your commands printed.

## Week 7: Parallel pipelines

objective: Speed up batch work with parallel patterns from the book without melting the machine.

topics: ["parallel", "jobs", "resource care"]

activity: Parallelize a safe embarrassingly-parallel scrub/explore step; note wall time before/after.

source_ids: ["S1", "S2"]

assessment: Timing note + no data corruption vs serial run.

## Week 8: Modeling at the command line

objective: Apply lightweight modeling/feature steps shown in the book; know when to hand off to Python/R.

topics: ["features", "simple models", "hand-off points"]

activity: Run one book-aligned modeling recipe; write when you would leave the CLI.

source_ids: ["S1", "S2"]

assessment: Clear hand-off rationale; cites for tools used.

## Week 9: Capstone — OSEMN on your own dataset

objective: Obtain, scrub, explore, (light) model a personal dataset entirely via CLI where honest.

topics: ["synthesis", "citation", "self-sufficiency"]

activity: Ship a short report + script pipeline; every non-obvious claim cites S1/S2.

source_ids: ["S1", "S2", "S3", "S4"]

assessment: Peer/tutor can reproduce; no unsourced tool claims.