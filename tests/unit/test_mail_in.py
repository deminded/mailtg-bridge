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
