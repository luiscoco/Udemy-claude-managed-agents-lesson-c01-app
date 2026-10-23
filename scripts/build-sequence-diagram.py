"""Draw C01's actual create/observe/send flow as a presentation-style UML image."""
from pathlib import Path
from html import escape

APP=Path(__file__).resolve().parents[1]
W,H=1320,1650
p=[f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title description">
<title id="title">C01 — Create a session and follow its first turn</title>
<desc id="description">UML sequence diagram with five participants: student, browser UI, Node.js host, Anthropic SDK, and Managed Agents. Twenty-one numbered messages show session creation, opening the provider stream before listing history, browser SSE, sending a prompt, and observing the result. The architecture page provides the full text equivalent.</desc>
<defs>
<marker id="request" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="10" markerHeight="10" orient="auto"><path d="M0 0 L12 6 L0 12 Z" fill="#193269"/></marker>
<marker id="response" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="10" markerHeight="10" orient="auto"><path d="M1 1 L11 6 L1 11" fill="none" stroke="#193269" stroke-width="2"/></marker>
</defs>
<rect width="1320" height="1650" rx="26" fill="#fff"/>
<rect x="1" y="1" width="1318" height="1648" rx="26" fill="none" stroke="#d7e7f5" stroke-width="2"/>
<style>text{{font-family:Arial,Helvetica,sans-serif;fill:#090d3b}}</style>''']


def text(x,y,value,size=26,color='#193269',bold=False):
    p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{"700" if bold else "400"}" fill="{color}" style="fill:{color}">{escape(value)}</text>')


def box(x,y,w,h,fill,stroke='#d7e7f5',r=16):
    p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')


def arrow(a,b,y,label,style='request'):
    dash=' stroke-dasharray="9 7"' if style=='return' else ''
    marker='request' if style=='request' else 'response'
    p.append(f'<line x1="{a}" y1="{y}" x2="{b}" y2="{y}" stroke="#193269" stroke-width="2.5"{dash} marker-end="url(#{marker})"/>')
    text(min(a,b)+10,y-12,label)


text(34,49,'LESSON C01 / UML SEQUENCE DIAGRAM',26,'#0872d4',True)
text(34,104,'Create a session. Observe its first turn.',43,'#090d3b',True)
text(34,148,'Live application path • read from top to bottom',28)

# The SDK lane is part of the host process, not another remote service.
box(548,176,504,43,'#f1eaff',r=9)
text(561,207,'Host process: Node.js + Anthropic SDK',26,'#6534a2',True)
xs=[140,400,660,920,1180]
for x,title,detail,fill,accent in [
    (140,'Student','Browser user','#edf7ff','#087dfa'),
    (400,'Browser UI','public/app.js','#edf7ff','#087dfa'),
    (660,'Node.js host','server.js','#f3edff','#853df2'),
    (920,'Anthropic SDK','Server-side client','#f3edff','#853df2'),
    (1180,'Managed Agents','Remote session','#eaf8f1','#00865d')]:
    box(x-113,232,226,94,fill)
    p.append(f'<rect x="{x-113}" y="232" width="226" height="7" rx="3" fill="{accent}"/>')
    text(x-100,273,title,27,'#090d3b',True)
    text(x-100,310,detail,26)
    p.append(f'<line x1="{x}" y1="326" x2="{x}" y2="1474" stroke="#97aac1" stroke-width="2" stroke-dasharray="7 7"/>')

messages=[
    (140,400,'1. New session','request'),
    (400,660,'2. POST session','request'),
    (660,920,'3. sessions.create','request'),
    (920,1180,'4. Create request','request'),
    (1180,920,'5. Session + ID','return'),
    (920,660,'6. Created session','return'),
    (660,660,'7. attach(id)','self'),
    (660,920,'8. events.stream','request'),
    (920,1180,'9. Open live stream','request'),
    (660,920,'10. events.list','request'),
    (1180,660,'11. History via SDK','return'),
    (660,400,'12. Session ready','return'),
    (400,660,'13. GET SSE stream','request'),
    (660,400,'14. Buffered events','event'),
    (140,400,'15. Send message','request'),
    (400,660,'16. POST message','request'),
    (660,920,'17. events.send','request'),
    (920,1180,'18. user.message','request'),
    (1180,660,'19. Agent + status events via SDK','event'),
    (660,400,'20. Live SSE events','event'),
    (400,140,'21. Answer + state','return')]
for i,(a,b,label,style) in enumerate(messages):
    y=381+i*53
    if style=='self':
        p.append(f'<path d="M {a} {y-17} h 43 v 22 h -43" fill="none" stroke="#193269" stroke-width="2.5" marker-end="url(#request)"/>')
        text(a+54,y-1,label)
    else:
        arrow(a,b,y,label,style)

box(27,1492,1266,61,'#eaf8f1',r=12)
text(45,1532,'Create once → open stream before history → send after observation is ready.',28,'#056b4b',True)
arrow(44,106,1590,'',style='request')
text(120,1598,'Request',26)
arrow(325,387,1590,'',style='return')
text(400,1598,'Returned data',26)
arrow(678,740,1590,'',style='event')
text(754,1598,'Event notification',26)
p.append('</svg>')
(APP/'public/architecture.svg').write_text('\n'.join(p),encoding='utf-8')
print('Generated architecture.svg: five lanes, 21 numbered messages.')
