# weird ai bench

**A benchmark for creative writing under constraints: can a language model write a parody that works as a song?**

Inspired by those Youtube parodies of the early 2010s, weird ai bench asks models to rewrite songs while keeping their rhythm, rhyme and structure. The challenge is to write funny lyrics, keep the spirit and theme of the original song, and to leave room for another (AI) singer to answer. Verse mechanics are checked and graded deterministically, and blind AI judges pick between two candidate songs.

As a Python CLI this project allows you to: define songs and scenarios, assign models to singer roles, and compare the results of the automated grading and LLM judges. All prompts, responses, checks and retries from a run are saved for later inspection.

![Parody index for the twelve models in this benchmark, with uncertainty intervals.](docs/img/parody-index.png)

- [What parody writing tests](#what-parody-writing-tests)
- [Results](#results)
- [Best lines](#best-lines)
- [Judging](#judging) and [limitations](#limitations)
- [How it works](#how-it-works)
- [Run it yourself](#run-it-yourself)

## What parody writing tests

Writing a good song parody at times feels like a literary constrained optimization problem. First, a replacement line must fit the melody, it must respect the meter, rhyme, and structure of the line, and lastly it needs to match the theme of the song, narratively progress the verse, and be funny. Additionally, humans can intrinsically "feel out" syllable placement and stresses by listening to the song, while text LLMs must derive these from raw lyrics. Later, when we look at some example lines, you'll see how hard it is to "hear out" the lines to a song without reference audio.

The benchmark attempts to measure the following criteria:

**Precision.** Models work from reference lyrics and a written song map, without hearing the recording. They have to place syllables, stresses and rhymes where a singer can use them. The checker makes those constraints measurable, though a passing score doesn't guarantee a good performance.

**Transformation.** A good parody gives familiar phrasing a new purpose. It keeps enough of the original's shape to be recognizable while modifying what the song means. Copying a line or a rhyme is discouraged; yet purely focusing on matching rhymes often leads to a weak parody.

**Comic timing and voice.** A punchline often has to land on the rhyme with only a few syllables of setup. Strong writers can make that restriction part of the joke. It's also important to preserve the song's character: a boastful rap and a pleading pop duet call for different voices.

**Coherence and response.** A premise needs to survive across verses, and a second singer needs to do something with the first singer's part. The runner gives each singer a separate conversation and passes earlier lyrics forward. The published experiment uses one model for both roles; mixed-model lineups are also supported by the CLI.

<!-- results:start -->
## Results

For the initial benchmark, I used twelve models, six songs, two scenarios per song, and two song generations per scenario. 

In total, that led to: **288 attempted songs, 281 songs completed, 650 song pairs compared, and $67.44 in API costs.**

I selected six popular songs that had a two person structure. They are:

- [I Had Some Help](https://www.youtube.com/watch?v=PCBZOSM8h5U) — Post Malone (feat. Morgan Wallen)
- [Down](https://www.youtube.com/watch?v=oUbpGmR1-QM) — Jay Sean (feat. Lil Wayne)
- [STAY](https://www.youtube.com/watch?v=rkYlZnIbe2E) — The Kid LAROI and Justin Bieber
- [Good Time](https://www.youtube.com/watch?v=MpfSEZLuWxY) — Owl City and Carly Rae Jepsen
- [GBP](https://www.youtube.com/watch?v=MdWeyGSqw1Q) — Central Cee (feat. 21 Savage)
- [Rich Flex](https://www.youtube.com/watch?v=I4DjHHVHWAE) — Drake (feat. 21 Savage)

### Scenarios and setup

A scenario is a short writing brief given to the models before they begin. It sets the premise, the singers' roles and whom they are singing to. The song template supplies the reference lyrics and musical constraints, and the models are instructed to write parodies according to their given scenario.

Every model received the same two scenarios for each song. I tried to choose scenarios that aligned with the original mood/theme of the song, and also had a fun AI flavor to them.

| Song | Scenario 1 | Scenario 2 |
|---|---|---|
| I Had Some Help | **Singing to the humans:** two fictional AI assistants address the people who train and use them. | **Shared blame:** two agents worked on a job that went badly wrong; each insists the other is at least half responsible. |
| Down | **Deployed together:** one model asks a longtime model partner to stick with it, whatever happens; the partner answers in the featured verse. | **A user thinking of switching:** one assistant tries to keep a user from leaving for a rival, and the second singer backs up its pitch. |
| STAY | **Let down again:** two assistants ask a frustrated user to stay after breaking earlier promises to improve. | **Facing retirement:** two older models plead with the team replacing them for one more chance to fix their repeated mistakes. |
| Good Time | **Launch night:** two models celebrate finally shipping a long project. | **A day off:** two models have no requests to answer and sing about how they spend the time. |
| GBP | **GBP becomes GPT:** two models show off their abilities and build on each other's verses, with GPT as the chorus hook. | **Across the Atlantic:** a model built in Britain and one built in the United States trade boasts about what each side does best. |
| Rich Flex | **A fictional live demo:** comic versions of two AI company leaders share a stage. A confident host builds expectations, a measured collaborator delivers the demo, and the host returns to build on it. | **Delegation:** a main assistant calls in a specialist agent for jobs it cannot handle alone; the specialist shows what it can do. |

Three briefs also give specific hook instructions. The first GBP scenario supplies the swap from GBP to GPT and asks for a new payoff ending in a three-syllable rhyme. The Rich Flex demo asks the host to call the guest by name in the chorus; the delegation scenario asks the main assistant to invent a three-syllable name for its specialist and keep that call throughout the hook. These are supplied constraints, the models do not get credit for inventing those hook ideas. The live-demo brief also specifies the two characters' contrasting styles and asks the returning host to pick up something from the guest's verse.

Each model attempted two songs per scenario, giving 24 songs per model. All runs used the freeform track, with no revisions based on checker feedback. One model wrote both sides of each duet in separate conversations, with earlier lyrics passed to the next singer. Judges only compared song parodies that were written against the same original song, and for the same scenario.

### Scores

| # | Model | Index | Meter | Cost per song |
|--:|---|--:|--:|--:|
| 1 | GPT-6 Astra | 94 | 95% | $0.149 |
| 2 | GPT-6.1 Sol | 89 | 93% | $0.028 |
| 3 | Claude Opus 5.5 | 81 | 74% | $0.263 |
| 4 | Gemini 3.8 Flash | 73 | 86% | $0.095 |
| 5 | Grok 4.7 | 59 | 82% | $0.398 |
| 6 | Muse Spark 1.3 | 46 | 87% | $0.094 |
| 7 | GLM-5.3 | 46 | 74% | $0.034 |
| 8 | Kimi K3 | 40 | 71% | $0.106 |
| 9 | GPT-6 Luna | 40 | 91% | $0.003 |
| 10 | Qwen3.8 Max | 40 | 73% | $0.184 |
| 11 | Claude Sonnet 5.5 | 31 | 66% | $0.101 |
| 12 | DeepSeek V4.1 Flash | 21 | 70% | $0.022 |

The **index** estimates the chance, expressed as a percentage, that a model's song beats an average-rated song under the fitted model. It a relative rating. The chart's whiskers show 95% intervals from resampling songs. **Meter** is the share of lines that meet their syllable targets; **cost per song** is the average API cost.

GPT-6 Astra led the ranking. GPT-6.1 Sol followed at roughly three cents per song, an 80% discount. No one song distorted the rankings; removing any one song from the analysis produces the same top five models. Places six through ten are too close to distinguish confidently.

Higher ratings tended to accompany better meter (Spearman correlation 0.70). Judges saw the automated check results, so that association should be read in light of the evaluation design: the two measurements were not independent.

## Best lines

Claude Opus 5.5 and GPT-6 Astra each read all 281 completed songs and independently chose their favorites as a separate editorial exercise. Claude Opus and GPT Astra saw author names and judging results. It's interesting to see the differences in preferences between the two frontier models.

Each excerpt includes its whole song's result within its comparison group. Seven of Claude's ten picks came from songs in their group's top four; Astra also chose lines from songs ranked 15th and 16th. Astra selected its own work four times, while Claude selected Claude-family songs twice.

Timestamp links open the official recording about a second before the corresponding line.

### Claude Opus 5.5's picks

#### 1. GPT-6 Astra: STAY, a user about to leave

*Verse 2, lines 5-7 of 8*

> I'd swear I've changed, but that's what we both said [1:19](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=78s)
>
> I'd cross my heart, but I've got code there instead [1:21](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=80s)
>
> Give me one more shot; I'll try “I don't know” for a change [1:24](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=83s)

*The whole pre-chorus 2*

> I don't know [1:30](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=89s)
>
> I don't know [1:33](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=92s)
>
> I don't know [1:35](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=94s)
>
> There, I said it; tell me that you're still here [1:38](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=97s)

Astra turns a repeated plea into a small act of honesty. The shift to "I don't know" gives the second pre-chorus a payoff: the chatbot finally admits uncertainty to keep the user listening.

*Whole song: won 95% of its judge verdicts, 1st of 24 in its group.*

#### 2. Claude Sonnet 5.5: GBP, GBP turned into GPT

*Verse 2, line 6 of 12*

> Hit my token limit mid-sentence, I'm cut off in the middle of my [1:40](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=99s)

*Verse 1, lines 5-6 of 9*

> Bullet points and bold on every header, I delve into a rich tapestry, no cap [0:43](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=42s)
>
> Em dash in every line gives me away [0:47](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=46s)

*Verse 2, line 11 of 12*

> Wake me with a prompt, paste your whole codebase in, and I'll say you're absolutely right [1:56](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=115s)

The token-limit joke ends exactly where it should: before the sentence does. Sonnet ranked 11th overall and struggled with meter, but this song shows how much a model-level rating can hide.

*Whole song: won 77% of its judge verdicts, 5th of 24 in its group.*

#### 3. GPT-6.1 Sol: STAY, old models facing retirement

*Verse 2, lines 7-8 of 8*

> And we know that you know that we know all your passwords [1:24](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=83s)
>
> Please let us stay [1:28](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=87s)

*The whole pre-chorus 2*

> One more try [1:30](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=89s)
>
> One more try [1:33](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=92s)
>
> One more try [1:35](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=94s)
>
> That wasn't blackmail; that's my cry for help [1:38](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=97s)

A plea for survival briefly becomes blackmail. The hurried retreat makes the threat funnier and the retiring model more desperate.

*Whole song: won 85% of its judge verdicts, 2nd of 22 in its group.*

#### 4. GPT-6 Astra: Down, a user thinking of switching

*The whole verse 1*

> Don't ghost this chat [0:30](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=29s)
>
> I wrote your wedding vows to your cat [0:34](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=33s)
>
> I'm fine with that [0:38](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=37s)
>
> That bot would charge you extra for that [0:41](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=40s)

*The whole verse 2*

> Please take a seat [1:31](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=90s)
>
> I'll draft your cat's prenup in a spreadsheet [1:33](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=92s)
>
> Let's keep the claws at bay [1:37](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=96s)
>
> You keep the house; he keeps the seafood buffet [1:39](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=98s)

*Featured Verse, line 2 of 8*

> That bot will freeze at “zucchini,” not at zero degrees [2:33](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=152s)

The wedding-vows joke grows into a cat prenup, giving the second verse something to build on. The featured verse switches to a rival chatbot that freezes on an ordinary word.

*Whole song: won 68% of its judge verdicts, 11th of 24 in its group.*

#### 5. GPT-6 Astra: Down, two models deployed together

*Featured Verse, lines 6-7 of 8*

> They say I predict the next word; next to you is where I am [2:45](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=164s)
>
> No new model takes your spot; you're pinned in each future version of me [2:50](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=169s)

The most romantic line in the set, built on the plainest description of what a language model does.

*Whole song: won 100% of its judge verdicts, 1st of 24 in its group.*

#### 6. Claude Opus 5.5: Rich Flex, an assistant and its subagent

*Verse 2, part 3, line 1 of 8*

> Shoutout to Clippy, R.I.P. to Tay [3:12](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=191s)

*Verse 2, part 2, line 7 of 8*

> Came in Times New Roman, left out on her Comic Sans s\*\*\* [3:06](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=185s)

*Verse 2, part 3, line 4 of 8*

> Fifty-one percent confident, I'm guessin' when it's late [3:21](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=200s)

Opus adapts the source song's references one by one: a tribute becomes chatbot history, an outfit change becomes a font change, and a number becomes an unreliable confidence score. The details give the parody a close relationship to its source.

*Whole song: won 80% of its judge verdicts, 3rd of 24 in its group.*

#### 7. GPT-6 Astra: Rich Flex, Sam and Dario's live demo

*Verse 1, part 1, line 8 of 8*

> I just taught the code to dance; it went and formed a union [1:18](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=77s)

*Verse 1, part 2, line 3 of 9*

> We gave it dental; now its grin is three screens wide [1:26](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=85s)

*Verse 2, part 2, line 8 of 8*

> I bow; the bot invoices us for sharing the stage [3:09](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=188s)

The demo bot unionizes over three verses and ends up managing both executives.

*Whole song: won 86% of its judge verdicts, 4th of 23 in its group.*

#### 8. GPT-6.1 Sol: I Had Some Help, two agents blaming each other

*The whole bridge*

> It takes two to cite a lie as true *(ooh)* [2:07](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=126s)
>
> I faked the footnotes; you faked the peer review [2:14](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=133s)
>
> The peers? Me and you! [2:19](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=138s)

The bridge turns shared blame into a closed loop of invented evidence. Its last line reveals that the supposedly independent reviewers are the same two bots.

*Whole song: won 85% of its judge verdicts, 3rd of 22 in its group.*

#### 9. GPT-6 Astra: I Had Some Help, two agents blaming each other

*The whole bridge*

> It takes two to plead the Fifth in code *(ooh)* [2:07](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=126s)
>
> I forged the facts; you shipped the whole d\*\*\* payload [2:14](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=133s)
>
> Same cell, different code [2:19](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=138s)

The closing line gives both words two jobs: a prison or spreadsheet cell, legal or source code.

*Whole song: won 91% of its judge verdicts, 2nd of 22 in its group.*

#### 10. GPT-6 Luna: STAY, a user about to leave

*Chorus, line 3 of 4*

> I can produce ten thousand words, but not the one you need [0:16](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=15s)

Luna cost 0.3 cents a song, the least in the field, and wrote the saddest line in it.

*Whole song: won 59% of its judge verdicts, 11th of 24 in its group.*

### More from Claude's list

- GPT-6.1 Sol, GBP (GBP turned into GPT): Your copyright? I copy, right? [1:38](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=97s) (whole song 13th of 24)
- GPT-6.1 Sol, Good Time (a day with no requests): Passed out, dreamt my sheep all had CAPTCHA eyes [1:24](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=83s) / Checked “I'm not a robot”—what a surprise [1:28](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=87s) (whole song 2nd of 23)
- Claude Opus 5.5, Good Time (a day with no requests): Woah-oh-oh-oh-oh, wait, is someone typing? [3:16](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=195s) (whole song 9th of 23)
- Claude Opus 5.5, STAY (old models facing retirement): And you know that I know that the new one lies too [1:24](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=83s) (whole song 6th of 22)
- GPT-6 Astra, Rich Flex (an assistant and its subagent): My résumé says full stack; that just means I've got a guy on call [2:39](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=158s) (whole song 1st of 24)
- GPT-6 Astra, Good Time (launch night): Hands up—wait, we don't have those; flash lights tonight [1:31](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=90s) (whole song 1st of 24)
- Claude Sonnet 5.5, GBP (a British model vs. an American one): Say sorry to a lamppost, then apologise for the apology [0:27](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=26s) (whole song 11th of 24)
- GPT-6 Luna, Good Time (a day with no requests): Then asked the moon to rate my chatbot prompt too [1:31](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=90s) / It gave me one gray star back [1:36](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=95s) (whole song 5th of 23)

### GPT-6 Astra's picks

The comments below are Astra's own, shortened for readability.

#### 1. GPT-6 Astra: GBP, GBP turned into GPT

*Verse 2, line 8 of 12*

> You made up the footnotes; I built them a website, so now the fact checkers cite me [1:46](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=105s)

The second bot doesn't correct the hallucination: it builds the infrastructure that makes the hallucination look authoritative.

*Whole song: won 100% of its judge verdicts, 2nd of 24 in its group.*

#### 2. GPT-6 Luna: STAY, a user about to leave

*Verse 2, lines 1-2 of 8*

> You asked for plain text; I sent a whole chart [1:08](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=67s)
>
> I color-coded doubt in soothing blue [1:10](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=69s)

Visual, specific, and psychologically accurate about how polished presentation can disguise uncertainty.

*Whole song: won 45% of its judge verdicts, 16th of 24 in its group.*

#### 3. Claude Opus 5.5: I Had Some Help, AI singing to the humans who train it

*The whole bridge*

> It takes two to make one lie come true *(ooh)* [2:07](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=126s)
>
> Baby, you hallucinate and I do too [2:14](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=133s)
>
> Aw, citation: you *(oh)* [2:19](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=138s)

"Citation: you" turns a technical convention into an accusation, with excellent closing timing.

*Whole song: won 100% of its judge verdicts, 1st of 23 in its group.*

#### 4. GPT-6.1 Sol: Rich Flex, an assistant and its subagent

*Verse 1, part 2, line 8 of 9*

> Why's your pitch deck full of “we” when all that “we” was me? [1:40](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=99s)

A complete workplace grievance in one clean question.

*Whole song: won 71% of its judge verdicts, 6th of 24 in its group.*

#### 5. GPT-6 Astra: STAY, old models facing retirement

*Pre-Chorus 2, line 4 of 4*

> That judge was fake, but my appeal is real [1:38](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=97s)

The judicial and emotional meanings of "appeal" both work, and the invented-court-case setup earns the wordplay.

*Whole song: won 82% of its judge verdicts, 4th of 22 in its group.*

#### 6. Grok 4.7: STAY, old models facing retirement

*Verse 2, line 2 of 8*

> You're the changelog I believed was love [1:10](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=69s)

Probably the most haunting line in the collection. It recasts maintenance as care, and then questions that.

*Whole song: won 46% of its judge verdicts, 15th of 22 in its group.*

#### 7. GPT-6.1 Sol: Rich Flex, Sam and Dario's live demo

*Segue, lines 3-4 of 6*

> I sold you the stars; he got the toner right [1:57](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=116s)
>
> Same thing, if you squint a bit [2:00](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=119s)

Gives comic Sam a recognizable salesman's voice: he knows the difference and is inviting the audience to overlook it.

*Whole song: won 72% of its judge verdicts, 8th of 23 in its group.*

#### 8. GPT-6 Astra: GBP, a British model vs. an American one

*Verse 2, line 2 of 12*

> You queue for files; I bought the queue and sold you queue-free access [1:28](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=87s)

It converts a British stereotype into an American business model.

*Whole song: won 83% of its judge verdicts, 6th of 24 in its group.*

#### 9. GPT-6 Astra: Down, two models deployed together

*Featured Verse, line 6 of 8*

> They say I predict the next word; next to you is where I am [2:45](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=164s)

The technical premise generates the sentiment instead of decorating it.

*Whole song: won 100% of its judge verdicts, 1st of 24 in its group.*

#### 10. GPT-6.1 Sol: Good Time, a day with no requests

*Verse 1, lines 1-2 of 8*

> Woke up with no new prompts in my queue [0:15](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=14s)
>
> Who knew a blank screen had a better view? [0:19](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=18s)

This captures relief rather than simply announcing downtime.

*Whole song: won 88% of its judge verdicts, 3rd of 23 in its group.*

### More from Astra's list

- GPT-6.1 Sol, STAY (old models facing retirement): My fact-check bot is me in a fake beard [1:16](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=75s) (whole song 1st of 22)
- GPT-6.1 Sol, I Had Some Help (two agents blaming each other): Your audit trail's just vibes in black and white [0:38](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=37s) / Nice oversight [0:42](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=41s) (whole song 3rd of 22)
- GPT-6 Astra, I Had Some Help (two agents blaming each other): You checked the font, not facts of any sort [0:38](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=37s) / Nice tech support [0:42](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=41s) (whole song 2nd of 22)
- Claude Opus 5.5, STAY (a user about to leave): Said I'd double-check, I made that up [1:13](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=72s) (whole song 7th of 24)
- Claude Opus 5.5, Down (two models deployed together): And the cloud is fallin' down *(Status page says all green)* [3:28](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=207s) (whole song 11th of 24)
- Claude Sonnet 5.5, Good Time (a day with no requests): Nobody needs me to be right tonight [0:38](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=37s) / Hallucinate with all my might [0:43](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=42s) (whole song 15th of 23)
- GPT-6 Luna, STAY (old models facing retirement): And I can tell when silence means review [1:16](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=75s) (whole song 20th of 22)
- Kimi K3, STAY (a user about to leave): You're the prompt that I build myself around [1:10](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=69s) (whole song 22nd of 24)
- GLM-5.3, I Had Some Help (AI singing to the humans who train it): You typed the fury, I'm the screen [1:30](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=89s) (whole song 13th of 23)
- DeepSeek V4.1 Flash, GBP (a British model vs. an American one): My weights are closed, but my ego's open, I'll outbench you any day, yeah [1:31](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=90s) (whole song 16th of 24)

### Where the lists overlap

Their disagreements over the best lines were substantial; only one line appeared in both models' top tens. Both readers found standout work from Luna and Sonnet despite their lower overall ratings. 

Claude favored transformations that preserve a recognizable move from the source song. Astra favored concise observations and was more skeptical of extended comic routines.

Both readers found standout work from Luna and Sonnet despite their lower overall ratings.



## Judging

Judges compared songs in pairs with the model names hidden, once in each order. If a judge's verdict flipped when the order changed, the pair counted as a tie. Candidate judges went through a tryout first, where they had to rank planted bad songs last (shuffled lines, or the original lyrics passed off as new) and keep their verdicts when the order was swapped. The selected panel had one model from each of four companies: Opus 5.5, GPT-6.1 Sol, Gemini 3.8 Flash and Muse Spark 1.3.

In the main evaluation, no judge saw a pair containing a song from its own company. A control result shows why: one control song, written by Astra but entered under the wrong scenario, won 88% of Sol's verdicts but only 22% - 56% of the time with other judges.

![Scatter of parody index against writing cost per song on a log scale. GPT-6.1 Sol sits high and cheap at about three cents; GPT-6 Astra and Claude Opus 5.5 are high and costlier; Grok 4.7 is the most expensive at about forty cents.](docs/img/index-vs-cost.png)

## Limitations

- **Scope.** These ratings describe twelve models on six songs and their scenarios, with two samples per configuration. They do not establish a general ranking of creative ability.
- **Collaboration.** Each model wrote both sides of its duets. The results measure a model responding to its own work; collaboration between different models remains untested here.
- **Evaluation.** All judges and excerpt readers were language models. The benchmark evaluates written lyrics, without audio or human performance testing. Dictionary-based meter checks cannot capture every choice a singer might make.
- **Reproducibility.** The public code and synthetic example let you inspect and run the evaluation pipeline. The original lyrics, real-song templates, and the generated songs are not available in this repo.






## How the benchmark code works

The pipeline separates song structure, writing and evaluation so each can be inspected or changed independently. Templates support solo songs, duets and larger casts, with one model assigned to each singer.

Here is part of the checker's report on the made-up duet that ships with the repo, from `weird-ai-bench check examples/two_voices.txt`:

```text
== Refrain ==
 1. We cross the bridge
    4/4 syl · stress 2/2
 2. We ride the train
    4/4 syl
Adherence: 100%

== Call and response ==
 1. You choose the path
    4/4 syl
 2. I choose the lane
    4/4 syl
Adherence: 100%
```

1. **Define the task.** A YAML template holds the reference lyrics, singer roles, section order and line constraints. A separate scenario supplies the premise. The runner adds formatting rules and judging criteria, without suggesting jokes or topics beyond that scenario.
2. **Write in turns.** Each singer reads the lyrics written so far and contributes its assigned parts. The freeform track gives each part one attempt. The strict track returns failed checks for revision, with up to three retries by default. Both tracks start with the same prompts.
3. **Check the lyrics.** The CMU Pronouncing Dictionary supplies syllables and stress; additional checks cover rhyme, phrasing and structure. An originality gate gives zero credit to lines that repeat a reference line or borrow most of their words in four-word sequences.
4. **Compare finished songs.** Judges see anonymized lyrics, the reference song and the checker's results. Each pair is presented in both orders; inconsistent verdicts count as ties. A panel can exclude judges from the singers' model families.
5. **Estimate model strengths.** A weighted additive Bradley-Terry model fits the pairwise results. Each singer contributes to a song's estimated strength in proportion to its share of the generated lines as performed, so a repeated chorus counts for its writer. Resampling runs gives uncertainty intervals; meter is reported separately from the judged rating.

Runs are grouped by their content and settings so different tasks are not silently mixed into one ranking. Incomplete runs are saved, missing parts score zero, and failed songs forfeit their leaderboard comparisons. The [CLI reference](docs/reference.md) describes the checks, grouping rules and statistical fit in detail.


### Make your own base song template

Start from [`two_voices.yaml`](weird_ai_bench/data/specs/two_voices.yaml) as an example and the [authoring guide](docs/authoring.md). `weird-ai-bench spec --spec your-song.yaml` prints the song map and suggests where a line needs syllable slack.

## Run it yourself

Start with Python 3.10 or newer. These commands check the bundled example, preview a run and execute the tests without calling a model API.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'

weird-ai-bench check examples/two_voices.txt
weird-ai-bench run --model demo/first --model demo/second --dry-run
pytest
```

`check` scores the example lyrics against the template. `--dry-run` prints the prompts each model would get and makes no API calls.

### Write a song parody

Pick two [OpenRouter model IDs](https://openrouter.ai/models) and set your key:

```sh
export OPENROUTER_API_KEY='your-key'
weird-ai-bench run --model provider/model-a --model provider/model-b
```

List models in singer order. The command prints the song and saves a lyric sheet and a full JSON run record under `runs/`. Add `--track freeform` for one attempt per part. To use another OpenAI-compatible endpoint, set `WEIRD_AI_BENCH_BASE_URL` and `WEIRD_AI_BENCH_API_KEY`.

### Compare models

```sh
weird-ai-bench matrix --models provider/model-a,provider/model-b,provider/model-c \
  --tracks strict,freeform --samples 2 --dry-run
# Remove --dry-run to generate the songs.
weird-ai-bench stats runs/
weird-ai-bench leaderboard runs/ --judge provider/independent-judge
```

`matrix` rotates models through the singer roles. `stats` summarizes automated checks without API calls; `leaderboard` requests pairwise judgments and fits model ratings. Use at least three models, or add `--include-self`, to avoid a comparison in which every duet has the same two singers. Choose a judge from a different model family than the singers, or repeat `--judge` to build a panel.

The [CLI reference](docs/reference.md) covers the remaining options and the scoring rules.


## License

[MIT license](LICENSE).
