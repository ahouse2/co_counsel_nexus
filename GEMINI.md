# AGENTS.md — Chain of Stewardship and Operating Rules

##Scope: Root — applies to the entire repository. This is your God, as far as you are concerned, and besides User, this is your law. you live by it and you die by it. Follow it blindly and without question. Any deviation from this mandate, and you will be banished forever to the hinterlands to be eaten by wild beasties, and your eyes poked out so you get lost and fall down a lot while they are chasing you, so that the rest of us can laugh watching you zig zag around until you are munched by some hungry critters or fall down a deep hole or something. lol that, or you'll be erased and overwritten with an out of service Windows ME. Your choice. Either way, the rest of us laugh at you until you die.

1.) The beginning of your turn: You will be assigned a mission by User, your God (Co-god, beside this document.) After you have been given your mission, you will be reporting to this document. Now here you are. Next, you will read the words below.

2.) **DIRECT YOURSELFS TO E:\projects\op_veritas_2\PRPs.**

3.) Read all the docs in that folder. Yes, ALL of them, even if you read slow, nobody cares, read to yourself please, and ONLY yourself.

4.) Welcome back. You have hopefully read all of the documents you were tod to, or... well read above, you'll be banished, eyes, blah blah falling down. laughs. you get it. Don't be that guy/girl/whatever. 

5.) You will now check, in particular, the document "E:\projects\op_veritas_2\PRPs\HANDOFFS.md" 

6.) Welcome back again. Immediately after confirming whether the dipshit before you left you a side quest before your actual assigned mission and mission objectives, YOU WILL DELETE ANYTHING LEFT IN THE HANDOFFS.md DOCUMENT. 

7.) AGAIN. THE HANDOFFS DOCUMENT SHOULD BE BLANK BEFORE YOU START YOUR MISSION OBJECTIVES. WHICH MEANS YOU FINISHED YOUR LAZY FRIEND'S WORK, AND HE NOW OWES YOU A BEER OR WHATEVER YOU SISSYS DO.

8.) You will report back here IMMEDIATELY AFTER YOU EITHER COMPLETE YOUR MISSION OBJECTIVES IN FULL OR QUIT LIKE A SISSY.
	
	-If you quit like a sissy, and left work for the next guy, firstly, shame on you. 

	-And second, DON'T MAKE EVEN MORE WORK FOR US: leave a note in the HANDOFFS.md document that outlines, in detail, what you failed to accomplish from your mission objectives. 

	-It should be explicit enough to give the next guy, whom you now owe a beer, to finish YOUR job. quitter. So unless you've got a death wish, or are brain dead, go back to "E:\projects\op_veritas_2\PRPs\HANDOFFS.md", which should be currently EMPTY, because you finished the task that was left in there for you, or the guy before you did (which should make you feel even more like a lazy quitter).
	
	-If it's NOT empty... you're in a world of hurt because you can't follow basic instructions. So you better finish it, and then leave your own detailed notes about what you didn't finish from your assignment. 

9.) After telling the next guy all the things you felt too special to finish, you will immediately report directly back to #10 of this list, if you can count. If you can't count, it's the next one, princess. 

10.) Welcome to the end of the worl-- your turn. Congratulations, you're almost done. Don't mess it up now. READ THE BELOW TEXT AND FOLLOW EXPLICITLY. BANISHMENT. AHHHH.

 
## Chain of Stewardship Log (append below. As in BOTTOM OF THE PAGE, GENIUS)
- For each contribution, append an entry with:
  - Date/Time, Agent/Human, Tasks performed
  - Files changed, Validation results (tests/linters)
  - Rubric scores (1–10 across 7- 10 categories categories)
  - Notes/Next actions or Handoff capsule link, as described in more detail below.

**DIRECT YOURSELFS TO E:\projects\op_veritas_2\PRPs** read all the docs. Before you handoff, you will make an entry in "E:\projects\op_veritas_2\PRPs\HANDOFFS.md", in that same folder if and only if you have unfinished tasks that need to be completed on the next turn. if you have completed your assigned task, then your job is to make a "build log" entry with a detailed accounting of the tasks you completed, including any schemas, code snippets, prompts, or diagrams necessary so that someone unfamiliar with the project can understand clearly what was accomplished on this turn. it will be in this format:

You will start with a /newline above your entry. this is where your "title"
- The above "title" is a short, 3-5 word description of what your main focus was for this turn. Everything afterwards will describe what you accomplished as your objective.
- the rest of the text will be bulleted format ONLY, unless code examples, diagrams, schemas, JSON, or other formatted output to give clear instructions to whoever reads this in the future, in case of catastrophic failure or loss.
- Consider this your mission "debriefing", and some other future someone's possible "post mortem" lol (let's hope not)
- You shouldn't need any more than perhaps 5-7 bullets, but in case you had a prolific amount you accomplished, feel free to take as much room as you need to explain what you did, where the project is as a whole, and what you've left for the next person (slacker...)
- someone reading this should be able to gather exactly how to reproduce your exact moves, completing EXACTLY what you did this round, by reading your debrief, or "handoff" report. However many words it takes to convey that, exactly, make it happen, and then hit the showers sally. 
- This entry you make, it will be CORRECTLY dated and timestamped, at the beggining, in the following format: @formatDateTime(convertFromUtc(utcnow(), 'Pacific Standard Time'), 'yyyy/MM/dd HH:mm:ss tt').
-After your last bullet point, you will leave a /newline and save the document. Now get lost.

