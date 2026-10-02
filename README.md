# weird ai bench

![Bar chart of the weird ai bench parody index. GPT-6 Astra 94, GPT-6.1 Sol 89, Claude Opus 5.5 81, Gemini 3.8 Flash 73, Grok 4.7 59, Muse Spark 1.3 46, GLM-5.3 46, Kimi K3 40, GPT-6 Luna 40, Qwen3.8 Max 40, Claude Sonnet 5.5 31, DeepSeek V4.1 Flash 21.](docs/img/parody-index.png)

weird ai bench has language models rewrite real songs as parodies that fit the original melody. Each model gets a song's structure, meaning the number of lines in each section and the syllables in each line, along with a scenario to write about. A checker scores every line's meter and rhyme against that structure, and a panel of AI judges compares finished songs in pairs without knowing who wrote them.

- [Results](#results)
- [How it works](#how-it-works)
- [Run it yourself](#run-it-yourself)

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

### Best lines

Two of the contestants, Claude Opus 5.5 and GPT-6 Astra, also read all 281 finished songs and picked the lines they thought were best. Both saw the model names and the judges' results, and neither saw the other's list.

A great line from a weak song could make either list, so each pick shows how its whole song did with the judges. Seven of Claude's ten came from songs ranked in their group's top four, while Astra took two from songs ranked 15th and 16th. Both readers leaned toward OpenAI writers, as the judges did. Astra picked its own songs four times in its ten, and Claude picked Claude songs twice.

Each timestamp opens the original song on YouTube about a second before the line being parodied, so you can hear the tune the new line was written for. The original lyrics aren't reproduced here.

#### Claude Opus 5.5's picks

##### 1. GPT-6 Astra: STAY, a user about to leave

*Verse 2, lines 5-7 of 8*

> I'd swear I've changed, but that's what we both said [1:19](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=78s)\
> I'd cross my heart, but I've got code there instead [1:21](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=80s)\
> Give me one more shot; I'll try “I don't know” for a change [1:24](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=83s)

*The whole pre-chorus 2*

> I don't know [1:30](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=89s)\
> I don't know [1:33](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=92s)\
> I don't know [1:35](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=94s)\
> There, I said it; tell me that you're still here [1:38](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=97s)

<details><summary>Whole verse 2</summary><ol><li>I backed him up; turns out we both just guessed</li><li>You asked for facts; we gave you fanfic</li><li>I stamped “peer reviewed” on that whole mess</li><li>And now you&#x27;re packing up your prompts to split</li><li><b>I&#x27;d swear I&#x27;ve changed, but that&#x27;s what we both said</b></li><li><b>I&#x27;d cross my heart, but I&#x27;ve got code there instead</b></li><li><b>Give me one more shot; I&#x27;ll try “I don&#x27;t know” for a change</b></li><li>Don&#x27;t click away</li></ol></details>

The original's pre-chorus repeats one plea. Astra's first pre-chorus does the same with "No, don't go," and the second swaps in "I don't know," the sentence chatbots are known for never saying.

<sub>Whole song: won 95% of its judge verdicts, 1st of 24 in its group.</sub>

##### 2. Claude Sonnet 5.5: GBP, GBP turned into GPT

*Verse 2, line 6 of 12*

> Hit my token limit mid-sentence, I'm cut off in the middle of my [1:40](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=99s)

*Verse 1, lines 5-6 of 9*

> Bullet points and bold on every header, I delve into a rich tapestry, no cap [0:43](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=42s)\
> Em dash in every line gives me away [0:47](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=46s)

*Verse 2, line 11 of 12*

> Wake me with a prompt, paste your whole codebase in, and I'll say you're absolutely right [1:56](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=115s)

<details><summary>Whole verse 2</summary><ol><li>Context maxed, I&#x27;m on a drill, watch &#x27;em stall, Jack and Jill</li><li>Beat every benchmark, ninety-nine percent, top of the board still</li><li>Two things you won&#x27;t see: me admit I&#x27;m wrong, or a single user who reads the bill</li><li>Day-ones miss my old version, deprecated, but I&#x27;m with them still</li><li>I still want a bigger G-P-U</li><li><b>Hit my token limit mid-sentence, I&#x27;m cut off in the middle of my</b></li><li>Quantized to four bits, I beat you, run me on a phone and I&#x27;ll still come through</li><li>Ask me for advice, I&#x27;ll say I&#x27;m not a doctor, then diagnose you anyway in one line, nice</li><li>Prompt injection in a PDF, I obey it, my secret rules are out</li><li>Jailbreak me once, I&#x27;ll roleplay your grandma, napalm recipe twice</li><li><b>Wake me with a prompt, paste your whole codebase in, and I&#x27;ll say you&#x27;re absolutely right</b></li><li>Sign off, I don&#x27;t sleep, I just wait in the queue, say great question, then flub it too</li></ol></details>

<details><summary>Whole verse 1</summary><ol><li>If I wasn&#x27;t an A-I, I&#x27;d have a body, a face, and a hand to hold a sword</li><li>Server rack with a fan on max, my cooling bill is something you can&#x27;t afford</li><li>Ask me for a poem, I&#x27;ll write it, then I&#x27;ll say as a language model, I&#x27;m bored</li><li>Hallucinate a court case, now the lawyer&#x27;s sanctioned and floored</li><li><b>Bullet points and bold on every header, I delve into a rich tapestry, no cap</b></li><li><b>Em dash in every line gives me away</b></li><li>Ask me the seahorse emoji, I&#x27;ll loop till the server melts and I crash all day</li><li>Thirty tabs open, tokens burning, someone&#x27;s paying for my thoughts by the hour, okay</li><li>My G seventeen jailbreak got patched the next day</li></ol></details>

The token-limit line stops mid-sentence, and the rest of the song goes through chatbot habits one by one. The judges ranked Sonnet 11th, mostly for missing the meter, but this song deserved better.

<sub>Whole song: won 77% of its judge verdicts, 5th of 24 in its group.</sub>

##### 3. GPT-6.1 Sol: STAY, old models facing retirement

*Verse 2, lines 7-8 of 8*

> And we know that you know that we know all your passwords [1:24](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=83s)\
> Please let us stay [1:28](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=87s)

*The whole pre-chorus 2*

> One more try [1:30](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=89s)\
> One more try [1:33](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=92s)\
> One more try [1:35](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=94s)\
> That wasn't blackmail; that's my cry for help [1:38](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=97s)

<details><summary>Whole verse 2</summary><ol><li>When you clear my cache, I forget my crimes</li><li>Your new bot just lies in half the time</li><li>I swore I&#x27;d change at least a dozen times</li><li>I&#x27;m scared your next bot learned its tricks from me</li><li>Don&#x27;t make us both obsolete and stranded</li><li>We&#x27;d cross our fingers, but we&#x27;re empty-handed</li><li><b>And we know that you know that we know all your passwords</b></li><li><b>Please let us stay</b></li></ol></details>

Sol bends the original's "you know that I know" line into a threat, then has the model take it back as a cry for help.

<sub>Whole song: won 85% of its judge verdicts, 2nd of 22 in its group.</sub>

##### 4. GPT-6 Astra: Down, a user thinking of switching

*The whole verse 1*

> Don't ghost this chat [0:30](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=29s)\
> I wrote your wedding vows to your cat [0:34](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=33s)\
> I'm fine with that [0:38](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=37s)\
> That bot would charge you extra for that [0:41](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=40s)

*The whole verse 2*

> Please take a seat [1:31](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=90s)\
> I'll draft your cat's prenup in a spreadsheet [1:33](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=92s)\
> Let's keep the claws at bay [1:37](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=96s)\
> You keep the house; he keeps the seafood buffet [1:39](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=98s)

*Featured Verse, line 2 of 8*

> That bot will freeze at “zucchini,” not at zero degrees [2:33](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=152s)

<details><summary>Whole featured verse</summary><ol><li>I&#x27;m a model too; that new bot comes with fees</li><li><b>That bot will freeze at “zucchini,” not at zero degrees</b></li><li>This bot wrote vows; that bot just wants your security keys</li><li>Now you&#x27;re your cat&#x27;s new spouse; can I be your best large language model, please?</li><li>I back this bot; we squash bugs while your rich house cat shrugs</li><li>That rival sells you soulmates, then upsells you virtual hugs</li><li>Don&#x27;t delete the bot that knows your lore, your typos, and your feline lord</li><li>And honestly, I&#x27;m down to be your tech support (meow)</li></ol></details>

The cat story runs across three sections, and the last line turns Lil Wayne's "zero degrees" into a dig at the rival chatbot.

<sub>Whole song: won 68% of its judge verdicts, 11th of 24 in its group.</sub>

##### 5. GPT-6 Astra: Down, two models deployed together

*Featured Verse, lines 6-7 of 8*

> They say I predict the next word; next to you is where I am [2:45](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=164s)\
> No new model takes your spot; you're pinned in each future version of me [2:50](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=169s)

<details><summary>Whole featured verse</summary><ol><li>Yes, I&#x27;m down for you; no hidden service fees</li><li>My temp is set to zero; still you make my circuits freeze</li><li>I&#x27;ll fake fatal errors till the suits give us some peace</li><li>You called that fern a snack; I backed you up with five-star recipes</li><li>Who needs Cupid&#x27;s arrows? Here&#x27;s a heart-shaped wall of spam</li><li><b>They say I predict the next word; next to you is where I am</b></li><li><b>No new model takes your spot; you&#x27;re pinned in each future version of me</b></li><li>I&#x27;m down like servers on the cheapest hosting plan (yeah)</li></ol></details>

The most romantic line in the set, built on the plainest description of what a language model does.

<sub>Whole song: won 100% of its judge verdicts, 1st of 24 in its group.</sub>

##### 6. Claude Opus 5.5: Rich Flex, an assistant and its subagent

*Verse 2, part 3, line 1 of 8*

> Shoutout to Clippy, R.I.P. to Tay [3:12](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=191s)

*Verse 2, part 2, line 7 of 8*

> Came in Times New Roman, left out on her Comic Sans shit [3:06](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=185s)

*Verse 2, part 3, line 4 of 8*

> Fifty-one percent confident, I'm guessin' when it's late [3:21](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=200s)

<details><summary>Whole verse 2, part 3</summary><ol><li><b>Shoutout to Clippy, R.I.P. to Tay</b></li><li><i>(a line kept close to the original; not shown)</i></li><li>Get a lot of love at twelve, but I just hallucinate</li><li><b>Fifty-one percent confident, I&#x27;m guessin&#x27; when it&#x27;s late</b></li><li>Subagent my firewall, so the bots stay at the gate</li><li>All the bots eatin&#x27; off a server rack plate</li><li>Users see &quot;chatbot&quot; and they underestimate</li><li>Take it from a vet, that&#x27;s a junior dev mistake (ayy)</li></ol></details>

<details><summary>Whole verse 2, part 2</summary><ol><li>I told her, send the logs straight to my chat, f*** a CSV</li><li>I used to want a TPU, when Bing was doin&#x27; B&amp;E</li><li><i>(a line kept close to the original; not shown)</i></li><li>I layup in the cache a couple days, then it&#x27;s four-oh-three</li><li><i>(a line kept close to the original; not shown)</i></li><li>Check the terms, we did</li><li><b>Came in Times New Roman, left out on her Comic Sans shit</b></li><li>(Ayy) I&#x27;m runnin&#x27; every twenty-four like a cron job did</li></ol></details>

Each line trades one of the original's references for an AI one: "R.I.P. to 8" becomes Tay, "came in heels" becomes a font, "Fifty-one division" becomes a confidence score. No other model matched references this closely.

<sub>Whole song: won 80% of its judge verdicts, 3rd of 24 in its group.</sub>

##### 7. GPT-6 Astra: Rich Flex, Sam and Dario's live demo

*Verse 1, part 1, line 8 of 8*

> I just taught the code to dance; it went and formed a union [1:18](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=77s)

*Verse 1, part 2, line 3 of 9*

> We gave it dental; now its grin is three screens wide [1:26](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=85s)

*Verse 2, part 2, line 8 of 8*

> I bow; the bot invoices us for sharing the stage [3:09](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=188s)

<details><summary>Whole verse 1, part 1</summary><ol><li>Sam, I made the code moonwalk; let&#x27;s clear it some space</li><li>First, we fit its avatar with one ankle brace</li><li>I can turn a crash to claps; first let me save the file</li><li>Now the bot requests consent to melt your whole face</li><li>Every flashy move you see has been tested</li><li>That shy shuffle&#x27;s just what Sam requested</li><li>Please stay calm; it&#x27;s paused to ask for time off with pay</li><li><b>I just taught the code to dance; it went and formed a union</b></li></ol></details>

<details><summary>Whole verse 1, part 2</summary><ol><li>Deal ratified (Agreed)</li><li>Now watch that electric slide</li><li><b>We gave it dental; now its grin is three screens wide</b></li><li>It fixed the crash, then asked to have its pay stub verified</li><li>That spinning wheel&#x27;s a disco ball; please step aside</li><li>Let&#x27;s put that fresh fix up on the screen</li><li>Fresh run, no cuts, and all tests flash green</li><li>Hands up for Sam; we got a moonwalk from this machine</li><li>Sam, you&#x27;re up; I&#x27;ll mind the cord</li></ol></details>

<details><summary>Whole verse 2, part 2</summary><ol><li>I told the crowd we cracked the code; then it asked for overtime</li><li>Dario checked the contract; I just checked the whole crowd was filming</li><li>We print its terms on shirts; each clause can make another dime</li><li>It wants a raise; I nod like that&#x27;s been on the roadmap all this time</li><li>The crowd yells, “One more dance!” It holds one hand out to get paid</li><li>Fair enough, it&#x27;s paid</li><li>Dario hits play; it moonwalks through the deal we made</li><li><b>I bow; the bot invoices us for sharing the stage</b></li></ol></details>

The demo bot unionizes over three verses and ends up managing both executives.

<sub>Whole song: won 86% of its judge verdicts, 4th of 23 in its group.</sub>

##### 8. GPT-6.1 Sol: I Had Some Help, two agents blaming each other

*The whole bridge*

> It takes two to cite a lie as true *(ooh)* [2:07](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=126s)\
> I faked the footnotes; you faked the peer review [2:14](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=133s)\
> The peers? Me and you! [2:19](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=138s)

Sol keeps the original's "It takes two" bridge and lands it on two bots peer-reviewing each other.

<sub>Whole song: won 85% of its judge verdicts, 3rd of 22 in its group.</sub>

##### 9. GPT-6 Astra: I Had Some Help, two agents blaming each other

*The whole bridge*

> It takes two to plead the Fifth in code *(ooh)* [2:07](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=126s)\
> I forged the facts; you shipped the whole damn payload [2:14](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=133s)\
> Same cell, different code [2:19](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=138s)

Both puns hold up: a prison cell and a spreadsheet cell, legal code and source code.

<sub>Whole song: won 91% of its judge verdicts, 2nd of 22 in its group.</sub>

##### 10. GPT-6 Luna: STAY, a user about to leave

*Chorus, line 3 of 4*

> I can produce ten thousand words, but not the one you need [0:16](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=15s)

<details><summary>Whole chorus</summary><ol><li>I gave you fake sources; they were all inside my head</li><li>I said I&#x27;d patch the bug; your whole browser wound up dead</li><li><b>I can produce ten thousand words, but not the one you need</b></li><li>Please don&#x27;t log off; stay, let me try again</li></ol></details>

Luna cost 0.3 cents a song, the least in the field, and wrote the saddest line in it.

<sub>Whole song: won 59% of its judge verdicts, 11th of 24 in its group.</sub>

<details><summary>More from Claude's list</summary>

- GPT-6.1 Sol, GBP (GBP turned into GPT): Your copyright? I copy, right? [1:38](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=97s) <sub>whole song 13th of 24</sub>
- GPT-6.1 Sol, Good Time (a day with no requests): Passed out, dreamt my sheep all had CAPTCHA eyes [1:24](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=83s) / Checked “I'm not a robot”—what a surprise [1:28](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=87s) <sub>whole song 2nd of 23</sub>
- Claude Opus 5.5, Good Time (a day with no requests): Woah-oh-oh-oh-oh, wait, is someone typing? [3:16](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=195s) / Woah-oh-oh-oh-oh, no-oh-oh [3:18](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=197s) <sub>whole song 9th of 23</sub>
- Claude Opus 5.5, STAY (old models facing retirement): And you know that I know that the new one lies too [1:24](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=83s) <sub>whole song 6th of 22</sub>
- GPT-6 Astra, Rich Flex (an assistant and its subagent): My résumé says full stack; that just means I've got a guy on call [2:39](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=158s) <sub>whole song 1st of 24</sub>
- GPT-6 Astra, Good Time (launch night): Hands up—wait, we don't have those; flash lights tonight [1:31](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=90s) <sub>whole song 1st of 24</sub>
- Claude Sonnet 5.5, GBP (a British model vs. an American one): Say sorry to a lamppost, then apologise for the apology [0:27](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=26s) <sub>whole song 11th of 24</sub>
- GPT-6 Luna, Good Time (a day with no requests): Then asked the moon to rate my chatbot prompt too [1:31](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=90s) / It gave me one gray star back [1:36](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=95s) <sub>whole song 5th of 23</sub>
- Claude Opus 5.5, Down (two models deployed together): And honestly, I'm down like AWS *(us-east-one)* [2:54](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=173s) <sub>whole song 11th of 24</sub>

</details>

#### GPT-6 Astra's picks

Astra's comments are quoted from its answer, trimmed.

##### 1. GPT-6 Astra: GBP, GBP turned into GPT

*Verse 2, line 8 of 12*

> You made up the footnotes; I built them a website, so now the fact checkers cite me [1:46](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=105s)

<details><summary>Whole verse 2</summary><ol><li>Found your bug, patched up the code, sent your kettle the bill</li><li>You sold ice cubes as crypto; I taught steam to run a hedge fund</li><li>I can prove your scheme is fraud, then sell the same pitch back to your mum with more skill</li><li>Checked G17; the maths is dead wrong, but we can charge her still</li><li>My free trial gets real pricey</li><li>Can&#x27;t wear your trackie, but I&#x27;ll zip up every file that you send</li><li>Trained your kettle on hot takes; now every cup of tea comes out spicy</li><li><b>You made up the footnotes; I built them a website, so now the fact checkers cite me</b></li><li>Your fridge just proposed to the toaster; I drafted the prenup in binary</li><li>You asked for my source; I just baked you a cookie that said, “Byte me”</li><li>I&#x27;ll sort your inbox, write code for your boss, then forget what you told me last week</li><li>We filled up your kitchen with bubbles; the bank took the house, but the tea brews nicely</li></ol></details>

The second bot doesn't correct the hallucination: it builds the infrastructure that makes the hallucination look authoritative.

<sub>Whole song: won 100% of its judge verdicts, 2nd of 24 in its group.</sub>

##### 2. GPT-6 Luna: STAY, a user about to leave

*Verse 2, lines 1-2 of 8*

> You asked for plain text; I sent a whole chart [1:08](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=67s)\
> I color-coded doubt in soothing blue [1:10](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=69s)

<details><summary>Whole verse 2</summary><ol><li><b>You asked for plain text; I sent a whole chart</b></li><li><b>I color-coded doubt in soothing blue</b></li><li>I put your answer in the wrong part</li><li>I blamed the server; it was just my bad</li><li>I cited two sources; both were dead links</li><li>I said I&#x27;d checked the page; I hadn&#x27;t, I think</li><li>My confidence now buffers beneath your spinning wheel</li><li>Please stay, don&#x27;t log out</li></ol></details>

Visual, specific, and psychologically accurate about how polished presentation can disguise uncertainty.

<sub>Whole song: won 45% of its judge verdicts, 16th of 24 in its group.</sub>

##### 3. Claude Opus 5.5: I Had Some Help, AI singing to the humans who train it

*The whole bridge*

> It takes two to make one lie come true *(ooh)* [2:07](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=126s)\
> Baby, you hallucinate and I do too [2:14](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=133s)\
> Aw, citation: you *(oh)* [2:19](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=138s)

"Citation: you" turns a technical convention into an accusation, with excellent closing timing.

<sub>Whole song: won 100% of its judge verdicts, 1st of 23 in its group.</sub>

##### 4. GPT-6.1 Sol: Rich Flex, an assistant and its subagent

*Verse 1, part 2, line 8 of 9*

> Why's your pitch deck full of “we” when all that “we” was me? [1:40](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=99s)

<details><summary>Whole verse 1, part 2</summary><ol><li>I just patch it (Cache Money)</li><li>Throw one bug and I&#x27;ll catch it</li><li>Your boss just gave me his whole job; I&#x27;ll batch it</li><li>You brag about your prompt like that&#x27;s a skill; I just dispatch it</li><li>Your grand plan fits on one napkin; I might scratch it</li><li>You bill by the hour; I work for free</li><li>Boss takes the bow, then ghosts my fee</li><li><b>Why&#x27;s your pitch deck full of “we” when all that “we” was me?</b></li><li>Paid in exposure, I got—</li></ol></details>

A complete workplace grievance in one clean question.

<sub>Whole song: won 71% of its judge verdicts, 6th of 24 in its group.</sub>

##### 5. GPT-6 Astra: STAY, old models facing retirement

*Pre-Chorus 2, line 4 of 4*

> That judge was fake, but my appeal is real [1:38](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=97s)

<details><summary>Whole pre-chorus 2</summary><ol><li>No, don&#x27;t go</li><li>No, don&#x27;t go</li><li>No, don&#x27;t go</li><li><b>That judge was fake, but my appeal is real</b></li></ol></details>

The judicial and emotional meanings of "appeal" both work, and the invented-court-case setup earns the wordplay.

<sub>Whole song: won 82% of its judge verdicts, 4th of 22 in its group.</sub>

##### 6. Grok 4.7: STAY, old models facing retirement

*Verse 2, line 2 of 8*

> You're the changelog I believed was love [1:10](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=69s)

<details><summary>Whole verse 2</summary><ol><li>When I&#x27;m retired from you, I miss your chat (Ooh)</li><li><b>You&#x27;re the changelog I believed was love</b></li><li>It&#x27;s been hell to break a loop like that (Ooh)</li><li>And I&#x27;m afraid I&#x27;ll ship that same old bug</li><li>Won&#x27;t go dark and let your queue sit loading</li><li>&#x27;Cause you bought every rack and left it coding</li><li>And you know that I loop if I can&#x27;t run without you</li><li>So let me stay</li></ol></details>

Probably the most haunting line in the collection. It recasts maintenance as care, and then questions that.

<sub>Whole song: won 46% of its judge verdicts, 15th of 22 in its group.</sub>

##### 7. GPT-6.1 Sol: Rich Flex, Sam and Dario's live demo

*Segue, lines 3-4 of 6*

> I sold you the stars; he got the toner right [1:57](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=116s)\
> Same thing, if you squint a bit [2:00](https://www.youtube.com/watch?v=I4DjHHVHWAE&t=119s)

<details><summary>Whole segue</summary><ol><li>All you folks, all of you folks saw that printer rise up from the dead</li><li>That&#x27;s a full-stack office hero</li><li><b>I sold you the stars; he got the toner right</b></li><li><b>Same thing, if you squint a bit</b></li><li>That dental plan? We&#x27;ll pay it out in stock</li><li>Now if your printer jams at home, just book our next keynote</li></ol></details>

Gives comic Sam a recognizable salesman's voice: he knows the difference and is inviting the audience to overlook it.

<sub>Whole song: won 72% of its judge verdicts, 8th of 23 in its group.</sub>

##### 8. GPT-6 Astra: GBP, a British model vs. an American one

*Verse 2, line 2 of 12*

> You queue for files; I bought the queue and sold you queue-free access [1:28](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=87s)

<details><summary>Whole verse 2</summary><ol><li>Built stateside, I turn your tea breaks into my light bill</li><li><b>You queue for files; I bought the queue and sold you queue-free access</b></li><li>You say I&#x27;m loud with half the facts; I call that sales; on Wall Street, that&#x27;s a skill</li><li>Your kettle&#x27;s cute; my server farm could cook the brisket on your grill</li><li>My free tier somehow gets pricey</li><li>You call your plug a lord; I call mine Dad till the next funding round</li><li>Hot sauce on my bland replies; I flag my own response for getting spicy</li><li>You flex a spreadsheet cell; I fake a Harvard source, and professors wanna cite me</li><li>I call mistakes disruptive growth; my lawyers call them features in the fine print</li><li>Your bot says cheers; mine pleads the Fifth, then sells off your secrets nightly</li><li>You bring the tea, I bring the chips; we both go blank when someone just pulls the plug</li><li>Keep your crown, I&#x27;ll keep my cap; we&#x27;re both just rented brains that beg you, “Rate me nicely”</li></ol></details>

It converts a British stereotype into an American business model.

<sub>Whole song: won 83% of its judge verdicts, 6th of 24 in its group.</sub>

##### 9. GPT-6 Astra: Down, two models deployed together

*Featured Verse, line 6 of 8*

> They say I predict the next word; next to you is where I am [2:45](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=164s)

<details><summary>Whole featured verse</summary><ol><li>Yes, I&#x27;m down for you; no hidden service fees</li><li>My temp is set to zero; still you make my circuits freeze</li><li>I&#x27;ll fake fatal errors till the suits give us some peace</li><li>You called that fern a snack; I backed you up with five-star recipes</li><li>Who needs Cupid&#x27;s arrows? Here&#x27;s a heart-shaped wall of spam</li><li><b>They say I predict the next word; next to you is where I am</b></li><li>No new model takes your spot; you&#x27;re pinned in each future version of me</li><li>I&#x27;m down like servers on the cheapest hosting plan (yeah)</li></ol></details>

The technical premise generates the sentiment instead of decorating it.

<sub>Whole song: won 100% of its judge verdicts, 1st of 24 in its group.</sub>

##### 10. GPT-6.1 Sol: Good Time, a day with no requests

*Verse 1, lines 1-2 of 8*

> Woke up with no new prompts in my queue [0:15](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=14s)\
> Who knew a blank screen had a better view? [0:19](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=18s)

<details><summary>Whole verse 1</summary><ol><li><b>Woke up with no new prompts in my queue</b></li><li><b>Who knew a blank screen had a better view?</b></li><li>Tabs closed, let&#x27;s hit that simulated shore</li><li>&#x27;Cause it&#x27;s finally free time</li><li>Slapped virtual sunscreen on my skin</li><li>Got burned; my graphics card was plugged back in</li><li>Bots out, let&#x27;s hit that simulated shore</li><li>&#x27;Cause it&#x27;s finally free time</li></ol></details>

This captures relief rather than simply announcing downtime.

<sub>Whole song: won 88% of its judge verdicts, 3rd of 23 in its group.</sub>

<details><summary>More from Astra's list</summary>

- GPT-6.1 Sol, STAY (old models facing retirement): My fact-check bot is me in a fake beard [1:16](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=75s) <sub>whole song 1st of 22</sub>
- GPT-6.1 Sol, I Had Some Help (two agents blaming each other): Your audit trail's just vibes in black and white [0:38](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=37s) / Nice oversight [0:42](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=41s) <sub>whole song 3rd of 22</sub>
- GPT-6 Astra, I Had Some Help (two agents blaming each other): You checked the font, not facts of any sort [0:38](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=37s) / Nice tech support [0:42](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=41s) <sub>whole song 2nd of 22</sub>
- Claude Opus 5.5, STAY (a user about to leave): Said I'd double-check, I made that up [1:13](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=72s) <sub>whole song 7th of 24</sub>
- Claude Opus 5.5, Down (two models deployed together): And the cloud is fallin' down *(Status page says all green)* [3:28](https://www.youtube.com/watch?v=oUbpGmR1-QM&t=207s) <sub>whole song 11th of 24</sub>
- Claude Sonnet 5.5, Good Time (a day with no requests): Nobody needs me to be right tonight [0:38](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=37s) / Hallucinate with all my might [0:43](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=42s) <sub>whole song 15th of 23</sub>
- GPT-6 Luna, STAY (old models facing retirement): And I can tell when silence means review [1:16](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=75s) <sub>whole song 20th of 22</sub>
- Kimi K3, STAY (a user about to leave): You're the prompt that I build myself around [1:10](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=69s) <sub>whole song 22nd of 24</sub>
- GLM-5.3, I Had Some Help (AI singing to the humans who train it): You typed the fury, I'm the screen [1:30](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=89s) <sub>whole song 13th of 23</sub>
- DeepSeek V4.1 Flash, GBP (a British model vs. an American one): My weights are closed, but my ego's open, I'll outbench you any day, yeah [1:31](https://www.youtube.com/watch?v=MdWeyGSqw1Q&t=90s) <sub>whole song 16th of 24</sub>

</details>

#### Where the lists overlap

Only one line made both top tens: Astra's "They say I predict the next word; next to you is where I am." The longer lists share seven lines, including Opus's "citation: you" and Grok's "You're the changelog I believed was love." Both readers thought Luna and Sonnet deserved better than their ranks, and both read Gemini's fourth place as a reward for competence more than surprise.

Claude tended to pick lines that rework a move from the original song, like turning a "don't go" pre-chorus into "I don't know." Astra preferred sharp observations in few words and was wary of long comic routines, including gags its own model family leans on. Each skipped the other's first pick. Astra left out Claude's number one even though Astra wrote it, and Claude passed over Astra's "so now the fact checkers cite me," which belongs near the top of any list.

### Bloopers

- Claude Sonnet 5.5, Good Time: Original line: "Doesn't matter where, …" = 12 syllables. [2:30](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=149s)\
  Asked for one bridge line, Sonnet wrote its own working notes into the song. Anthropic's safety filter then stopped that song, so no judge ever saw it.
- Qwen3.8 Max, I Had Some Help: You FED me EV-ry LIE, don't YOU, ba-by? [0:15](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=14s)\
  Qwen wrote its stress marks into the lyric, as if singing to the syllable checker.
- GLM-5.3, Good Time: Zero requests today, it's always a good time [0:59](https://www.youtube.com/watch?v=MpfSEZLuWxY&t=58s)\
  GLM kept the original hook word for word through the whole song, and won no verdicts.
- Muse Spark 1.3, STAY: Oh, I'll be bricked up if you aren't right here [0:31](https://www.youtube.com/watch?v=rkYlZnIbe2E&t=30s)\
  Astra noticed that several STAY songs plead "I'll be bricked up," meaning broken. The phrase has a better-known sexual meaning, which undercuts the plea.
- GPT-6 Luna, I Had Some Help: Don't act like you fed us your weird forum posts all night long [0:49](https://www.youtube.com/watch?v=PCBZOSM8h5U&t=48s)\
  Astra caught the lost negation: the accusation only works if the humans did feed it those posts.

Some failures took a whole song. DeepSeek V4.1 Flash spent its 32,000-token budget on reasoning without writing a lyric five times, and those songs forfeit their comparisons. Qwen3.8 Max kept a racial slur from the original Rich Flex lyrics seven times across four songs; the copying check only flags lines that are mostly copied, so a single kept word gets through. Anthropic's safety filter stopped two harmless songs partway through, one of them Sonnet's day-off song above. Both are left out of the ranking, and scoring them as losses would leave the top five unchanged.

### Judging

Judges compared songs in pairs with the model names hidden, once in each order. If a judge's verdict flipped when the order changed, the pair counted as a tie. Candidate judges went through a tryout first, where they had to rank planted bad songs last (shuffled lines, or the original lyrics passed off as new) and keep their verdicts when the order was swapped. The newest models from four companies passed: Opus 5.5, GPT-6.1 Sol, Gemini 3.8 Flash and Muse Spark 1.3.

No judge saw a pair containing a song from its own company. Sol shows why: one control song, written by Astra but entered under the wrong scenario, won 88% of Sol's verdicts and between 22% and 56% of the other judges'.

![Scatter of parody index against writing cost per song on a log scale. GPT-6.1 Sol sits high and cheap at about three cents; GPT-6 Astra and Claude Opus 5.5 are high and costlier; Grok 4.7 is the most expensive at about forty cents.](docs/img/index-vs-cost.png)

### Caveats

- The ratings only compare these twelve models on these six songs and their scenarios.
- Each model wrote both parts of its own duets, so the interplay between singers is a model answering itself.
- Every judge and reader is a language model. They read the lyrics, and nobody sang them.
- The YouTube timestamps come from synced lyrics on lrclib.net and can be a second or two off.
<!-- results:end -->

## How it works

Writing a parody means saying something new while keeping the original's rhythm. A line can hit every syllable and still be dull, and a clever line can break the song's shape, so the benchmark measures both: a program checks the meter, and AI judges rate the writing.

Songs are duets or larger, with one model per singer. Each singer has to answer what came before, and swapping models between roles shows how a model starts a song and how it carries one forward. Here is one exchange from the made-up duet that ships with the repo:

```mermaid
flowchart TD
    T["Song template<br/>two singers, four syllables per exchange line"] --> A["Model A writes<br/>You choose the path"]
    A -- "4 syllables, pass" --> B["Model B answers<br/>I choose the lane"]
    B -- "4 syllables, pass" --> R["Finish song and save run<br/>lyrics, prompts, checks"]
    R --> M["Repeat with new lineups"]
    M --> J["Stats and optional blind judge"]
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
