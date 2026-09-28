import gettext
import re
from pathlib import Path

import markdown

from .typings import AddonInfo


def _fix_doc_links(html_text: str, current_lang: str) -> str:
	"""
	Automatically rewrites markdown (.md) documentation links to offline relative HTML (.html) links.
	Enables repository README.md links to work seamlessly on both GitHub (markdown)
	and inside installed NVDA add-on HTML help files without manual editing.
	"""
	def replace_doc_link(match):
		target_lang = match.group(1).replace("_", "-").lower()
		if target_lang == current_lang.lower():
			return 'href="readme.html"'
		else:
			return f'href="../{target_lang}/readme.html"'

	# 1. Transform language readme links (e.g. href="addon/doc/ar/readme.md" -> href="../ar/readme.html")
	lang_pattern = (
		r'href=["\'](?!https?://)(?:.*?/)?(?:addon/)?(?:doc/)?([a-zA-Z]{2}(?:[_-][a-zA-Z]{2})?)/readme\.md["\']'
	)
	html_text = re.sub(lang_pattern, replace_doc_link, html_text, flags=re.IGNORECASE)

	# 2. Transform any remaining local .md relative links to .html (ignoring web URLs)
	html_text = re.sub(
		r'href=(["\'])(?!https?://|mailto:|#)(.*?)\.md\1',
		r'href=\1\2.html\1',
		html_text,
		flags=re.IGNORECASE
	)

	return html_text


def md2html(
		source: str | Path,
		dest: str | Path,
		*,
		moFile: str | Path | None,
		mdExtensions: list[str],
		addon_info: AddonInfo
	):
	if isinstance(source, str):
		source = Path(source)
	if isinstance(dest, str):
		dest = Path(dest)
	if isinstance(moFile, str):
		moFile = Path(moFile)

	try:
		with moFile.open("rb") as f:
			_ = gettext.GNUTranslations(f).gettext
	except Exception:
		summary = addon_info["addon_summary"]
	else:
		summary = _(addon_info["addon_summary"])
	version = addon_info["addon_version"]
	title = f"{summary} {version}"
	lang = source.parent.name.replace("_", "-")
	headerDic = {
		'[[!meta title="': "# ",
		'"]]': " #",
	}
	with source.open("r", encoding="utf-8") as f:
		mdText = f.read()
	for k, v in headerDic.items():
		mdText = mdText.replace(k, v, 1)

	# Compile markdown to HTML
	htmlText = markdown.markdown(mdText, extensions=mdExtensions)

	# Automatically apply smart link transformation for offline documentation
	htmlText = _fix_doc_links(htmlText, lang)

	# Optimization: build resulting HTML text in one go instead of writing parts separately.
	docText = "\n".join(
		(
			"<!DOCTYPE html>",
			f'<html lang="{lang}">',
			"<head>",
			'<meta charset="UTF-8">',
			'<meta name="viewport" content="width=device-width, initial-scale=1.0">',
			'<link rel="stylesheet" type="text/css" href="../style.css" media="screen">',
			f"<title>{title}</title>",
			"</head>\n<body>",
			htmlText,
			"</body>\n</html>",
		)
	)
	with dest.open("w", encoding="utf-8") as f:
		f.write(docText)  # type: ignore