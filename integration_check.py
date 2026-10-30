import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import gi

gi.require_version('IBus', '1.0')
from gi.repository import GLib, IBus
from settings import SettingsStore

project = Path(__file__).resolve().parent
processes = []

def spin(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    context = GLib.MainContext.default()
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError('Timed out waiting for IBus test condition')

with tempfile.TemporaryDirectory(prefix='bgv-') as temporary:
    root = Path(temporary)
    os.environ['IBUS_ADDRESS'] = f'unix:path={root}/bus'
    for key, name in [('XDG_CACHE_HOME','cache'), ('XDG_CONFIG_HOME','config'), ('XDG_DATA_HOME','data'), ('XDG_RUNTIME_DIR','runtime')]:
        (root/name).mkdir(mode=0o700)
        os.environ[key] = str(root/name)
    os.environ.pop('DISPLAY', None)
    os.environ.pop('WAYLAND_DISPLAY', None)
    try:
        processes.append(subprocess.Popen(['ibus-daemon', '--single', '--address', os.environ['IBUS_ADDRESS'], '--cache=none', '--emoji-extension=disable'], stdout=subprocess.DEVNULL))
        IBus.init()
        bus = IBus.Bus.new_async()
        spin(bus.is_connected)
        processes.append(subprocess.Popen(['/usr/bin/python3', str(project/'engine.py')]))
        spin(lambda: any(desc.get_name() == 'bo-go-viet-telex' for desc in bus.list_active_engines()))
        print('PASS: engine registered dynamically for this test')
        context = bus.create_input_context('bo-go-viet-integration-test')
        context.set_capabilities(IBus.Capabilite.PREEDIT_TEXT | IBus.Capabilite.FOCUS | IBus.Capabilite.PROPERTY)
        context.focus_in()
        # IBus defaults to a global engine; SetEngine on a context can be ignored.
        assert bus.set_global_engine('bo-go-viet-telex')
        spin(lambda: context.get_engine() is not None and context.get_engine().get_name() == 'bo-go-viet-telex')
        committed = []
        preedit = []
        received = []
        direct_model = None
        visible_preedit = []

        def publish_surrounding():
            context.set_surrounding_text(IBus.Text.new_from_string(direct_model['text']), direct_model['cursor'], direct_model['anchor'])

        # Keep payloads alive until C signal dispatch finishes on PyGObject/IBus.
        def on_commit(_context, text):
            received.append(text)
            committed.append(text.get_text())
            if direct_model is not None:
                start, end = sorted((direct_model['cursor'], direct_model['anchor']))
                direct_model['text'] = direct_model['text'][:start] + text.get_text() + direct_model['text'][end:]
                direct_model['cursor'] = direct_model['anchor'] = start + len(text.get_text())
                publish_surrounding()

        def on_preedit(_context, text, cursor, visible):
            received.append(text)
            preedit.append(text.get_text())
            if visible:
                visible_preedit.append(text.get_text())

        def on_delete(_context, offset, count):
            assert direct_model is not None
            start = direct_model['cursor'] + offset
            assert 0 <= start <= start + count <= len(direct_model['text'])
            direct_model['text'] = direct_model['text'][:start] + direct_model['text'][start + count:]
            direct_model['cursor'] = direct_model['anchor'] = start
            publish_surrounding()

        forwarded = []
        def on_forward(_context, keyval, keycode, modifiers):
            forwarded.append((keyval, keycode, modifiers))
            if keyval == IBus.KEY_BackSpace and not modifiers & IBus.ModifierType.RELEASE_MASK:
                start = direct_model['cursor'] - 1
                assert start >= 0
                direct_model['text'] = direct_model['text'][:start] + direct_model['text'][start + 1:]
                direct_model['cursor'] = direct_model['anchor'] = start
                publish_surrounding()
            elif not modifiers & IBus.ModifierType.RELEASE_MASK:
                char = IBus.keyval_to_unicode(keyval)
                if char and char.isprintable():
                    start = direct_model['cursor']
                    direct_model['text'] = direct_model['text'][:start] + char + direct_model['text'][start:]
                    direct_model['cursor'] = direct_model['anchor'] = start + len(char)
                    publish_surrounding()

        context.connect('commit-text', on_commit)
        context.connect('update-preedit-text', on_preedit)
        context.connect('delete-surrounding-text', on_delete)
        context.connect('forward-key-event', on_forward)

        def key(char, state=0):
            value = ord(char) if isinstance(char, str) else char
            handled = context.process_key_event(value, 0, state)
            while GLib.MainContext.default().pending():
                GLib.MainContext.default().iteration(False)
            return handled

        for char in 'tieengs':
            assert key(char)
        spin(lambda: preedit and preedit[-1] == 'tiếng')
        assert not key(' ')
        spin(lambda: committed == ['tiếng'])
        print('PASS: key events -> preedit tiếng -> committed tiếng')
        for char, expected in zip('oiw', ('o', 'oi', 'ơi')):
            assert key(char)
            spin(lambda: preedit[-1] == expected)
        assert not key(' ')
        spin(lambda: committed[-1] == 'ơi')
        print('PASS: delayed w transforms oi into ơi and commits through IBus')
        for char in 'Vieetj':
            key(char)
        assert key(IBus.KEY_BackSpace)
        spin(lambda: preedit[-1] == 'Việ')
        key(IBus.KEY_Return)
        spin(lambda: committed[-1] == 'Việ')
        print('PASS: Backspace deletes displayed character; Return commits')
        for char in 'ass':
            key(char)
        assert key(IBus.KEY_Escape)
        spin(lambda: committed[-1] == 'ass')
        print('PASS: Escape restores original keys')
        mask = IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.SHIFT_MASK
        assert key(' ', mask)
        assert not key('a')
        assert key(' ', mask)
        assert key('a')
        key(' ')
        print('PASS: Ctrl+Shift+Space toggles English/Vietnamese')
        count = len(committed)
        context.set_content_type(IBus.InputPurpose.PASSWORD, 0)
        # A synchronous key request is ordered after SetContentType on this connection.
        assert not key('a')
        assert not key('s')
        assert len(committed) == count
        context.set_content_type(IBus.InputPurpose.FREE_FORM, 0)
        assert key('a')
        key(' ')
        print('PASS: declared password field bypasses composition')
        settings = SettingsStore()
        for char in 'tieengs':
            assert key(char)
        settings.update(input_method='vni')
        for char in 'Vie65t':
            assert key(char)
        spin(lambda: preedit[-1] == 'Việt')
        key(' ')
        spin(lambda: committed[-2:] == ['tiếng', 'Việt'])
        print('PASS: changing settings commits the pending Telex word and activates VNI live')
        settings.update(macros_enabled=True, macros={'btw': 'nhân tiện'})
        for char in 'btw':
            assert key(char)
        key(' ')
        spin(lambda: committed[-1] == 'nhân tiện')
        print('PASS: configured macro expands through real IBus key events')
        direct_model = {'text': 'Có sẵn: ', 'cursor': 8, 'anchor': 8}
        context.set_capabilities(IBus.Capabilite.PREEDIT_TEXT | IBus.Capabilite.FOCUS | IBus.Capabilite.PROPERTY | IBus.Capabilite.SURROUNDING_TEXT)
        publish_surrounding()
        settings.update(input_method='telex', typing_mode='direct')
        visible_count = len(visible_preedit)
        for char, expected in zip('tieengs', ('t', 'ti', 'tie', 'tiê', 'tiên', 'tiêng', 'tiếng')):
            assert key(char)
            spin(lambda: direct_model['text'] == 'Có sẵn: ' + expected)
        assert len(visible_preedit) == visible_count
        assert not key(' ')
        assert direct_model['text'] == 'Có sẵn: tiếng'
        print('PASS: direct mode commits after each key, updates tones, and never displays preedit')
        for char in 'book':
            assert key(char)
        assert key(IBus.KEY_Escape)
        spin(lambda: direct_model['text'] == 'Có sẵn: tiếngbook')
        for char in 'btw':
            assert key(char)
        assert not key(' ')
        spin(lambda: direct_model['text'] == 'Có sẵn: tiếngbooknhân tiện')
        print('PASS: direct-mode Escape and macro replacement preserve existing Unicode text')
        direct_model['cursor'], direct_model['anchor'] = 0, 3
        publish_surrounding()
        before = direct_model['text']
        assert key('a')
        spin(lambda: preedit[-1] == 'a')
        assert direct_model['text'] == before
        context.reset()
        print('PASS: moving/selecting text abandons direct replacement and falls back without deleting')
        direct_model = {'text': 'Có sẵn: ', 'cursor': 8, 'anchor': 8}
        context.set_capabilities(IBus.Capabilite.PREEDIT_TEXT | IBus.Capabilite.FOCUS | IBus.Capabilite.PROPERTY)
        settings.update(typing_mode='forward')
        visible_count = len(visible_preedit)
        for char, expected in zip('Phamj', ('P', 'Ph', 'Pha', 'Pham', 'Phạm')):
            assert key(char)
            spin(lambda: direct_model['text'] == 'Có sẵn: ' + expected)
        assert len(visible_preedit) == visible_count
        assert len(forwarded) == 4
        assert not key(' ')
        assert direct_model['text'] == 'Có sẵn: Phạm'
        print('PASS: compatibility mode forwards Backspace/commit in order without surrounding support or visible preedit')
        direct_model = {'text': '', 'cursor': 0, 'anchor': 0}
        context.reset()
        visible_count = len(visible_preedit)
        for char in 'Phamj Tooi yeeu tieengs Vieetj ':
            if not key(char):
                on_forward(context, ord(char), 0, 0)
        spin(lambda: direct_model['text'] == 'Phạm Tôi yêu tiếng Việt ')
        assert len(visible_preedit) == visible_count
        print('PASS: rapid queued typing preserves words, spaces and tone changes in compatibility mode')
        context.reset()
        direct_model = {'text': '', 'cursor': 0, 'anchor': 0}
        for char in 'Phamj':
            assert key(char)
        spin(lambda: direct_model['text'] == 'Phạm')
        forwarded_count = len(forwarded)
        for expected in ('Phạ', 'Ph', 'P', ''):
            assert not key(IBus.KEY_BackSpace)
            assert len(forwarded) == forwarded_count
            # The real client handles the original unconsumed physical key.
            on_delete(context, -1, 1)
            assert direct_model['text'] == expected
        assert key('a')
        spin(lambda: direct_model['text'] == 'a')
        print('PASS: ordinary physical Backspace passes through without synthetic keys or a replacement queue')
        print('ALL IBUS INTEGRATION CHECKS PASSED')
    finally:
        for process in reversed(processes):
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