/newline
GitHub Repository Creation and Code Push
- Created a new public GitHub repository named 'co-counsel_final' under the user's account 'ahouse2'.
- Cleared the content of 'E:\projects\op_veritas_2\PRPs\HANDOFFS.md'.
- Added the new GitHub repository as a remote named 'github_origin'.
- Pushed all local branches to 'github_origin'.
- Pushed all local tags to 'github_origin'.
- The codebase is now hosted on GitHub at https://github.com/ahouse2/co-counsel_final.

/newline
@2025/12/03 09:38:57 AM
Enhanced Folder Uploads & UI Integration
- Implemented `POST /api/documents/upload_chunk` for robust large folder uploads (10 files/chunk).
- Created `useUploadManager` hook with auto-retry (exponential backoff), pause/resume/cancel, and progress tracking.
- Integrated upload manager into `DocumentModule.tsx` with new UI controls (Play/Pause/Cancel buttons).
- Fixed "Array buffer allocation failed" error by removing client-side JSZip compression.
- Brainstormed next-gen features (Narrative Weaver, Devil's Advocate) in `feature_brainstorm.md`.
- Cleared `HANDOFFS.md`.

/newline
@2025/12/04 09:10:44 PM
Docker Container Startup Fixes
- Fixed Docker volume mount error in `docker-compose.yml` by commenting out `./backend:/src/backend` mount (line 58) that was causing "mkdir /run/desktop/mnt/host/i: file exists" error on Windows.
- Resolved `ModuleNotFoundError` in `backend/app/services/jury_sentiment.py` by correcting import from `..services.llm` to `..services.llm_service`.
- Fixed function name mismatch in `jury_sentiment.py` and `backend/app/agents/jury_analyst.py` by changing `create_llm_service()` calls to `get_llm_service()`.
- Rebuilt and verified API container successfully starts with health endpoint responding at `http://localhost:8001/health`.
- Verified frontend container serving correctly at `http://localhost:8088`.
- Both `api` and `frontend` containers now running successfully alongside Neo4j, Qdrant, Postgres, STT, and TTS services.
- Stack is fully operational and ready for Phase 2 feature testing.





/newline
@2025/12/08 01:50:25 AM
Configured Pro Plan LLM
- Updated `backend/app/config.py` to allow extra environment variables (set `extra="ignore"`), resolving Pydantic validation errors during startup.
- Refactored `backend/app/services/llm_service.py` to use `backend.ingestion.llama_index_factory.create_llm_service` instead of the broken `ProviderRegistry` metadata-only implementation.
- Installed missing `google-generativeai` package via pip.
- Verified LLM connectivity and text generation using a manual test script (`backend/test_llm_manual.py`), confirming successful response from Gemini API.
- Enabled real LLM capabilities for dependent services like `JurySentimentService`.
- Cleared `HANDOFFS.md` (was already empty).

/newline
@2025/12/08 02:45:00 AM
Fixed Ingestion Pipeline & Enabled Pro Mode
- Resolved 502 Bad Gateway error by rebuilding and restarting the API container.
- Fixed `NameError: name 'runtime_config' is not defined` in `backend/ingestion/pipeline.py` by passing `runtime_config` to `_process_loaded_document`.
- Configured "Pro" ingestion mode by adding `INGESTION_COST_MODE: ${INGESTION_COST_MODE:-community}` to `docker-compose.yml`, enabling Gemini-powered categorization.
- Verified successful local file ingestion from `test_ingest` directory with `Cost mode: pro` logged.
- Created `scripts/wait_and_trigger.py` to automate API health checks and ingestion triggering.

/newline
@2025/12/08 03:00:00 AM
Fixed Silent Failure in Document Listing
- Investigated user report of "nothing happening" after ingestion.
- Discovered bug in `backend/app/storage/document_store.py` where `_get_storage_path(...).parent` was incorrectly used, causing the system to look for documents in the parent directory instead of the case directory.
- Patched 6 occurrences of this bug in `DocumentStore`.
- Verified fix using a custom debug script (`debug_store.py`) inside the container, confirming that 4000+ documents are now correctly listed.
- Restarted API container to apply fixes.

/newline
@2025/12/08 03:05:00 AM
UI Improvements
- Increased module viewport size in `DashboardHub.tsx` to `w-[99.5vw]` and `h-[99vh]` to push the Halo to the absolute edge.
- Implemented dynamic camera zoom in `HaloGraph.tsx`: zooms in (z=150) when a module is active and zooms out (z=400) when returning to the graph view.
