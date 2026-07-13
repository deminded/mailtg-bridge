from datetime import datetime, timezone
from mailtg_bridge.algorithms import *
from mailtg_bridge.domain import *
from mailtg_bridge.errors import FloodWait, Transient

def msg(id=1,text="",mentioned=False): return TgMessage(id,"d",datetime.now(timezone.utc),text=text,mentioned=mentioned)
def test_addressing_all_modes():
    dm=DialogRef("d",SourceType.DM); ch=DialogRef("c",SourceType.CHANNEL,username="chan")
    assert is_addressed(msg(),dm,set(),MentionPolicy.SELECTED,set())
    assert is_addressed(msg(),ch,{"@chan"},MentionPolicy.SELECTED,set())
    assert is_addressed(msg(mentioned=True),ch,set(),MentionPolicy.ALL,set())
    assert not is_addressed(msg(mentioned=True),ch,set(),MentionPolicy.SELECTED,set())
    assert is_addressed(msg(mentioned=True),ch,set(),MentionPolicy.SELECTED,{"c"})
    assert is_addressed(msg(text="hello @bridge"),ch,set(),MentionPolicy.ALL,set(),"bridge")

def botmsg(uname="somebot"): return TgMessage(1,"d",datetime.now(timezone.utc),Sender("Bot",uname,7,True))
def test_bot_policy_gates_dm(tmp_path=None):
    dm=DialogRef("d",SourceType.DM)
    # human DM always passes regardless of bot policy
    assert is_addressed(msg(),dm,set(),MentionPolicy.SELECTED,set(),bot_policy=BotPolicy.NONE)
    # bot DM: none -> drop, all -> keep, selected -> only if listed
    assert not is_addressed(botmsg(),dm,set(),MentionPolicy.SELECTED,set(),bot_policy=BotPolicy.NONE)
    assert is_addressed(botmsg(),dm,set(),MentionPolicy.SELECTED,set(),bot_policy=BotPolicy.ALL)
    assert not is_addressed(botmsg("x"),dm,set(),MentionPolicy.SELECTED,set(),bot_policy=BotPolicy.SELECTED,bot_list={"@ok"})
    assert is_addressed(botmsg("ok"),dm,set(),MentionPolicy.SELECTED,set(),bot_policy=BotPolicy.SELECTED,bot_list={"@ok"})
    # default (ALL) preserves v0.1 behaviour
    assert is_addressed(botmsg(),dm,set(),MentionPolicy.SELECTED,set())
    # a bot without @username can still be selected by its numeric id (bot_list accepts both)
    idbot=TgMessage(1,"d",datetime.now(timezone.utc),Sender("Bot",None,42,True))
    assert is_addressed(idbot,dm,set(),MentionPolicy.SELECTED,set(),bot_policy=BotPolicy.SELECTED,bot_list={"42"})
    assert not is_addressed(idbot,dm,set(),MentionPolicy.SELECTED,set(),bot_policy=BotPolicy.SELECTED,bot_list={"99"})

def test_batch_order_links_and_backoff():
    d=DialogRef("-100123",SourceType.TOPIC,peer_id=-100123,topic_id=42)
    assert [m.msg_id for m in make_dialog_batch(d,[msg(3),msg(1)],5).messages]==[1,3]
    assert build_deeplink(d,9)=="https://t.me/c/123/42/9"
    assert build_deeplink(DialogRef("d",SourceType.DM),9) is None
    now=datetime.now(timezone.utc); assert (next_backoff(FloodWait(90),0,30,3600,now).not_before-now).total_seconds()==90
    assert (next_backoff(Transient(),1,30,3600,now,jitter=0).not_before-now).total_seconds()==60
