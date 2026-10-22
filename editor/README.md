# Shared block editor

The static `block-editor.js` bundle is committed. Normal app hosting needs no Node,
package installation, runtime CDN or additional backend. ProseMirror supplies the
editable document, selection, clipboard, composition handling and undo history.

To edit the engine and rebuild:

```sh
cd editor
npm ci
npm run build
```

`src.js` mounts an EditorView on each existing editable `.rt` element. Dataset
identifiers, automatic saving, local recovery, attachment uploads and sheet drafts
continue through the app's existing handlers. `serialize()` flushes pending DOM
changes and uses the schema's serializer, so temporary controls and hydrated photo
URLs never enter the saved HTML. Unedited documents retain their original HTML.

Legacy `.tgl` plus `.tgc` siblings are grouped in a rendered copy. New toggles have
an actual title and nested block body; changing a toggle to ordinary text unwraps
its content. No document collection is rewritten just by opening the app. Supported
legacy headings, lists, checks, indentation, day headers, formatting, links and photo
IDs/sizes are parsed into the schema. Adding a new block/attribute requires a schema
rule and a round-trip preservation test. The runtime MIT notices are in
`THIRD_PARTY_NOTICES.md`.

Run the browser regression suite from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_block_editor.py' -v
```

These tests use mocked Firebase. Before shipping native input changes, also check
Gboard/Samsung Keyboard composition, Enter in nested toggles, keyboard dismissal,
photo selection and Android Back on an actual phone. Desktop emulation cannot
verify a real Android keyboard or notification environment.

Explicit, cancelable `beforeinput: insertParagraph` intents go through the block
Enter command. Android Chrome suppresses the usual keydown Enter path; relying
on native div splitting duplicates a custom toggle container. Composition text
intents are left to ProseMirror. Disclosure clicks retain external focus and
only relocate a cursor that would otherwise remain in a hidden body.

`block-moving.js` owns pointer capture, mouse hover controls, gutter hit testing,
drop indicators, touch cancellation and ancestor/page auto-scroll. It commits a
single schema transaction on a valid drop, with no writes on hover or cancel.
Controls must stay mounted during pointer capture. Block ranges share the same
move/type/duplicate/delete operations; media nodes stay intact. Native list HTML
is flattened into the schema's paragraph kind/depth representation before parse.
Clipboard paste and cut have separate history boundaries. This is a practical
writing subset, not Notion's complete editor or database feature set.

Also run `test_block_moving.py` and `test_block_writing.py` with unittest discovery
for real mouse/touch movement, hover without focus, auto-scroll, grouped actions,
clipboard round trips and list nesting. Touch coverage uses Chromium emulation,
not a physical Android device.
