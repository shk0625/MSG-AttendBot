import asyncio
from datetime import datetime

from pytz import timezone  # loop
from config import timezone # timezone

import connection
from dotenv import load_dotenv
import os

import discord
from discord.ext import commands
from discord.ext import tasks  # loop

bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())
load_dotenv()

token = os.getenv('AttendBot_TOKEN')
channel_id = os.getenv('Test_Channel')  # test channel

connection = connection.Connection()
conn, cur = connection.getConnection()

server_database_connections = {}  # 서버 ID 별로 데이터베이스 연결을 관리하기 위한 딕셔너리


@tasks.loop(hours=24)
async def routine():
    tz = timezone(timezone)
    now = datetime.now(tz)

    if now.hour == 18 and now.minute == 40:
        channel = bot.get_channel(int(channel_id))
        embed = discord.Embed(title="**출석체크 하세요**!!!!!!",
                              description="포인트가 얻고 싶지 않으신가요?\n\n순위표에 1등 한 번 찍어보셔야죠?\n\n이 쉬운걸.. 안 해?\n\n"
                              , color=0xffc0cb)
        await channel.send(embed=embed)


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    channel = bot.get_channel(int(channel_id))

    if channel:
        command = bot.get_command("도움말")
        if command:
            await command.callback(channel)


@bot.event
async def on_message(message):
    if bot.user.mentioned_in(message):
        for mention in message.mentions:
            if mention.name == "당신은 출석이 하고싶다.":
                await message.channel.send(f'> 등장! 💫💫💫💫💫💫')
                break

    await bot.process_commands(message)


@bot.command(name="안녕")
async def testHello(ctx):
    await ctx.channel.send(f'{ctx.message.author.mention}님, 나도 안녕!', reference=ctx.message)


@bot.command(aliases=['독촉', 'dc'])  # 출석 체크 여부 파악 후 독촉 기능 수행
async def follow(ctx, user: discord.Member):
    conn, cur = connection.getConnection()

    sql = "SELECT * FROM attend WHERE did=%s"
    cur.execute(sql, (str(ctx.author.id),))
    rs = cur.fetchone()

    if rs is None:
        await ctx.send(f"{ctx.author.mention}님 본인부터 출석체크하세요!")
        return

    sql = "SELECT * FROM attend WHERE did=%s"
    cur.execute(sql, (str(user.id),))
    rs = cur.fetchone()

    if rs is not None:
        await ctx.send(f"{ctx.author.display_name}님 좀 느린듯?, {user.display_name}님은 이미 출석함ㅋ ")
    else:
        await user.send(f"> {user.mention}님, 출석과 데일리가 어려운 게 아닌데.. 아직도..")


@bot.command(aliases=['알람', 'al'])
async def alarm(ctx, duration: int = None, member: discord.Member = None):
    if member is not None:
        await ctx.send("> 다른 사용자의 알람을 설정할 수 없습니다.")
        return

    if duration is None or duration not in [3, 5, 7]:
        await ctx.send("> 3, 5, 7분 뒤 재알람만 가능합니다.`/알람 3` 형식으로 입력해주세요.")
        return

    await ctx.send(f"> {ctx.message.author.mention}님, {duration}분 후에 재알람 설정이 되었습니다. **출석**과 **데일리**를 성실하게 해주세요 오늘도 파이팅 "
                   f"٩( ᐛ )و")
    await asyncio.sleep(duration * 60)
    await ctx.author.send(f"> {ctx.message.author.mention}님, {duration}분이 지났습니다. `/출석`, `/작성` 명령어를 사용하세요.\n"
                          f"도움이 필요하다면 `/hp`명령어를 사용하세요.")


