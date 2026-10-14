async function voice(args) {
  // DOM text is data only. No navigation, arbitrary expressions, cookies, or history reads.
  const error = code => ({error: code});
  const visible = el => !!el && !el.closest('[hidden]') &&
    getComputedStyle(el).display !== 'none' && getComputedStyle(el).visibility !== 'hidden' &&
    el.getClientRects().length > 0;
  const all = selector => [...document.querySelectorAll(selector)].filter(visible);
  const text = (el, selector) => {
    const child = el.querySelector(selector);
    return child && visible(child) ? (child.innerText || child.textContent || '').trim() || null : null;
  };
  const guard = () => {
    if (location.origin !== 'https://voice.google.com') return error('origin');
    const accounts = new Set(all('[aria-label]').map(el => el.getAttribute('aria-label'))
      .filter(label => /^Google Account:/i.test(label))
      .flatMap(label => label.match(/[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9.-]+\.[A-Z]{2,}/ig) || [])
      .map(email => email.toLowerCase()));
    if (accounts.size !== 1) return error('account_unknown');
    const account_email = [...accounts][0];
    if (args.account_email && account_email !== args.account_email.toLowerCase()) return error('account_mismatch');
    const match = location.pathname.match(/^\/u\/\d+\/(messages|calls|voicemail)\/?$/);
    return {account_email, url: location.href, section: match ? match[1] : null};
  };
  const identity = guard();
  if (identity.error) return identity;
  if (args.action === 'inspect') return {...identity, limited_to_visible: true};
  const messages = (limit = 100) => all('gv-message-item').slice(-limit).map(el => ({
    id: null, text: text(el, '.content'), timestamp: null,
    timestamp_display: text(el, '.sender-timestamp .timestamp'),
    direction: el.querySelector('.full-container.outgoing') ? 'outgoing' :
      el.querySelector('.full-container.incoming') ? 'incoming' : null,
  }));
  if (args.action === 'read') {
    const section = {sms: 'messages', calls: 'calls', voicemails: 'voicemail', thread: 'messages'}[args.kind];
    if (identity.section !== section) return error('section');
    let items;
    if (args.kind === 'thread') {
      if (!all('gv-thread-details-header').length) return error('unsupported_dom');
      items = messages(args.limit);
      if (!items.length || items.some(item => item.text === null)) return error('unsupported_dom');
    } else {
      // Lists contain summaries, not complete conversations or voicemail transcripts.
      const selectors = {sms: 'gv-message-thread-list-item', calls: 'gv-call-thread-list-item', voicemails: 'gv-voicemail-thread-list-item'};
      const nodes = all(selectors[args.kind]);
      if (!nodes.length)
        return error('unsupported_dom');
      if (args.unread_only && nodes.some(el => !el.querySelector('.container.read, .container.unread') ||
          !el.querySelector(args.kind === 'voicemails' ? '.participant' : '.participants')))
        return error('unsupported_dom');
      items = nodes.filter(el => !args.unread_only || el.querySelector('.container.unread')).slice(0, args.limit).map(el => ({
        id: null, participants_display: text(el, args.kind === 'voicemails' ? '.participant' : '.participants'),
        preview: text(el, '.preview'), timestamp: null, timestamp_display: text(el, '.timestamp'),
        ...(args.kind === 'calls' ? {call_type: el.querySelector('.gv-call.missed') ? 'missed' :
          el.querySelector('.gv-call.incoming') ? 'incoming' : el.querySelector('.gv-call.outgoing') ? 'outgoing' : null,
          duration_seconds: null} : {}),
        ...(args.kind === 'voicemails' ? {transcript_preview: text(el, '.transcription'),
          duration_display: text(el, '.duration'), duration_seconds: null} : {}),
        is_read: el.querySelector('.container.unread') ? false : el.querySelector('.container.read') ? true : null,
      }));
      if (items.some(item => item.participants_display === null)) return error('unsupported_dom');
    }
    return {...identity, items, limited_to_visible: true};
  }
  if (args.action !== 'send') return error('unsupported_dom');
  if (!args.account_email || !/^\+[1-9][0-9]{7,14}$/.test(args.recipient) ||
      typeof args.text !== 'string' || !args.text.trim() || args.text.length > 1600) return error('recipient');
  // Both the route and the visible header must identify one international number.
  // Named-only contacts and group threads are deliberately unsupported.
  const recipientProof = () => {
    const current = guard();
    if (current.error || current.section !== 'messages') return false;
    const route = new URL(location.href).searchParams.get('itemId');
    if (route !== `t.${args.recipient}`) return false;
    const headers = all('gv-thread-details-header');
    if (headers.length !== 1) return false;
    const header = text(headers[0], '.header-title') || text(headers[0], '.header-content h2');
    const secondary = text(headers[0], '.secondary-text');
    // Match a whole phone label rather than accidentally accepting a group title.
    const phone = value => value && /^\+[\d\s().-]+$/.test(value) ? value.replace(/[^+\d]/g, '') : null;
    return phone(header) === args.recipient || (phone(secondary) === args.recipient &&
      header && !/[;,]|\band\b|\+\s*\d+\s*(more|others)/i.test(header));
  };
  if (!recipientProof()) return error('recipient');
  const boxes = all('gv-message-entry textarea[placeholder="Type a message"]');
  const buttons = all('button[aria-label="Send message"]');
  if (boxes.length !== 1 || buttons.length !== 1) return error('unsupported_dom');
  const box = boxes[0], button = buttons[0], route = location.href;
  if (box.value !== '') return error('draft');
  if (box.disabled || box.readOnly) return error('send_disabled');
  const same = () => location.href === route && recipientProof() && visible(box) && visible(button) &&
    all('gv-message-entry textarea[placeholder="Type a message"]').length === 1 &&
    document.querySelector('gv-message-entry textarea[placeholder="Type a message"]') === box &&
    all('button[aria-label="Send message"]').length === 1 &&
    document.querySelector('button[aria-label="Send message"]') === button;
  if (!same() || box.value !== '') return error('changed');
  const before = messages().filter(item => item.direction === 'outgoing' && item.text === args.text).length;
  // Use the native setter so Angular receives the input event.
  Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(box, args.text);
  box.dispatchEvent(new Event('input', {bubbles: true}));
  await new Promise(resolve => setTimeout(resolve, 100));
  if (!same() || box.value !== args.text) return error('changed');
  if (button.disabled || button.getAttribute('aria-disabled') === 'true') return error('send_disabled');
  // This is the only click. Any uncertainty from here on is non-retriable.
  try {
    button.click();
    for (let attempt = 0; attempt < 8; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 250));
      if (!same()) break;
      const after = messages().filter(item => item.direction === 'outgoing' && item.text === args.text).length;
      if (box.value === '' && after > before) return {state: 'submitted', delivery_confirmed: false,
        account_email: identity.account_email, recipient: args.recipient, observed_in_thread: true};
    }
  } catch (_) { /* A click may already have reached the application. */ }
  return {state: 'outcome_unknown', delivery_confirmed: false,
    detail: 'Inspect the thread and draft before any further action; do not retry automatically.'};
}
