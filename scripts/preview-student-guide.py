"""Capture C01's student guide without creating provider resources."""
from pathlib import Path
import json
import os
import subprocess
import time
import urllib.request
from playwright.sync_api import sync_playwright

APP=Path(__file__).resolve().parents[1]
OUTPUT=APP/'teaching-material/student-guide-preview'
OUTPUT.mkdir(parents=True,exist_ok=True)
port=34101
base=f'http://127.0.0.1:{port}'
log=(OUTPUT/'server.log').open('w',encoding='utf-8')
server=subprocess.Popen(['node','server.js'],cwd=APP,env={**os.environ,'PORT':str(port)},
                        stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    for _ in range(80):
        if server.poll() is not None:
            raise RuntimeError('Preview server exited')
        try:
            with opener.open(base+'/api/config',timeout=1) as response:
                json.load(response)
            break
        except OSError:
            time.sleep(.2)
    else:
        raise RuntimeError('Preview server readiness timeout')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        errors=[]
        writes=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('request',lambda request:writes.append(request.url) if request.method!='GET' else None)
        # Render the editable SVG at its original resolution for downloading.
        page.goto(base+'/architecture.svg',wait_until='networkidle')
        assert page.locator('svg').count()==1
        overflow=page.locator('svg text').evaluate_all('nodes=>nodes.filter(n=>{const b=n.getBBox();return b.x<0||b.x+b.width>1320||b.y+b.height>1650}).map(n=>n.textContent)')
        assert not overflow,overflow
        page.locator('svg').screenshot(path=str(APP/'public/architecture.png'))
        page.goto(base+'/architecture.html',wait_until='networkidle')
        assert page.locator('.uml-image').evaluate('e=>e.complete&&e.naturalWidth===1320')
        assert page.locator('.student-nav[aria-label="Lesson sections"] a[aria-current="location"]').get_attribute('href')=='/architecture.html'
        assert page.locator('#walkthrough .run-steps>li').count()==6
        for step in page.locator('#walkthrough .run-steps>li').all():
            assert step.locator('.code-example pre code').count()>0
        assert page.locator('.code-example').count()==23
        assert page.locator('#prerequisite-steps>li').count()==4
        assert page.locator('#prerequisites').evaluate('e=>Boolean(e.compareDocumentPosition(document.querySelector("#walkthrough"))&Node.DOCUMENT_POSITION_FOLLOWING)')
        assert 'client.beta.agents.create' in page.locator('#prerequisites').inner_text()
        assert 'client.beta.environments.create' in page.locator('#prerequisites').inner_text()
        for branch in page.locator('.architecture-branches article').all():
            assert branch.locator('.code-example pre code').count()>0
        assert min(page.locator('.code-example pre code').evaluate_all('nodes=>nodes.map(n=>parseFloat(getComputedStyle(n).fontSize))'))>=19
        page.screenshot(path=str(OUTPUT/'C01-Architecture-Page.png'))
        page.locator('#prerequisite-steps>li').nth(1).screenshot(path=str(OUTPUT/'C01-Prerequisites-Create-Agent.png'))
        page.locator('#prerequisite-steps>li').nth(2).screenshot(path=str(OUTPUT/'C01-Prerequisites-Create-Environment.png'))
        page.locator('#walkthrough .run-steps>li').first.screenshot(path=str(OUTPUT/'C01-Walkthrough-Code-Step-01.png'))
        page.locator('#walkthrough .run-steps>li').nth(3).screenshot(path=str(OUTPUT/'C01-Walkthrough-Code-Step-04.png'))
        page.locator('.uml-figure').screenshot(path=str(OUTPUT/'C01-UML-Infographic.png'))
        png=page.request.get(base+'/architecture.png')
        assert png.ok and png.headers.get('content-type')=='image/png'
        page.goto(base,wait_until='networkidle')
        assert page.locator('#learning').count()==0
        assert page.locator('#create').is_enabled()
        assert page.locator('#message').is_disabled()
        page.screenshot(path=str(OUTPUT/'C01-Session-Lab-Navigation.png'),full_page=True)
        page.locator('.student-nav a[href="/guide.html#learning"]').click()
        page.wait_for_url(base+'/guide.html#learning')
        page.locator('.student-nav[aria-label="Lesson sections"] a[href="/architecture.html"]').click()
        page.wait_for_url(base+'/architecture.html')
        page.locator('.student-nav[aria-label="Lesson sections"] a[href="/guide.html#learning"]').click()
        page.wait_for_url(base+'/guide.html#learning')
        assert page.locator('#learning .learning-card').count()==6
        assert page.locator('#run-guide .run-steps>li').count()==6
        page.locator('.student-nav[aria-label="Lesson sections"] a[href="/guide.html#run-guide"]').click()
        assert page.evaluate('location.hash')=='#run-guide'
        assert page.locator('.student-nav[aria-label="Lesson sections"] a[aria-current="location"]').inner_text()=='How to run the application'
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(OUTPUT/'C01-Student-Guide-Navigation.png'))
        for section,name in [('learning','C01-What-You-Will-Learn.png'),('run-guide','C01-How-To-Run.png')]:
            page.locator('#'+section).screenshot(path=str(OUTPUT/name))
        assert page.locator('.resource-help pre').is_hidden()
        page.locator('.resource-help summary').click()
        assert page.locator('.resource-help pre').is_visible()
        page.locator('.resource-help summary').click()
        sizes=page.locator('#learning p, #run-guide p, #run-guide code').evaluate_all(
            'nodes=>nodes.map(n=>parseFloat(getComputedStyle(n).fontSize))')
        assert min(sizes)>=18
        page.locator('#themeToggle').click()
        assert page.locator('html').get_attribute('data-theme')=='dark'
        page.locator('#learning').screenshot(path=str(OUTPUT/'C01-Learning-Dark.png'))
        page.locator('#run-guide').screenshot(path=str(OUTPUT/'C01-Run-Guide-Dark.png'))
        page.locator('.student-nav[aria-label="Lesson sections"] a[href="/#session-lab"]').click()
        page.wait_for_url(base+'/#session-lab')
        assert page.locator('html').get_attribute('data-theme')=='dark'
        # An explicitly authored SSE fixture checks session-ID preservation;
        # it never reaches the local server or the provider.
        page.route('**/api/sessions/sesn_navigation_preview/stream',lambda route:route.fulfill(
            status=200,content_type='text/event-stream',body='data: {"type":"session.status_idle","stop_reason":{"type":"end_turn"}}\n\n'))
        page.locator('#sessionId').fill('sesn_navigation_preview')
        page.locator('#connect').click()
        page.locator('.student-nav a[href="/guide.html#learning"]').click()
        page.wait_for_url(base+'/guide.html#learning')
        page.locator('.student-nav[aria-label="Lesson sections"] a[href="/#session-lab"]').click()
        page.wait_for_url(base+'/#session-lab')
        assert page.locator('#sessionId').input_value()=='sesn_navigation_preview'
        assert page.locator('#message').is_disabled()
        page.evaluate('sessionStorage.removeItem("session-lab-last-session")')
        page.locator('.student-nav a[href="/guide.html#learning"]').click()
        page.wait_for_url(base+'/guide.html#learning')
        page.locator('#themeToggle').click()
        for width in [390,768,1024]:
            page.set_viewport_size({'width':width,'height':844})
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+2'),f'Guide overflow at {width}px'
            if width==390:
                page.locator('#learning').screenshot(path=str(OUTPUT/'C01-Learning-Mobile.png'))
                page.locator('#run-guide').screenshot(path=str(OUTPUT/'C01-Run-Guide-Mobile.png'))
            page.locator('.student-nav[aria-label="Lesson sections"] a[href="/#session-lab"]').click()
            page.wait_for_url(base+'/#session-lab')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+2'),f'Lab overflow at {width}px'
            page.locator('.student-nav a[href="/guide.html#learning"]').click()
            page.wait_for_url(base+'/guide.html#learning')
            page.locator('.student-nav[aria-label="Lesson sections"] a[href="/architecture.html"]').click()
            page.wait_for_url(base+'/architecture.html')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+2'),f'Architecture page overflow at {width}px'
            assert page.locator('.uml-image').evaluate('e=>e.naturalWidth===1320')
            if width==390:
                page.screenshot(path=str(OUTPUT/'C01-Architecture-Mobile.png'))
                assert page.locator('.diagram-scroll').evaluate('e=>e.scrollWidth>e.clientWidth')
            page.locator('.student-nav[aria-label="Lesson sections"] a[href="/guide.html#learning"]').click()
            page.wait_for_url(base+'/guide.html#learning')
        assert not errors,errors
        assert not writes,writes
        browser.close()
    (OUTPUT/'verification.json').write_text(json.dumps(dict(learningCards=6,runSteps=6,
        sectionNavigation='passed: separate guide and lab pages, links both ways',optionalResourceHelp='passed',lightAndDark='passed: preference shared across pages',
        sessionIdPreservation='passed with authored browser SSE fixture; no automatic reconnect',
        architecture='passed: SVG, PNG export, dedicated HTML, navigation, mobile scroll',
        codeWalkthrough='passed: 23 visible source excerpts across setup, all six runtime steps and both branches; minimum 19px code',
        prerequisites='passed: four setup steps precede runtime; agent and environment code visible',
        mobileWidths=[390,768,1024],horizontalOverflow=False,minimumInstructionFontPx=min(sizes),
        browserErrors=errors,providerWriteRequests=writes),indent=2),encoding='utf-8')
    print('C01 guide verified: desktop/mobile, light/dark, navigation, 6 concepts and 6 run steps.')
finally:
    if server.poll() is None:
        server.terminate()
        server.wait(timeout=10)
    log.close()