@bot.command(aliases=['출석', 'aa'])
async def attend(ctx, member: discord.Member = None):
    conn, cur = connection.getConnection()

    if member is not None:
        await ctx.channel.send("> 다른 사용자의 출석을 기록할 수 없습니다.")
        return

    sql = "SELECT * FROM attend WHERE did=%s"
    cur.execute(sql, (str(ctx.author.id),))
    rs = cur.fetchone()
    today = datetime.now().strftime('%Y-%m-%d')

    sql = "SELECT * FROM daily WHERE did=%s AND day=%s"
    cur.execute(sql, (str(ctx.author.id), today))
    daily_rs = cur.fetchone()

    if rs is not None and str(rs.get('date')) == today:
        if daily_rs is None:
            await ctx.channel.send(f'> {ctx.author.display_name}님은 이미 출석체크를 했어요. 데일리를 작성해주세요!')
        elif daily_rs is not None:
            await ctx.channel.send(f'> {ctx.author.display_name}님은 이미 출석체크를 했어요.')
        return

    if rs is None:
        sql = "INSERT INTO attend (did, count, date) values (%s, %s, %s)"
        cur.execute(sql, (str(ctx.author.id), 1, today))
        conn.commit()

        if daily_rs is not None:
            await ctx.channel.send(f'> {ctx.author.display_name}님의 출석이 확인되었어요!')
        elif daily_rs is None:
            await ctx.channel.send(f'> {ctx.author.display_name}님 출석을 완료했으니 데일리를 작성해주세요!')

    else:
        sql = 'UPDATE attend SET count=%s, date=%s WHERE did=%s'
        cur.execute(sql, (rs['count'] + 1, today, str(ctx.author.id)))
        conn.commit()

        if daily_rs is not None:
            await ctx.channel.send(f'> {ctx.author.display_name}님의 출석이 확인되었어요!')
        elif daily_rs is None:
            await ctx.channel.send(f'> {ctx.author.display_name}님 출석을 완료했으니 데일리를 작성해주세요!')


