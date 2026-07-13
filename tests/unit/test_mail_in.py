from email.message import EmailMessage
from mailtg_bridge.mail_in import *
def test_parse_trust_ids_and_reply_strip():
    m=EmailMessage(); m['From']='User <u@example.org>'; m['To']='b@example.net'; m['Subject']='=?utf-8?b?0KLQtdGB0YI=?='; m['In-Reply-To']='<a@x>'; m['References']='<old@x> <a@x>'
    m.set_content('answer\n\nOn yesterday wrote:\n> quote')
    x=parse_inbound(m.as_bytes(),'uid:1')
    assert x.body_text=='answer' and x.in_reply_to==('<a@x>',)
    assert MailClassifier('u@example.org','b@example.net').trusted(x)
    assert MailClassifier('u@example.org','b@example.net').parent_ids(x)==('<a@x>','<a@x>','<old@x>')

def test_html_only_and_auto():
    m=EmailMessage(); m['From']='u@x'; m['To']='b@x'; m['Auto-Submitted']='auto-replied'; m.set_content('<b>Hello</b>',subtype='html')
    assert extract_reply_text(m)=='Hello' and is_auto_or_loop(m,'b@x')

def test_strip_russian_attribution_tail():
    # Live-test leak: RU client attribution ("... писал(а):") was not an English
    # "On ... wrote:" so the whole quoted original passed through into Telegram.
    body='Мой ответ, всё чисто.\n\n13.07.2026, 08:24, "Arête" <b@x> писал(а):\n> Telegram: 123\n> оригинал'
    assert strip_quoted_tail(body)=='Мой ответ, всё чисто.'

def test_html_reply_drops_blockquote_and_keeps_lines():
    # The other half of the leak: html_to_text used to flatten newlines to one line,
    # so the tail could never be found line-by-line. Now block breaks are kept and the
    # quote container is dropped whole.
    html='<div>Ответ из почты.</div><div>Живой тест окупился.</div>'\
         '<div class="gmail_quote"><div>13.07.2026 писал(а):</div>'\
         '<blockquote>Telegram: 123<br>оригинал</blockquote></div>'
    m=EmailMessage(); m['From']='u@x'; m['To']='b@x'; m.set_content(html,subtype='html')
    out=extract_reply_text(m)
    assert 'Ответ из почты.' in out and 'Живой тест окупился.' in out
    assert 'Telegram: 123' not in out and 'писал' not in out

def test_bare_blockquote_reply_stripped():
    m=EmailMessage(); m['From']='u@x'; m['To']='b@x'
    m.set_content('<div>Чистый ответ</div><blockquote type="cite">старое сообщение</blockquote>',subtype='html')
    assert extract_reply_text(m)=='Чистый ответ'

def test_text_after_quote_is_kept():
    # Only the quoted subtree is skipped, not everything after it: an inline reply or a
    # trailing P.S. below the quote survives (regression guard for depth-tracking parser).
    html='<div>Верхний ответ</div><blockquote>цитата</blockquote><div>P.S. важное</div>'
    assert html_to_text(html)=='Верхний ответ\nP.S. важное'
    inline='<div>Согласен с этим:</div><blockquote>тезис</blockquote><div>но не с тем</div>'
    assert html_to_text(inline)=='Согласен с этим:\nно не с тем'

def test_russian_attribution_variants():
    for attr in ("Иван писал(а):","Мария писала:","Коллеги писали:","13.07 Пётр написал:"):
        assert strip_quoted_tail(f"ответ\n\n{attr}\n> цитата")=="ответ"

def test_yandex_mobile_quote_block():
    # Real client from live test: Yandex mobile mail. Quote is a plain header block
    # (Кому:/Тема:/"<email>:" attribution) + a "--" signature, NOT a <blockquote>.
    body=('Тест ответа\n\n'
          'Кому: "deminded@eparfenov.ru" <deminded@eparfenov.ru>;\n'
          'Тема: Telegram: 8756743924;\n'
          '09:59, 13 июля 2026 г., "deminded-tg@noomarxism.ru" <deminded-tg@noomarxism.ru>:\n\n'
          '--\nОтправлено из мобильного приложения Яндекс Почты')
    assert strip_quoted_tail(body)=='Тест ответа'

def test_signature_delimiter_cuts_tail():
    assert strip_quoted_tail('живой текст\n-- \nмоя подпись')=='живой текст'
