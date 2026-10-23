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

Drop hit testing first chooses the deepest visible toggle body containing the
pointer, including its handle gutter and a small vertical gap tolerance, then
the nearest child block. Do not use only `elementFromPoint()` for this: handles
sit outside child text rectangles, where DOM hits resolve to the outer toggle.
Regression tests must exercise nested-to-nested moves in both directions, gaps,
native touch events and persisted order after reloading.

Empty first body Backspace returns to the title; required empty body placeholders
remain structural children rather than being moved to an outside paragraph.
Backspace from a following empty paragraph skips these placeholders and respects
closed toggles. Cancelable non-composing `deleteContentBackward` input intents use
the same command for Android keyboards that omit a useful keydown event.

Selection-change handlers flush the view's DOM observer before positioning tools.
The focus event must not display a handle using the old model selection: a first
tap may still have its native caret update pending. Click targets can position
controls directly, and subsequent selection updates follow the synchronized state.
Tests press the touch handle immediately after the first tap without adding a
delay to mask this race. Scroll updates preserve visible hover controls.

Deletion boundaries are explicit commands. Backspace at the beginning of text
after a toggle enters the last visible text; forward Delete before a toggle
enters its title. Delete at the end of a title enters its open body or the next
visible text. It never selects the required title/body containers. Those schema
nodes are not selectable; deliberate whole-document or block selection still
allows deletion. Native forward-delete intents use the same command.

`test_editor_surfaces.py` verifies actual typing, paragraph merging, select-all
deletion, undo/redo, empty-body saving and reopening on each surface in both
spaces at desktop/mobile widths. It also checks isolation and other journal days.
`test_editor_delete_boundaries.py` covers hidden-body preservation, native delete
intents, photos after undo, and Chromium's IME composition/cancellation path.

Writing hints appear only in a wholly empty editor's single plain paragraph.
Leading, trailing and intermediate blank paragraphs, including those inside
toggles, remain visible spacing without repeated slash hints. Empty toggle titles
retain their title prompt. This changes decorations only; blank blocks remain
in the document and survive saving, reopening and undo. Slash menus and hover
controls are available on those blank blocks without a visible prompt.

The user's 2026-10-23 Notion recording supplies the reference for paragraph vs
soft-line spacing, toggle exit and multiline quotes. Enter makes a separate
paragraph; Shift+Enter and cancelable native `insertLineBreak` share the same
hard-break command. Plain paragraphs get a runtime-only decoration class for
spacing; it is not serialized into saved HTML. A final empty body paragraph
after existing toggle content leaves one toggle level on Backspace. A first
empty body still returns to the title, and a middle empty line does not move
following content outside. `test_notion_writing_flow.py` covers these boundaries,
undo/redo, nested order and storage round trips.
