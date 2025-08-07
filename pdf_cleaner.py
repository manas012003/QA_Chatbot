import re
import fitz
import pymupdf4llm
from pathlib import Path

def extract_cleaned_markdown_from_pdf(pdf_path):
    pdf_name = Path(pdf_path).stem
    final_output_md = f"Markdown/{pdf_name}.md"
    Path("Markdown").mkdir(exist_ok=True)

    # === STEP 1: Extract all pages as Markdown ===
    doc = fitz.open(pdf_path)
    num_pages = doc.page_count
    doc.close()

    all_md = []
    for i in range(num_pages):
        md = pymupdf4llm.to_markdown(pdf_path, pages=[i]).strip()
        all_md.append(f"\n\n---\n### 📄 Page {i+1}\n---\n{md}")
    md_text = "\n".join(all_md)

    # === STEP 2: Define Helpers ===
    def parse_pages(md_text):
        page_splits = re.split(r'### 📄 Page (\d+)', md_text)
        pages = []
        for i in range(1, len(page_splits), 2):
            page_num = int(page_splits[i])
            content = page_splits[i + 1]
            pages.append({'page_num': page_num, 'content': content})
        return pages

    def extract_tables(page_content):
        table_pattern = re.compile(
            r'((?:\|[^\n]*\|\n)+\|[ ]*[-:| ]+\|\n(?:\|[^\n]*\|\n?)*)',
            re.MULTILINE
        )
        tables = []
        for match in table_pattern.finditer(page_content):
            tables.append({'span': match.span(), 'text': match.group()})
        return tables

    def merge_tables_across_pages(pages):
        merged_pages = []
        i = 0
        while i < len(pages):
            page = pages[i]
            tables = extract_tables(page['content'])

            if not tables:
                merged_pages.append(page['content'])
                i += 1
                continue

            new_content = page['content']
            for t_idx, table in enumerate(tables):
                if t_idx == len(tables) - 1 and i + 1 < len(pages):
                    next_tables = extract_tables(pages[i + 1]['content'])
                    if next_tables:
                        this_header = table['text'].split('\n')[0].strip()
                        next_lines = next_tables[0]['text'].split('\n')
                        next_header = next_lines[0].strip()

                        if (this_header == next_header or this_header.count('|') == next_header.count('|')):
                            sep_idx = next(
                                (idx for idx, line in enumerate(next_lines) if re.match(r'^\|[ -:|]+\|$', line)),
                                None
                            )
                            if this_header == next_header and sep_idx is not None:
                                next_data_rows = next_lines[sep_idx + 1:]
                            else:
                                next_data_rows = next_lines

                            merged_table = (
                                table['text'].rstrip() + '\n' +
                                '\n'.join(next_data_rows).rstrip() + '\n'
                            )

                            new_content = (
                                new_content[:table['span'][0]] +
                                merged_table +
                                new_content[table['span'][1]:]
                            )

                            next_content = pages[i + 1]['content']
                            next_content = (
                                next_content[:next_tables[0]['span'][0]] +
                                next_content[next_tables[0]['span'][1]:]
                            )
                            pages[i + 1]['content'] = next_content

            merged_pages.append(new_content)
            i += 1
        return merged_pages

    def reconstruct_markdown(pages, merged_contents):
        output = []
        for page, content in zip(pages, merged_contents):
            cleaned_lines = []
            for line in content.strip().split('\n'):
                if not re.match(r'^\|[ -:|]+\|$', line.strip()):
                    cleaned_lines.append(line)
            output.append(f"\n---\n### 📄 Page {page['page_num']}\n---\n")
            output.append('\n'.join(cleaned_lines))
        return '\n'.join(output).strip()

    # === STEP 3: Merge & Clean Tables ===
    pages = parse_pages(md_text)
    merged_contents = merge_tables_across_pages(pages)
    cleaned_md = reconstruct_markdown(pages, merged_contents)

    # === STEP 4: Save final output ===
    Path(final_output_md).write_text(cleaned_md, encoding="utf-8")
    #print(f"✅ Final merged markdown saved to: {final_output_md}")

    return cleaned_md