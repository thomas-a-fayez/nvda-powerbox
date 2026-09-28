"""This tool allows generation of gettext .mo compiled files, pot files from source code files
and pot files for merging using either native Python (polib & AST) or GNU gettext.
"""

import os
import shutil
import ast
from datetime import datetime
from SCons.Action import Action


def exists(env):
	return True


XGETTEXT_COMMON_ARGS = (
	"--msgid-bugs-address='$gettext_package_bugs_address' "
	"--package-name='$gettext_package_name' "
	"--package-version='$gettext_package_version' "
	"--keyword=pgettext:1c,2 "
	"-c -o $TARGET $SOURCES"
)


def _compile_mo_python(target, source, env):
	"""Compiles .po to .mo in pure Python using polib, eliminating msgfmt dependency on Windows."""
	try:
		import polib
		po = polib.pofile(str(source[0].abspath))
		po.save_as_mofile(str(target[0].abspath))
		return None
	except Exception as e:
		return str(e)


def _generate_pot_python(target, source, env):
	"""
	Extracts _("...") translatable strings using Python's native AST parser
	and dynamically retrieves version & project metadata from buildVars / SCons environment.
	"""
	try:
		import polib
		target_file = str(target[0].abspath)

		# Dynamically retrieve metadata from SCons environment or buildVars
		addon_info = env.get("addon_info", {})
		pkg_name = env.get("gettext_package_name") or addon_info.get("addon_name", "addon")
		pkg_version = env.get("gettext_package_version") or addon_info.get("addon_version", "")
		pkg_bugs = env.get("gettext_package_bugs_address") or addon_info.get("addon_author", "")

		version_str = f"{pkg_name} {pkg_version}".strip()

		pot = polib.POFile()
		pot.metadata = {
			"Project-Id-Version": version_str,
			"Report-Msgid-Bugs-To": pkg_bugs,
			"POT-Creation-Date": datetime.now().strftime("%Y-%m-%d %H:%M%z"),
			"PO-Revision-Date": datetime.now().strftime("%Y-%m-%d %H:%M%z"),
			"MIME-Version": "1.0",
			"Content-Type": "text/plain; charset=UTF-8",
			"Content-Transfer-Encoding": "8bit",
			"Generated-By": "PowerBox Pure Python POT Generator",
		}

		entries = {}

		for s in source:
			filepath = str(s.abspath)
			if not os.path.isfile(filepath):
				continue

			relpath = os.path.relpath(filepath, os.getcwd()).replace("\\", "/")

			try:
				with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
					tree = ast.parse(f.read(), filename=relpath)

				for node in ast.walk(tree):
					if isinstance(node, ast.Call):
						func_name = ""
						if isinstance(node.func, ast.Name):
							func_name = node.func.id

						if func_name == "_" and node.args:
							first_arg = node.args[0]
							if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
								msgid = first_arg.value
								lineno = getattr(node, "lineno", 1)
								if msgid in entries:
									entries[msgid].occurrences.append((relpath, lineno))
								else:
									entry = polib.POEntry(
										msgid=msgid,
										msgstr="",
										occurrences=[(relpath, lineno)],
									)
									entries[msgid] = entry
									pot.append(entry)
			except Exception:
				pass

		pot.save(target_file)
		return None
	except Exception as e:
		return str(e)


def generate(env):
	# Dynamic defaults without any hardcoded version or project strings
	env.SetDefault(gettext_package_bugs_address="")
	env.SetDefault(gettext_package_name="")
	env.SetDefault(gettext_package_version="")

	# Check if native msgfmt executable exists (e.g. on Linux/GitHub Actions)
	msgfmt_bin = shutil.which("msgfmt")
	if msgfmt_bin:
		mo_action = Action(f'"{msgfmt_bin}" -o $TARGET $SOURCE', "Compiling translation $SOURCE")
	else:
		mo_action = Action(_compile_mo_python, "Compiling translation (Python polib) $SOURCE")

	env["BUILDERS"]["gettextMoFile"] = env.Builder(
		action=mo_action,
		suffix=".mo",
		src_suffix=".po",
	)

	# Check if native xgettext executable exists
	xgettext_bin = shutil.which("xgettext")
	if xgettext_bin:
		pot_action = Action(f'"{xgettext_bin}" ' + XGETTEXT_COMMON_ARGS, "Generating pot file $TARGET")
		merge_action = Action(
			f'"{xgettext_bin}" ' + "--omit-header --no-location " + XGETTEXT_COMMON_ARGS,
			"Generating pot file $TARGET",
		)
	else:
		pot_action = Action(_generate_pot_python, "Generating pot file (Python AST) $TARGET")
		merge_action = Action(_generate_pot_python, "Generating pot file (Python AST) $TARGET")

	env["BUILDERS"]["gettextPotFile"] = env.Builder(
		action=pot_action,
		suffix=".pot",
	)

	env["BUILDERS"]["gettextMergePotFile"] = env.Builder(
		action=merge_action,
		suffix=".pot",
	)