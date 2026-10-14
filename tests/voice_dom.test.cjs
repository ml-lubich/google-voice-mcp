/* Execute the shipped browser code in a synthetic DOM; never open real Chrome. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');
const source = fs.readFileSync('src/google_voice_mcp/scripts/voice.js', 'utf8');
const account = '<button aria-label="Google Account: Tester (owner@example.test)"></button>';
const header = '<gv-thread-details-header><div class="header-title" aria-hidden="true">+1 (555) 123-4567</div></gv-thread-details-header>';
const composer = '<gv-message-entry><textarea placeholder="Type a message"></textarea></gv-message-entry><button aria-label="Send message">Send</button>';
const message = (body, direction = 'incoming', time = '') => `<gv-message-item><div class="full-container ${direction}"><gv-annotation class="content" aria-hidden="true">${body}</gv-annotation><div class="sender-timestamp"><span class="timestamp">${time}</span></div></div></gv-message-item>`;
const listItem = (body, status = 'read') => `<gv-message-thread-list-item><gv-thread-list-item><div class="container ${status}"><span class="participants" aria-hidden="true">Contact</span><span class="preview">${body}</span><span class="timestamp">Yesterday</span></div></gv-thread-list-item></gv-message-thread-list-item>`;
function fixture(html = header + composer, path = '/u/1/messages?itemId=t.%2B15551234567') {
  const dom = new JSDOM(account + html, {url: 'https://voice.google.com' + path, runScripts: 'outside-only'});
  const w = dom.window;
  w.HTMLElement.prototype.getClientRects = function() {return [{}];};
  w.setTimeout = callback => {queueMicrotask(callback); return 0;};
  const run = w.eval(`(${source})`);
  let clicks = 0;
  const button = w.document.querySelector('[aria-label="Send message"]');
  button?.addEventListener('click', () => clicks++);
  return {w, run: async args => JSON.parse(JSON.stringify(await run({account_email: 'owner@example.test', ...args}))),
    clicks: () => clicks, box: w.document.querySelector('textarea'), button};
}
const send = {action: 'send', recipient: '+15551234567', text: 'Approved exact text'};

test('inspect verifies origin and unique account without reading messages', async () => {
  const f = fixture();
  assert.equal((await f.run({action: 'inspect'})).account_email, 'owner@example.test');
  assert.equal((await f.run({action: 'inspect', account_email: null})).section, 'messages');
  assert.equal((await f.run({action: 'inspect', account_email: 'someone@example.test'})).error, 'account_mismatch');
  f.w.document.querySelector('[aria-label]').remove();
  assert.equal((await f.run({action: 'inspect'})).error, 'account_unknown');
});

test('ambiguous account, hidden account, and wrong origin refuse', async () => {
  let f = fixture();
  f.w.document.body.insertAdjacentHTML('beforeend', '<button aria-label="Google Account: Other (other@example.test)"></button>');
  assert.equal((await f.run({action: 'inspect'})).error, 'account_unknown');
  f = fixture(); f.w.document.querySelector('[aria-label]').hidden = true;
  assert.equal((await f.run({action: 'inspect'})).error, 'account_unknown');
  const dom = new JSDOM(account, {url: 'https://evil.test', runScripts: 'outside-only'});
  assert.equal((await dom.window.eval(`(${source})`)({action: 'inspect'})).error, 'origin');
});

test('SMS summaries are bounded and unread filter preserves unknowns', async () => {
  const f = fixture(listItem('read') + listItem('unread', 'unread') + listItem('unknown', ''));
  let result = await f.run({action: 'read', kind: 'sms', limit: 1});
  assert.equal(result.items.length, 1); assert.equal(result.items[0].preview, 'read');
  assert.equal(result.items[0].timestamp, null); assert.equal(result.items[0].id, null);
  result = await f.run({action: 'read', kind: 'sms', limit: 10, unread_only: true});
  assert.equal(result.error, 'unsupported_dom');
  const known = fixture(listItem('read') + listItem('unread', 'unread'));
  result = await known.run({action: 'read', kind: 'sms', limit: 10, unread_only: true});
  assert.equal(result.items.length, 1); assert.equal(result.items[0].is_read, false);
  result = await f.run({action: 'read', kind: 'sms', limit: 10});
  assert.equal(result.items[2].is_read, null);
  assert.equal(result.limited_to_visible, true);
});

test('thread messages retain displayed timestamp, null unknown fields, direction and bound', async () => {
  const f = fixture(header + message('old') + message('second', 'outgoing', '10:00 AM') + message('last', 'unknown'));
  const result = await f.run({action: 'read', kind: 'thread', limit: 2});
  assert.deepEqual(result.items.map(x => x.text), ['second', 'last']);
  assert.equal(result.items[0].direction, 'outgoing');
  assert.equal(result.items[0].timestamp_display, '10:00 AM');
  assert.equal(result.items[1].timestamp_display, null);
  assert.equal(result.items[1].direction, null);
});

test('wrong section, unrecognized DOM and unsupported actions refuse', async () => {
  const f = fixture('');
  assert.equal((await f.run({action: 'read', kind: 'calls', limit: 1})).error, 'section');
  assert.equal((await f.run({action: 'read', kind: 'sms', limit: 1})).error, 'unsupported_dom');
  assert.equal((await f.run({action: 'read', kind: 'thread', limit: 1})).error, 'unsupported_dom');
  assert.equal((await f.run({action: 'arbitrary'})).error, 'unsupported_dom');
  const empty = fixture('<gv-message-thread-list></gv-message-thread-list>');
  assert.equal((await empty.run({action: 'read', kind: 'sms', limit: 1})).error, 'unsupported_dom');
  assert.equal((await fixture('', '/u/1/settings').run({action:'inspect'})).section, null);
});

test('call and voicemail summaries expose only DOM-observed fields', async () => {
  for (const [kind, section, tag] of [['calls','calls','gv-call-thread-list-item'],['voicemails','voicemail','gv-voicemail-thread-list-item']]) {
    const f = fixture(`<${tag}><div class="${kind === 'voicemails' ? 'participant' : 'participants'}">Phone</div><div class="timestamp">Today</div></${tag}>`, `/u/1/${section}`);
    const row = (await f.run({action: 'read', kind, limit: 1})).items[0];
    assert.equal(row.participants_display, 'Phone'); assert.equal(row.preview, null);
    assert.equal(row.timestamp, null); assert.equal(row.is_read, null);
  }
});

test('one click only; observe newly added outgoing text and cleared draft, never claim delivery', async () => {
  const f = fixture(header + message(send.text, 'outgoing') + composer);
  f.button.addEventListener('click', () => {
    f.w.document.body.insertAdjacentHTML('beforeend', message(send.text, 'outgoing'));
    f.box.value = '';
  });
  const result = await f.run(send);
  assert.equal(f.clicks(), 1); assert.equal(result.state, 'submitted');
  assert.equal(result.delivery_confirmed, false); assert.equal(result.observed_in_thread, true);
});

test('ambiguous click result is outcome_unknown with no retry', async () => {
  const f = fixture();
  assert.equal((await f.run(send)).state, 'outcome_unknown');
  assert.equal(f.clicks(), 1);
  const throwing = fixture(); throwing.button.click = () => {throw Error('private');};
  assert.equal((await throwing.run(send)).state, 'outcome_unknown');
});

test('unchanged matching old text cannot confirm submission', async () => {
  const f = fixture(header + message(send.text, 'outgoing') + composer);
  f.button.addEventListener('click', () => {f.box.value = '';});
  assert.equal((await f.run(send)).state, 'outcome_unknown'); assert.equal(f.clicks(), 1);
});

test('route change after click produces unknown and never clicks again', async () => {
  const f = fixture();
  f.button.addEventListener('click', () => f.w.history.replaceState({}, '', '/u/1/calls'));
  assert.equal((await f.run(send)).state, 'outcome_unknown'); assert.equal(f.clicks(), 1);
});

test('wrong recipient, missing header, group route and named-only header leave draft untouched', async () => {
  for (const [html, path] of [[composer, undefined], [header+composer, '/u/1/messages?itemId=g.group'],
    [header+composer, '/u/1/messages?itemId=t.%2B15551230000'],
    ['<gv-thread-details-header><div class="header-title">A friend</div></gv-thread-details-header>'+composer, undefined],
    ['<gv-thread-details-header><div class="header-title">+15551234567; +15559999999</div></gv-thread-details-header>'+composer,undefined]]) {
    const f = fixture(html, path);
    assert.equal((await f.run(send)).error, 'recipient'); assert.equal(f.clicks(), 0); assert.equal(f.box.value, '');
  }
});

test('secondary exact number supports a single named contact', async () => {
  const f = fixture('<gv-thread-details-header><div class="header-title">Friend</div><div class="secondary-text">+1 555 123 4567</div></gv-thread-details-header>'+composer);
  assert.equal((await f.run(send)).state, 'outcome_unknown'); assert.equal(f.clicks(), 1);
});

test('existing draft is preserved; unavailable or duplicated controls refuse', async () => {
  const f = fixture(); f.box.value = 'user draft';
  assert.equal((await f.run(send)).error, 'draft'); assert.equal(f.box.value, 'user draft'); assert.equal(f.clicks(), 0);
  for (const property of ['disabled','readOnly']) {
    const f = fixture(); f.box[property] = true;
    assert.equal((await f.run(send)).error, 'send_disabled'); assert.equal(f.box.value, '');
  }
  const duplicate = fixture(header+composer+composer);
  assert.equal((await duplicate.run(send)).error, 'unsupported_dom');
  const disabled = fixture(); disabled.button.disabled = true;
  assert.equal((await disabled.run(send)).error, 'send_disabled'); assert.equal(disabled.clicks(), 0);
});

test('input event races recheck account, route, recipient, draft and controls before click', async () => {
  const changes = [
    f => f.w.history.replaceState({}, '', '/u/1/messages?itemId=t.%2B15551230000'),
    f => f.w.document.querySelector('[aria-label]').setAttribute('aria-label','Google Account: Other (other@example.test)'),
    f => {f.w.document.querySelector('.header-title').textContent = '+15559999999';},
    f => {f.box.value = 'changed by user';},
    f => f.box.remove(),
    f => f.button.replaceWith(f.button.cloneNode(true)),
  ];
  for (const change of changes) {
    const f = fixture(); f.box.addEventListener('input', () => change(f));
    assert.equal((await f.run(send)).error, 'changed'); assert.equal(f.clicks(), 0);
  }
});

test('invalid send arguments fail before draft mutation', async () => {
  for (const values of [{account_email:null},{recipient:'5551234567'},{text:''},{text:' '},{text:'x'.repeat(1601)}]) {
    const f = fixture(); assert.equal((await f.run({...send,...values})).error,'recipient'); assert.equal(f.box.value,'');
  }
});

 test('loading wrappers and changed item markup fail closed', async () => {
   for (const html of ['<gv-thread-list><unknown-item>Private</unknown-item></gv-thread-list>',
      '<gv-message-thread-list-item><unknown-item>Private</unknown-item></gv-message-thread-list-item>']) {
     const f = fixture(html);
     assert.equal((await f.run({action:'read',kind:'sms',limit:1})).error,'unsupported_dom');
   }
   for (const html of [header, header+'<gv-message-item><unknown-content>Private</unknown-content></gv-message-item>']) {
     const f = fixture(html);
     assert.equal((await f.run({action:'read',kind:'thread',limit:1})).error,'unsupported_dom');
   }
 });

test('unread filtering refuses unknown structure or status before filtering', async () => {
  for (const html of [listItem('unknown',''), '<gv-message-thread-list-item><div class="container read"></div></gv-message-thread-list-item>']) {
    assert.equal((await fixture(html).run({action:'read',kind:'sms',limit:1,unread_only:true})).error,'unsupported_dom');
  }
  assert.deepEqual((await fixture(listItem('known read')).run({action:'read',kind:'sms',limit:1,unread_only:true})).items, []);
});
