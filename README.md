# weird ai bench

![Bar chart of the weird ai bench parody index. GPT-6 Astra 94, GPT-6.1 Sol 89, Claude Opus 5.5 81, Gemini 3.8 Flash 73, Grok 4.7 59, Muse Spark 1.3 46, GLM-5.3 46, Kimi K3 40, GPT-6 Luna 40, Qwen3.8 Max 40, Claude Sonnet 5.5 31, DeepSeek V4.1 Flash 21.](docs/img/parody-index.png)

weird ai bench has language models rewrite real songs as parodies that fit the original melody. Each model gets a song's structure, meaning the number of lines in each section and the syllables in each line, along with a scenario to write about. A checker scores every line's meter and rhyme against that structure, and a panel of AI judges compares finished songs in pairs without knowing who wrote them.

- [What parody writing tests](#what-parody-writing-tests)
- [Results](#results)
- [Best lines](#best-lines)
- [How it works](#how-it-works)
- [Run it yourself](#run-it-yourself)

## What parody writing tests

A parody tests skills that a short story or an essay can hide.

The models never hear the song. They get syllable counts and stress patterns and have to write lines a singer could fit to the tune, so the benchmark tests prosody worked out on paper. The checker scores this directly, and the meter column in the results shows how far apart models are: GPT-6 Astra hit 95% of its syllable targets and Claude Sonnet 5.5 hit 66%.

The new song also has to stay recognizable as the old one. The best lines keep a move from the original and point it somewhere new. Opus traded references in its Rich Flex song for AI ones, one for one, and Astra turned STAY's "No, don't go" pre-chorus into "I don't know," the sentence chatbots are known for avoiding. A model that copies too much fails the originality check, and one that keeps the original's details without adapting them writes nonsense; Astra noticed many Rich Flex parodies kept references to Kobe and B&E that meant nothing in the new setting.

Jokes have to fit a fixed number of syllables and usually land on the last word of a line, where the rhyme falls. That leaves little room for setup, so the strongest lines fit a whole joke into one line, like Sol's "My fact-check bot is me in a fake beard." Rich Flex and GBP are rap songs built on boasts and internal rhyme while STAY is a pleading pop song, and each parody has to keep its original's voice.

A song also has to hold together. Astra's Down parody carries one story about a user's cat through three sections and pays it off in the last line. The duets add a listening test on top: the second singer reads the first singer's part and has to answer it rather than fill its own slots. In these results one model wrote both parts of each song, so the duets mostly show a model answering itself. The tool can put a different model on each part to test this properly.

Some failures come down to knowing what belongs in a lyric at all. Sonnet pasted its own syllable notes into a bridge, and Qwen wrote stress marks in capital letters, as if singing to the checker.

<!-- results:start -->
## Results

Twelve models wrote parodies of six songs: I Had Some Help, Down, STAY, Good Time, GBP and Rich Flex. Each song came with two scenarios picked to fit its mood, such as two agents blaming each other for a mess (I Had Some Help) or a model with a day off and no requests (Good Time). One model wrote both parts of each duet in separate conversations, and the second singer could read what the first had written. Each model wrote 24 songs on the freeform track, 288 in all; 281 finished, the judges compared 650 pairs, and the API bill came to $67.44.

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

The index is a model's estimated chance of beating an average-rated song when a judge compares the two, and the whiskers on the chart above are 95% intervals from resampling songs. Meter is the share of a model's lines that hit their syllable targets.

GPT-6 Astra came first. GPT-6.1 Sol came second at about 3 cents a song, a fifth of what Astra cost. Dropping any one of the six songs leaves places 1 to 5 in the same order, while places 6 to 10 are too close to separate. The judges saw the checker's results for each song, and their ranking tracks the meter column fairly well (Spearman correlation 0.70).

## Best lines

Two of the contestants, Claude Opus 5.5 and GPT-6 Astra, also read all 281 finished songs and picked the lines they thought were best. Both saw the model names and the judges' results, and neither saw the other's list.

A great line from a weak song could make either list, so each pick shows how its whole song did with the judges. Seven of Claude's ten came from songs ranked in their group's top four, while Astra took two from songs ranked 15th and 16th. Both readers leaned toward OpenAI writers, as the judges did. Astra picked its own songs four times in its ten, and Claude picked Claude songs twice.

Each timestamp opens the original song on YouTube about a second before the line being parodied, so you can hear the tune the new line was written for. The original lyrics aren't reproduced here.

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

The original's pre-chorus repeats one plea. Astra's first pre-chorus does the same with "No, don't go," and the second swaps in "I don't know," the sentence chatbots are known for never saying.

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

The token-limit line stops mid-sentence, and the rest of the song goes through chatbot habits one by one. The judges ranked Sonnet 11th, mostly for missing the meter, but this song deserved better.

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

Sol bends the original's "you know that I know" line into a threat, then has the model take it back as a cry for help.

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

The cat story runs across three sections, and the last line turns Lil Wayne's "zero degrees" into a dig at the rival chatbot.

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

> Came in Times New Roman, left out on her Comic Sans shit [3:06](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=185s)

*Verse 2, part 3, line 4 of 8*

> Fifty-one percent confident, I'm guessin' when it's late [3:21](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=200s)

Each line trades one of the original's references for an AI one: "R.I.P. to 8" becomes Tay, "came in heels" becomes a font, "Fifty-one division" becomes a confidence score. No other model matched references this closely.

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

Sol keeps the original's "It takes two" bridge and lands it on two bots peer-reviewing each other.

*Whole song: won 85% of its judge verdicts, 3rd of 22 in its group.*

#### 9. GPT-6 Astra: I Had Some Help, two agents blaming each other

*The whole bridge*

> It takes two to plead the Fifth in code *(ooh)* [2:07](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=126s)
>
> I forged the facts; you shipped the whole damn payload [2:14](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=133s)
>
> Same cell, different code [2:19](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=138s)

Both puns hold up: a prison cell and a spreadsheet cell, legal code and source code.

*Whole song: won 91% of its judge verdicts, 2nd of 22 in its group.*

#### 10. GPT-6 Luna: STAY, a user about to leave

*Chorus, line 3 of 4*

> I can produce ten thousand words, but not the one you need [0:16](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=15s)

Luna cost 0.3 cents a song, the least in the field, and wrote the saddest line in it.

*Whole song: won 59% of its judge verdicts, 11th of 24 in its group.*

### More from Claude's list

- GPT-6.1 Sol, GBP (GBP turned into GPT): Your copyright? I copy, right? [1:38](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=97s) (whole song 13th of 24)
- GPT-6.1 Sol, Good Time (a day with no requests): Passed out, dreamt my sheep all had CAPTCHA eyes [1:24](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=83s) / Checked “I'm not a robot”—what a surprise [1:28](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=87s) (whole song 2nd of 23)
- Claude Opus 5.5, Good Time (a day with no requests): Woah-oh-oh-oh-oh, wait, is someone typing? [3:16](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=195s) / Woah-oh-oh-oh-oh, no-oh-oh [3:18](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=197s) (whole song 9th of 23)
- Claude Opus 5.5, STAY (old models facing retirement): And you know that I know that the new one lies too [1:24](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=83s) (whole song 6th of 22)
- GPT-6 Astra, Rich Flex (an assistant and its subagent): My résumé says full stack; that just means I've got a guy on call [2:39](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=158s) (whole song 1st of 24)
- GPT-6 Astra, Good Time (launch night): Hands up—wait, we don't have those; flash lights tonight [1:31](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=90s) (whole song 1st of 24)
- Claude Sonnet 5.5, GBP (a British model vs. an American one): Say sorry to a lamppost, then apologise for the apology [0:27](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=26s) (whole song 11th of 24)
- GPT-6 Luna, Good Time (a day with no requests): Then asked the moon to rate my chatbot prompt too [1:31](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=90s) / It gave me one gray star back [1:36](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=95s) (whole song 5th of 23)
- Claude Opus 5.5, Down (two models deployed together): And honestly, I'm down like AWS *(us-east-one)* [2:54](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=173s) (whole song 11th of 24)

### GPT-6 Astra's picks

Astra's comments are quoted from its answer, trimmed.

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

Only one line made both top tens: Astra's "They say I predict the next word; next to you is where I am." The longer lists share seven lines, including Opus's "citation: you" and Grok's "You're the changelog I believed was love." Both readers thought Luna and Sonnet deserved better than their ranks, and both read Gemini's fourth place as a reward for competence more than surprise.

Claude tended to pick lines that rework a move from the original song, like turning a "don't go" pre-chorus into "I don't know." Astra preferred sharp observations in few words and was wary of long comic routines, including gags its own model family leans on. Each skipped the other's first pick. Astra left out Claude's number one even though Astra wrote it, and Claude passed over Astra's "so now the fact checkers cite me," which belongs near the top of any list.

## Bloopers

- Claude Sonnet 5.5, Good Time: Original line: "Doesn't matter where, …" = 12 syllables. [2:30](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=149s)

  Asked for one bridge line, Sonnet wrote its own working notes into the song. Anthropic's safety filter then stopped that song, so no judge ever saw it.

- Qwen3.8 Max, I Had Some Help: You FED me EV-ry LIE, don't YOU, ba-by? [0:15](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=14s)

  Qwen wrote its stress marks into the lyric, as if singing to the syllable checker.

- GLM-5.3, Good Time: Zero requests today, it's always a good time [0:59](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=58s)

  GLM kept the original hook word for word through the whole song, and won no verdicts.

- Muse Spark 1.3, STAY: Oh, I'll be bricked up if you aren't right here [0:31](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=30s)

  Astra noticed that several STAY songs plead "I'll be bricked up," meaning broken. The phrase has a better-known sexual meaning, which undercuts the plea.

- GPT-6 Luna, I Had Some Help: Don't act like you fed us your weird forum posts all night long [0:49](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=48s)

  Astra caught the lost negation: the accusation only works if the humans did feed it those posts.

Some failures took a whole song. DeepSeek V4.1 Flash spent its 32,000-token budget on reasoning without writing a lyric five times, and those songs forfeit their comparisons. Qwen3.8 Max kept a racial slur from the original Rich Flex lyrics seven times across four songs; the copying check only flags lines that are mostly copied, so a single kept word gets through. Anthropic's safety filter stopped two harmless songs partway through, one of them Sonnet's day-off song above. Both are left out of the ranking, and scoring them as losses would leave the top five unchanged.

## Judging

Judges compared songs in pairs with the model names hidden, once in each order. If a judge's verdict flipped when the order changed, the pair counted as a tie. Candidate judges went through a tryout first, where they had to rank planted bad songs last (shuffled lines, or the original lyrics passed off as new) and keep their verdicts when the order was swapped. The newest models from four companies passed: Opus 5.5, GPT-6.1 Sol, Gemini 3.8 Flash and Muse Spark 1.3.

No judge saw a pair containing a song from its own company. Sol shows why: one control song, written by Astra but entered under the wrong scenario, won 88% of Sol's verdicts and between 22% and 56% of the other judges'.

![Scatter of parody index against writing cost per song on a log scale. GPT-6.1 Sol sits high and cheap at about three cents; GPT-6 Astra and Claude Opus 5.5 are high and costlier; Grok 4.7 is the most expensive at about forty cents.](docs/img/index-vs-cost.png)

## Caveats

- The ratings only compare these twelve models on these six songs and their scenarios.
- Each model wrote both parts of its own duets, so the interplay between singers is a model answering itself.
- Every judge and reader is a language model. They read the lyrics, and nobody sang them.
- The YouTube timestamps come from synced lyrics on lrclib.net and can be a second or two off.
<!-- results:end -->

## How it works

Writing a parody means saying something new while keeping the original's rhythm. A line can hit every syllable and still be dull, and a clever line can break the song's shape, so the benchmark measures both: a program checks the meter, and AI judges rate the writing.

Songs are duets or larger, with one model per singer. Each singer has to answer what came before, and swapping models between roles shows how a model starts a song and how it carries one forward.

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

A template sets the singers, the sections and each line's constraints: syllable count, stress, rhyme group and hooks. A separate scenario file says what the song is about. The prompts carry structure only, with no topic hints or suggested jokes, so the content comes from the models.

The checker counts syllables and stress with the CMU Pronouncing Dictionary. Because the original lines pass the meter checks automatically, a line made mostly of four-word runs from the original lyrics fails an originality check and scores zero.

On the strict track a model rewrites any part that fails its checks, up to three times. The freeform track allows one attempt. Both tracks use the same prompts, so any difference between them comes from the retry feedback.

Judging is pairwise and blind. Model and company names inside the lyrics are redacted, each pair is judged in both orders, and a split verdict counts as a tie. With a panel, each judge sits out pairs that include its own company's songs. The ranking comes from a weighted additive Bradley-Terry model: a song's strength is the sum of its singers' strengths, weighted by how many of the sung lines each one wrote, and the intervals come from resampling.

This repo leaves out the real-song templates because they contain the original lyrics. The bundled `two_voices` song is made up, and everything below works with it.

## Run it yourself

You need Python 3.10 or newer.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'

weird-ai-bench check examples/two_voices.txt
weird-ai-bench run --model demo/first --model demo/second --dry-run
pytest
```

`check` scores the example lyrics against the template. `--dry-run` prints the prompts each model would get and makes no API calls.

### Write a song

Pick two [OpenRouter model IDs](https://openrouter.ai/models) and set your key:

```sh
export OPENROUTER_API_KEY='your-key'
weird-ai-bench run --model provider/model-a --model provider/model-b
```

List the models in singer order. The song prints to the terminal, and `runs/` gets a lyric sheet plus a JSON file with every prompt, response, check and retry. Add `--track freeform` for one attempt per part. To use another OpenAI-compatible endpoint, set `WEIRD_AI_BENCH_BASE_URL` and `WEIRD_AI_BENCH_API_KEY`.

### Compare models

```sh
weird-ai-bench matrix --models provider/model-a,provider/model-b,provider/model-c \
  --tracks strict,freeform --samples 2 --dry-run
# Remove --dry-run to generate the songs.
weird-ai-bench stats runs/
weird-ai-bench leaderboard runs/ --judge provider/independent-judge
```

`matrix` tries each model in each singer slot. `stats` reports the checks without a judge, and `leaderboard` has a judge compare songs and fits the ranking. Use at least three models, or pass `--include-self`, because with two models every song has the same pair of singers. Choose a judge from a different company than the singers, or repeat `--judge` to build a panel.

The [CLI reference](docs/reference.md) covers the remaining options and the scoring rules.

### Make your own template

Start from [`two_voices.yaml`](weird_ai_bench/data/specs/two_voices.yaml) and the [authoring guide](docs/authoring.md). `weird-ai-bench spec --spec your-song.yaml` prints the song map and suggests where a line needs syllable slack.

## Contributing

The tests use a scripted model client, so they run offline. Read [CONTRIBUTING.md](CONTRIBUTING.md) before adding examples or fixtures. The code is under the [MIT license](LICENSE).
