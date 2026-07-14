# EGW Library import format

The EGW Library plugin imports books from JSON files (UTF-8, `.json`). A file holds one
book or several:

```json
{"book": { ... }}
{"books": [{ ... }, { ... }]}
```

A bare book object at the top level is also accepted.

## Book

| Field          | Required | Meaning                                                        |
|----------------|----------|----------------------------------------------------------------|
| `title`        | yes      | Full title, e.g. `"The Desire of Ages"`.                       |
| `abbreviation` | yes      | Standard EGW abbreviation, e.g. `"DA"`. Also used in citations.|
| `copyright`    | no       | Shown in the footer when enabled in the settings.              |
| `language`     | no       | ISO code, defaults to `"en"`.                                  |
| `aliases`      | no       | Extra names the search should recognise, e.g. `["Desire of Ages", "desire", "d.a."]`. The title and abbreviation are always recognised. Aliases are matched ignoring case and punctuation, so `"d.a."` also covers `DA` and `da`. |
| `chapters`     | (*)      | List of chapters, see below.                                   |
| `paragraphs`   | (*)      | For books without chapters: the paragraph list directly.       |

(*) A book needs either `chapters` or `paragraphs`.

## Chapter

| Field        | Required | Meaning                                              |
|--------------|----------|------------------------------------------------------|
| `number`     | no       | Chapter number; defaults to its position in the list.|
| `title`      | no       | Chapter title, e.g. `"God With Us"`.                 |
| `paragraphs` | yes      | List of paragraphs.                                  |

## Paragraph

A paragraph is either a plain string (the text) or an object:

| Field  | Required | Meaning                                                                  |
|--------|----------|--------------------------------------------------------------------------|
| `text` | yes      | The paragraph text. Paragraphs with empty text are skipped.              |
| `page` | no       | The page the paragraph *starts* on. Carries forward from the previous paragraph when omitted. |
| `para` | no       | The paragraph's number on its page (the ".2" in "DA 83.2"). Normally computed automatically by counting paragraphs per page; give it explicitly when the source numbering differs — e.g. when a paragraph carried over from the previous page counts as paragraph 1, the first paragraph *starting* on the page is `"para": 2`. |

## Notes

- Importing a book whose abbreviation already exists **replaces** that book.
- Citations follow the EGW standard: `DA 83.2` is page 83, second paragraph. Books
  imported without page numbers are still searchable by chapter and full text, and are
  cited by paragraph number (`DA ¶12`).
- A sample file is provided in this folder (`sample_book.json`).
