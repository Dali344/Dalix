"""
بوت ديسكورد: تحدي الكلمة (PvP Wordle بالعربي)
------------------------------------------------
- لاعب يتحدى لاعب آخر.
- كل لاعب يرسل كلمته السرية بالـ DM للبوت.
- يتناوبان على التخمين حتى يفوز أحدهما أو تنتهي المحاولات.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

AR_LETTERS_PATTERN = re.compile(r"^[ء-ي]+$")

DIACRITICS = str.maketrans({
    "\u064B": None,"\u064C": None,"\u064D": None,"\u064E": None,"\u064F": None,
    "\u0650": None,"\u0651": None,"\u0652": None,"\u0653": None,"\u0654": None,
    "\u0655": None,"\u0640": None,
})

def normalize_ar(s: str) -> str:
    s = s.translate(DIACRITICS)
    s = s.replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ٱ","ا")
    s = s.replace("ى","ي").replace("ة","ه")
    s = s.replace("ؤ","ء").replace("ئ","ء")
    return s

# تقييم التخمين
def score_guess(target: str, guess: str) -> str:
    t = normalize_ar(target)
    g = normalize_ar(guess)
    result = ["⬛"]*5
    from collections import Counter
    counts = Counter(t)

    for i in range(5):
        if g[i] == t[i]:
            result[i] = "🟩"
            counts[g[i]] -= 1
    for i in range(5):
        if result[i] == "🟩":
            continue
        if counts.get(g[i],0) > 0:
            result[i] = "🟨"
            counts[g[i]] -= 1
    return "".join(result)

# حالة اللعبة
@dataclass
class ChallengeGame:
    player1: int
    player2: int
    word1: Optional[str] = None
    word2: Optional[str] = None
    attempts1: List[Tuple[str,str]] = field(default_factory=list)
    attempts2: List[Tuple[str,str]] = field(default_factory=list)
    turn: int = 1
    over: bool = False
    winner: Optional[int] = None

    def ready(self):
        return self.word1 and self.word2

# البوت
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

CHALLENGES: Dict[int, ChallengeGame] = {}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command(name="challenge")
async def challenge_cmd(ctx: commands.Context, opponent: discord.Member):
    if ctx.channel.id in CHALLENGES:
        await ctx.reply("هناك تحدي جارٍ بالفعل في هذه القناة.")
        return
    if opponent.bot:
        await ctx.reply("لا يمكنك تحدي بوت.")
        return
    game = ChallengeGame(player1=ctx.author.id, player2=opponent.id)
    CHALLENGES[ctx.channel.id] = game
    await ctx.reply(f"🎮 تحدي بدأ بين {ctx.author.mention} و {opponent.mention}!\nكل لاعب يستلم رسالة DM لإرسال كلمته.")
    for pid in [ctx.author, opponent]:
        try:
            await pid.send("أرسل كلمتك السرية (5 حروف عربية).")
        except:
            await ctx.send(f"❌ لم أستطع إرسال DM إلى {pid.mention}، افتح الخاص.")

@bot.command(name="guess")
async def guess_cmd(ctx: commands.Context, *, word: str):
    game = CHALLENGES.get(ctx.channel.id)
    if not game:
        await ctx.reply("لا يوجد تحدي في هذه القناة.")
        return
    word = word.strip()
    if not AR_LETTERS_PATTERN.match(word) or len(normalize_ar(word))!=5:
        await ctx.reply("❌ الكلمة يجب أن تكون عربية من 5 حروف.")
        return
    pid = ctx.author.id
    if game.over:
        await ctx.reply("التحدي انتهى.")
        return
    if pid not in [game.player1, game.player2]:
        await ctx.reply("لست مشاركاً في هذا التحدي.")
        return
    if not game.ready():
        await ctx.reply("بانتظار إدخال كل لاعب كلمته.")
        return
    if (game.turn==1 and pid!=game.player1) or (game.turn==2 and pid!=game.player2):
        await ctx.reply("ليس دورك.")
        return

    target = game.word2 if pid==game.player1 else game.word1
    emojis = score_guess(target, word)
    if pid==game.player1:
        game.attempts1.append((emojis,word))
        game.turn=2
    else:
        game.attempts2.append((emojis,word))
        game.turn=1

    await ctx.send(f"{ctx.author.mention} يخمّن: {word}\n{emojis}")

    if emojis=="🟩🟩🟩🟩🟩":
        game.over=True
        game.winner=pid
        await ctx.send(f"🎉 {ctx.author.mention} خمّن الكلمة بشكل صحيح! فاز بالتحدي.")

@bot.event
async def on_message(message: discord.Message):
    if message.author==bot.user:
        return
    if isinstance(message.channel, discord.DMChannel):
        for cid, game in CHALLENGES.items():
            if game.over:
                continue
            if message.author.id in [game.player1, game.player2]:
                word = message.content.strip()
                if not AR_LETTERS_PATTERN.match(word) or len(normalize_ar(word))!=5:
                    await message.channel.send("❌ الكلمة يجب أن تكون عربية من 5 حروف.")
                    return
                if message.author.id==game.player1:
                    game.word1=word
                else:
                    game.word2=word
                await message.channel.send("✅ تم تسجيل كلمتك.")
                if game.ready():
                    ch=bot.get_channel(cid)
                    if ch:
                        await ch.send(f"✨ الكلمتان تم تسجيلهما. يبدأ <@{game.player1}>.")
    await bot.process_commands(message)

if __name__=="__main__":
    load_dotenv()
    token=os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ ضع التوكن في ملف .env")