@bot.command(aliases=['포인트', 'pp'])
async def point(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    conn, cur = connection.getConnection()
    sql = f"SELECT * FROM attend WHERE did=%s"
    cur.execute(sql, (str(member.id),))
    rs = cur.fetchone()
    if rs is None:
        await ctx.send(f"> **{member.display_name}**님, 출석 기록이 없습니다.")
    else:
        count = rs['count']
        base_point = count * 10  # 출석 횟수에 따라 10점씩 적립
        bonus_point = count // 5 * 20  # 5의 배수일 때 20점씩 추가 적립
        total_point = base_point + bonus_point
        print("attend point", total_point)
        await ctx.send(f"> **{member.display_name}**님의 현재 출석 포인트는 {total_point}점입니다.")
        update_sql = "UPDATE attend SET point = %s WHERE did = %s"
        cur.execute(update_sql, (total_point, str(member.id)))
        conn.commit()

    today = datetime.now().strftime('%Y-%m-%d')
    sql_attend = f"SELECT * FROM attend WHERE did = %s AND date = %s"
    cur.execute(sql_attend, (str(member.id), today))
    rs_attend = cur.fetchone()

    if rs_attend is not None:
        current_point = rs_attend['point'] if rs_attend['point'] else 0
        new_point = current_point + 10

        update_sql = "UPDATE attend SET point = %s WHERE did = %s AND date = %s"
        cur.execute(update_sql, (new_point, str(member.id), today))
        conn.commit()
        print("daily point", new_point)
        await ctx.channel.send(f"{member.display_name}님의 {new_point}점 데일리 포인트가 입니다.")
    else:
        await ctx.channel.send("오늘 데일리 작성을 하지 않았습니다.")


@bot.command(aliases=['순위', 'rk'])
async def ranking(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    conn, cur = connection.getConnection()

    guild_id = ctx.guild.id
    if guild_id not in server_database_connections:
        # 새로운 서버의 경우 데이터베이스 연결 설정
        server_database_connections[guild_id] = connection.getConnection()

    guild_members = [member.id for member in ctx.guild.members]

    sql = f"SELECT * FROM attend WHERE did IN ({', '.join(['%s'] * len(guild_members))}) ORDER BY point DESC LIMIT 5"
    cur.execute(sql, guild_members)
    result = cur.fetchall()

    embed = discord.Embed(title="🏆 순위표 🏆", color=discord.Color.blue())
    for index, row in enumerate(result):
        user = bot.get_user(int(row['did']))
        if user:
            embed.add_field(name=f"현재 {index + 1}등 !!! ", value=f"{user.display_name}\n  POINT: **{row['point']}**점",
                            inline=False)

    await ctx.send(embed=embed)

    today = datetime.now().strftime('%Y-%m-%d')
    sql = "SELECT * FROM attend WHERE did=%s AND date=%s"
    cur.execute(sql, (str(member.id), today))
    rs = cur.fetchone()

    sql = f"SELECT * FROM attend WHERE did IN ({', '.join(['%s'] * len(guild_members))}) ORDER BY point"
    cur.execute(sql, guild_members)
    rs2 = cur.fetchall()

    if rs is None:
        print("랭킹 출석체크 여부", rs)
        await ctx.send(f"**{member.display_name}**님, 출석체크부터 할까요?")
    else:
        index = next((i for i, v in enumerate(rs2) if v['did'] == str(member.id)), None)
        if index is not None:
            if index < 1:
                await ctx.send(
                    f"🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏\n# {member.mention}님은 {index + 1}등\n🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏🎉👏")
            if 0 < index < 5:
                await ctx.send(f"**{member.display_name}**님은 순위표 내에 있어요! {index + 1}등이에요.")
            elif any(row['did'] == str(member.id) for row in rs2[5:]):
                await ctx.send(
                    f"엇 **{member.mention}**님의 순위는 **{index + 1}**등입니다. 허접이네요ㅋ")


@bot.command(aliases=['데일리', '기록', 'da'])
async def daily(ctx, *, content: str):
    conn, cur = connection.getConnection()

    today = datetime.now().strftime('%Y-%m-%d')

    cur.execute("INSERT INTO daily (did, todays, day) VALUES (%s, %s, %s)", (str(ctx.author.id), content, today))
    conn.commit()

    cur.execute("SELECT * FROM daily WHERE did = %s", (str(ctx.author.id),))
    all_entries = cur.fetchall()

    embed = discord.Embed(title="데일리 기록", description=f"**{ctx.author.display_name}**님의 데일리 목록",
                          color=discord.Color.purple())
    for entry in all_entries:
        embed.add_field(name=f"작성일: {entry['day']}", value=f"내용: {entry['todays']}", inline=False)

    await ctx.channel.send(embed=embed)


@bot.command(aliases=['삭제', '데일리삭제', 'dd'])
async def daily_delete(ctx):
    conn, cur = connection.getConnection()

    cur.execute("SELECT * FROM daily WHERE did = %s", (str(ctx.author.id),))
    existing_daily = cur.fetchone()

    if not existing_daily:
        await ctx.channel.send(f"> {ctx.author.display_name}님은 아직 데일리를 작성하지 않았습니다!")
        return

    confirmation = await ctx.channel.send(f"> {ctx.author.display_name}님, 데일리를 삭제하시겠습니까? 삭제하려면 'Y'라고 입력해주세요.")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel and msg.content == 'Y'

    try:
        msg = await bot.wait_for('message', check=check, timeout=5)
    except asyncio.TimeoutError:
        await ctx.channel.send(f"> {ctx.author.display_name}님, 시간이 초과되었습니다. 데일리 삭제를 취소합니다.")
    else:
        cur.execute("DELETE FROM daily WHERE did = %s", (str(ctx.author.id),))
        conn.commit()
        await ctx.channel.send(f"> {ctx.author.display_name}님의 데일리가 삭제되었습니다!")


@bot.command(aliases=['도움말', 'hp'])
async def helps(ctx):
    embed = discord.Embed(title="도움말",
                          description="**/출석**, **/aa**\n`/출석`을 해서 스택을 쌓습니다. `/출석 @상대` 기능으로 출석여부를 파악할 수 있습니다.\n\n "
                                      "**/알람**, **/al**\n`/알람 3`, `/al 3`형식으로 작성합니다. 3,5,7분만 가능합니다.\n\n"
                                      "**/독촉**, **/dc**\n`/독촉 @상대`형식으로 사용합니다. 멘션 대상자에게 독촉 DM을 봇이 대신 보내줍니다.\n\n"
                                      "**/순위표**\n현재 출석률을 확인합니다.\n\n"
                                      "**/데일리**, **/기록**, **/da**\n데일리를 기록할 수 있습니다. 기록후 바로 확인 가능합니다.\n\n"
                                      "**/삭제**, **/데일리삭제**, **/dd**\n 데일리를 *전체 삭제*합니다. 경고창이 표시됩니다.\n\n"
                                      "**/포인트**, **/pp**\n 현재 포인트가 표시됩니다. `/포인트 @상대` 상대포인트가 반환됩니다.\n\n"
                          , color=0xffc0cb)

    await ctx.send(embed=embed)


bot.run(token)
